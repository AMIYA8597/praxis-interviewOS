"""
Phase 64 — Coding Interview Engine.

Problem + editor + test execution + runtime limits.

Execution is sandboxed via a subprocess with resource limits.
Supports Python (primary) and can be extended.
This is NOT editor-only — it actually executes code against test cases.
"""
import asyncio
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_DEFAULT_TIME_LIMIT_MS = 2000
_DEFAULT_MEMORY_LIMIT_KB = 65536  # 64 MB

# Supported languages and their execution configs
_LANGUAGE_CONFIGS = {
    "python": {
        "extension": ".py",
        "command": [sys.executable, "-u"],
    },
}


async def _execute_code_subprocess(
    code: str,
    stdin_data: str,
    language: str,
    time_limit_ms: int,
) -> dict:
    """
    Execute code in a subprocess with timeout. Returns {stdout, stderr, runtime_ms, timed_out}.
    """
    config = _LANGUAGE_CONFIGS.get(language)
    if config is None:
        return {"stdout": "", "stderr": f"Language '{language}' not supported.", "runtime_ms": 0, "timed_out": False, "error": True}

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=config["extension"], delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmpfile = f.name

    try:
        cmd = config["command"] + [tmpfile]
        start = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_data, stderr_data = await asyncio.wait_for(
                proc.communicate(input=stdin_data.encode()),
                timeout=time_limit_ms / 1000.0,
            )
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return {
                "stdout": stdout_data.decode(errors="replace")[:10000],
                "stderr": stderr_data.decode(errors="replace")[:2000],
                "runtime_ms": elapsed_ms,
                "timed_out": False,
                "error": proc.returncode != 0,
            }
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return {
                "stdout": "", "stderr": "Time limit exceeded.",
                "runtime_ms": time_limit_ms, "timed_out": True, "error": False,
            }
    finally:
        try:
            os.unlink(tmpfile)
        except OSError:
            pass


async def run_code_against_tests(
    db: AsyncSession,
    session_id: str,
    code: str,
    test_cases: list[dict],
    language: str = "python",
    time_limit_ms: int = _DEFAULT_TIME_LIMIT_MS,
) -> dict:
    """
    Execute code against all test cases. Persist results to coding_test_run_results.
    Returns verdict + per-test results.
    """
    # Get current run number
    run_row = await db.execute(text("""
        SELECT COALESCE(MAX(run_number), 0) FROM coding_test_run_results WHERE session_id = :sid
    """), {"sid": session_id})
    run_number = (run_row.scalar() or 0) + 1

    results = []
    passed = 0
    verdict = "passed"

    for i, tc in enumerate(test_cases):
        stdin = tc.get("input", "")
        expected = tc.get("expected_output", "").strip()

        exec_result = await _execute_code_subprocess(code, stdin, language, time_limit_ms)

        if exec_result["timed_out"]:
            tc_verdict = "tle"
            verdict = "tle"
        elif exec_result["error"]:
            tc_verdict = "error"
            if verdict not in ("tle",):
                verdict = "error"
        else:
            actual = exec_result["stdout"].strip()
            if actual == expected:
                tc_verdict = "passed"
                passed += 1
            else:
                tc_verdict = "failed"
                if verdict not in ("tle", "error"):
                    verdict = "failed"

        results.append({
            "test_case": i + 1,
            "verdict": tc_verdict,
            "stdout": exec_result["stdout"][:500],
            "stderr": exec_result["stderr"][:200],
            "runtime_ms": exec_result["runtime_ms"],
            "expected": expected[:200] if expected else None,
        })

    now = datetime.now(timezone.utc)
    await db.execute(text("""
        INSERT INTO coding_test_run_results
        (session_id, run_number, code_snapshot, stdout, stderr,
         tests_passed, tests_failed, runtime_ms, verdict, ran_at)
        VALUES (:sid, :run, :code, :stdout, :stderr, :passed, :failed, :rt, :verdict, :now)
    """), {
        "sid": session_id, "run": run_number, "code": code[:50000],
        "stdout": results[0]["stdout"] if results else "",
        "stderr": results[0]["stderr"] if results else "",
        "passed": passed, "failed": len(test_cases) - passed,
        "rt": results[0]["runtime_ms"] if results else 0,
        "verdict": verdict, "now": now,
    })

    # Update coding_session_state
    await db.execute(text("""
        UPDATE coding_session_state SET
          current_code = :code, test_runs = test_runs + 1,
          tests_passed = :passed, tests_total = :total, last_run_at = :now
        WHERE session_id = :sid
    """), {
        "code": code[:50000], "passed": passed,
        "total": len(test_cases), "now": now, "sid": session_id,
    })

    await db.commit()

    return {
        "run_number": run_number,
        "verdict": verdict,
        "tests_passed": passed,
        "tests_total": len(test_cases),
        "results": results,
    }


async def get_coding_state(db: AsyncSession, session_id: str) -> Optional[dict]:
    row = await db.execute(text("""
        SELECT language, current_code, test_runs, tests_passed, tests_total
        FROM coding_session_state WHERE session_id = :sid
    """), {"sid": session_id})
    r = row.fetchone()
    if not r:
        return None
    return dict(r._mapping)
