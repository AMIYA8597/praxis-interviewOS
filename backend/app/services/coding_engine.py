"""
Phase 64 — Coding Interview Engine.

Problem + editor + test execution + runtime limits.

Execution is sandboxed:
- Zero secrets in environment (minimal env only)
- Network egress blocked
- Execution in clean, empty isolated temporary directory
- Supports remote standalone sandbox service (via SANDBOX_SERVICE_URL)
- Resource limits (memory, execution timeout, subprocess controls)
- Supports hidden test cases
"""
import asyncio
import functools
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_DEFAULT_TIME_LIMIT_MS = 2000
_DEFAULT_MEMORY_LIMIT_KB = 65536  # 64 MB

_EGRESS_BLOCKER = """
import socket

def _block_connect(*args, **kwargs):
    raise PermissionError("Network egress is disabled in this sandbox environment")

socket.socket.connect = _block_connect
socket.socket.connect_ex = lambda *a, **kw: 111
socket.create_connection = _block_connect
"""


def _sandbox_preexec(memory_limit_kb: int) -> None:
    """
    Called in the child process before exec — enforces resource limits on Linux.
    Gracefully skipped on Windows (no `resource` module).
    Limits:
      - RLIMIT_AS: virtual address space (memory)
      - RLIMIT_NPROC: number of subprocesses (blocks fork bombs)
      - RLIMIT_NOFILE: open file descriptors
    """
    try:
        import resource as _resource  # Unix only
        mem_bytes = memory_limit_kb * 1024
        _resource.setrlimit(_resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        _resource.setrlimit(_resource.RLIMIT_NPROC, (1, 1))  # no child processes
        _resource.setrlimit(_resource.RLIMIT_NOFILE, (64, 64))  # limit open files
    except (ImportError, ValueError, OSError):
        pass  # Windows or privilege issue — timeout is still the last-resort guard


def _get_minimal_env(temp_dir: str) -> dict[str, str]:
    """
    Produce a strictly sanitized minimal environment.
    Guarantees no application secrets, database credentials, or API keys are inherited.
    """
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTHONUNBUFFERED": "1",
        "HOME": temp_dir,
        "TMPDIR": temp_dir,
        "TMP": temp_dir,
        "TEMP": temp_dir,
        "USERPROFILE": temp_dir,
        "PYTHONPATH": temp_dir,
    }
    if sys.platform == "win32":
        for k in ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"):
            if k in os.environ:
                env[k] = os.environ[k]
    return env


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
    Execute code in a sandboxed subprocess with timeout, minimal environment,
    empty temp dir, and network egress blocked.
    If SANDBOX_SERVICE_URL is configured, dispatches to the standalone sandbox service.
    """
    sandbox_url = os.environ.get("SANDBOX_SERVICE_URL")
    if sandbox_url:
        try:
            async with httpx.AsyncClient(timeout=time_limit_ms / 1000.0 + 3.0) as client:
                resp = await client.post(
                    f"{sandbox_url.rstrip('/')}/execute",
                    json={
                        "code": code,
                        "stdin_data": stdin_data,
                        "language": language,
                        "time_limit_ms": time_limit_ms,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"Remote sandbox invocation failed, falling back to local sandbox: {e}")

    config = _LANGUAGE_CONFIGS.get(language)
    if config is None:
        return {
            "stdout": "",
            "stderr": f"Language '{language}' not supported.",
            "runtime_ms": 0,
            "timed_out": False,
            "error": True,
        }

    with tempfile.TemporaryDirectory(prefix="praxis_sandbox_", ignore_cleanup_errors=True) as tmp_dir:
        # Write network guard to prevent network egress from the candidate script
        guard_file = os.path.join(tmp_dir, "sitecustomize.py")
        with open(guard_file, "w", encoding="utf-8") as f:
            f.write(_EGRESS_BLOCKER)

        code_file = os.path.join(tmp_dir, f"solution{config['extension']}")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        minimal_env = _get_minimal_env(tmp_dir)
        cmd = config["command"] + [code_file]
        start = time.perf_counter()
        proc = None
        try:
            preexec = functools.partial(_sandbox_preexec, _DEFAULT_MEMORY_LIMIT_KB)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmp_dir,
                env=minimal_env,
                preexec_fn=preexec if sys.platform != "win32" else None,
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
            if proc is not None:
                try:
                    proc.kill()
                    await asyncio.wait_for(proc.wait(), timeout=1.0)
                except Exception:
                    pass
            return {
                "stdout": "",
                "stderr": "Time limit exceeded.",
                "runtime_ms": time_limit_ms,
                "timed_out": True,
                "error": False,
            }
        finally:
            if proc is not None and proc.returncode is None:
                try:
                    proc.kill()
                    await asyncio.wait_for(proc.wait(), timeout=1.0)
                except Exception:
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
    Returns verdict + per-test results (masking hidden test inputs/outputs).
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
        is_hidden = bool(tc.get("is_hidden", False))

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
            "is_hidden": is_hidden,
            "stdout": "[Hidden]" if is_hidden else exec_result["stdout"][:500],
            "stderr": "[Hidden]" if is_hidden and tc_verdict != "tle" else exec_result["stderr"][:200],
            "runtime_ms": exec_result["runtime_ms"],
            "expected": "[Hidden]" if is_hidden else (expected[:200] if expected else None),
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

    # Upsert coding_session_state (creates row on first run, increments on subsequent runs)
    await db.execute(text("""
        INSERT INTO coding_session_state
          (session_id, language, current_code, test_runs, tests_passed, tests_total, last_run_at)
        VALUES (:sid, :lang, :code, 1, :passed, :total, :now)
        ON CONFLICT (session_id) DO UPDATE SET
          current_code = EXCLUDED.current_code,
          test_runs    = coding_session_state.test_runs + 1,
          tests_passed = EXCLUDED.tests_passed,
          tests_total  = EXCLUDED.tests_total,
          last_run_at  = EXCLUDED.last_run_at
    """), {
        "sid": session_id, "lang": language,
        "code": code[:50000], "passed": passed,
        "total": len(test_cases), "now": now,
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
