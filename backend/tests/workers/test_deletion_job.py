"""
Unit tests for the account-deletion job (P1C.2).

These use a fake async engine that records every SQL statement per
transaction, so they run without a database. The real-DB path is covered by
backend/tests/integration/test_real_deletion_job.py.

Contract under test:
  * DeletionService.process_deletion_job performs the cascade only and never
    touches deletion_jobs (the old inner "step 4" UPDATE, which queried the
    already-deleted candidate row and always updated zero rows, is gone).
  * delete_candidate_account_job in worker_tasks.py is the single source of
    truth for deletion_jobs status: exactly one write, 'completed' on success,
    'failed' on error.
"""
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.core.deletion import DeletionService
from backend.app.worker_tasks import delete_candidate_account_job


class FakeConn:
    def __init__(self, engine, txn):
        self._engine = engine
        self._txn = txn

    async def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        self._engine.statements.append((self._txn, sql, dict(params or {})))
        if self._engine.fail_on and self._engine.fail_on in sql:
            raise RuntimeError(f"simulated failure on: {self._engine.fail_on}")
        result = MagicMock()
        if sql.startswith("SELECT storage_path FROM documents"):
            result.fetchall.return_value = [(p,) for p in self._engine.storage_paths]
        else:
            result.fetchall.return_value = []
        return result


class FakeEngine:
    """Mimics the AsyncEngine.begin() API used by DeletionService and the worker."""

    def __init__(self, storage_paths=(), fail_on=None):
        self.statements = []  # (transaction_index, sql, params)
        self.storage_paths = list(storage_paths)
        self.fail_on = fail_on
        self._txn_count = 0

    @asynccontextmanager
    async def begin(self):
        self._txn_count += 1
        yield FakeConn(self, self._txn_count)

    def sql_matching(self, needle):
        return [(t, s, p) for (t, s, p) in self.statements if needle in s]


def _fake_storage():
    storage = MagicMock()
    storage.delete = AsyncMock()
    return storage


async def test_deletion_service_never_touches_deletion_jobs():
    engine = FakeEngine(storage_paths=["resumes/a.pdf"])
    storage = _fake_storage()
    candidate_id = str(uuid.uuid4())

    await DeletionService(db=engine, storage_client=storage).process_deletion_job(candidate_id)

    assert engine.sql_matching("deletion_jobs") == [], (
        "DeletionService must not read or write deletion_jobs; "
        "status is owned by delete_candidate_account_job"
    )
    deletes = engine.sql_matching("DELETE FROM candidates WHERE id = CAST(:cid AS uuid)")
    assert len(deletes) == 1 and deletes[0][2] == {"cid": candidate_id}
    # Nothing may query the candidate row after it has been deleted (the old bug).
    delete_idx = engine.statements.index(deletes[0])
    assert not any(
        "FROM candidates" in s for (_, s, _) in engine.statements[delete_idx + 1:]
    )
    storage.delete.assert_awaited_once_with("resumes/a.pdf")


async def test_job_marks_completed_exactly_once():
    engine = FakeEngine(storage_paths=["resumes/a.pdf", "resumes/b.pdf"])
    storage = _fake_storage()
    job_id, candidate_id = str(uuid.uuid4()), str(uuid.uuid4())

    with patch("backend.app.core.storage.get_storage_client", return_value=storage):
        await delete_candidate_account_job({"db_engine": engine}, job_id, candidate_id)

    writes = engine.sql_matching("deletion_jobs")
    # Expect 2 writes: 'running' (start) then 'completed' (end).
    statuses = [s for (_, s, _) in writes]
    assert any("status = 'running'" in s for s in statuses), "missing 'running' update"
    completed = [(t, s, p) for (t, s, p) in writes if "status = 'completed'" in s]
    assert len(completed) == 1, f"expected exactly 1 'completed' write, got {completed}"
    txn, sql, params = completed[0]
    assert "completed_at = NOW()" in sql
    assert params.get("id") == job_id

    # The final status write happens after the cascade committed.
    cascade_txns = {t for (t, s, _) in engine.sql_matching("DELETE FROM candidates")}
    assert txn > max(cascade_txns)
    assert storage.delete.await_count == 2


async def test_job_marks_failed_and_reraises_on_cascade_error():
    engine = FakeEngine(fail_on="DELETE FROM candidates")
    job_id, candidate_id = str(uuid.uuid4()), str(uuid.uuid4())

    from backend.app.worker_tasks import DEFAULT_MAX_TRIES
    # Simulate the final retry attempt so the job writes 'failed' instead of re-queuing.
    ctx = {"db_engine": engine, "job_try": DEFAULT_MAX_TRIES}
    with patch("backend.app.core.storage.get_storage_client", return_value=_fake_storage()):
        with pytest.raises(Exception):
            await delete_candidate_account_job(ctx, job_id, candidate_id)

    writes = engine.sql_matching("deletion_jobs")
    # Expect 2 writes: 'running' then 'failed'.
    failed = [(t, s, p) for (t, s, p) in writes if "status = 'failed'" in s]
    assert len(failed) == 1, f"expected exactly 1 'failed' write, got {writes}"
    _, sql, params = failed[0]
    assert params.get("id") == job_id
    assert params.get("err") or params.get("error_message")  # error text is present
    assert engine.sql_matching("status = 'completed'") == []
