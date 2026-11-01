"""
Standalone Sandbox Execution Service.

Runs candidate-submitted code in an isolated environment with:
- No network egress
- No secrets in environment variables
- Memory, process, and CPU limits
- Clean, empty temporary directory per execution
"""
import asyncio
import logging
import os
import sys
import tempfile
import time

from fastapi import FastAPI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_DEFAULT_TIME_LIMIT_MS = 2000
_DEFAULT_MEMORY_LIMIT_KB = 65536  # 64 MB

app = FastAPI(title="PRAXIS Sandbox Service", version="1.0.0")


class ExecuteRequest(BaseModel):
    code: str
    stdin_data: str = ""
    language: str = "python"
    time_limit_ms: int = Field(default=_DEFAULT_TIME_LIMIT_MS, ge=100, le=10000)


class ExecuteResponse(BaseModel):
    stdout: str
    stderr: str
    runtime_ms: int
    timed_out: bool
    error: bool


_EGRESS_BLOCKER = """
import socket

def _block_connect(*args, **kwargs):
    raise PermissionError("Network egress is disabled in this sandbox environment")

socket.socket.connect = _block_connect
socket.socket.connect_ex = lambda *a, **kw: 111
socket.create_connection = _block_connect
"""


def _sandbox_preexec(memory_limit_kb: int) -> None:
    try:
        import resource as _resource
        mem_bytes = memory_limit_kb * 1024
        _resource.setrlimit(_resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        _resource.setrlimit(_resource.RLIMIT_NPROC, (1, 1))
        _resource.setrlimit(_resource.RLIMIT_NOFILE, (64, 64))
    except (ImportError, ValueError, OSError):
        pass


def _get_minimal_env(temp_dir: str) -> dict[str, str]:
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


async def execute_code_locally(
    code: str,
    stdin_data: str = "",
    language: str = "python",
    time_limit_ms: int = _DEFAULT_TIME_LIMIT_MS,
) -> dict:
    if language != "python":
        return {
            "stdout": "",
            "stderr": f"Language '{language}' not supported.",
            "runtime_ms": 0,
            "timed_out": False,
            "error": True,
        }

    with tempfile.TemporaryDirectory(prefix="praxis_sandbox_") as tmp_dir:
        # Write network guard
        with open(os.path.join(tmp_dir, "sitecustomize.py"), "w", encoding="utf-8") as f:
            f.write(_EGRESS_BLOCKER)

        code_file = os.path.join(tmp_dir, "solution.py")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        minimal_env = _get_minimal_env(tmp_dir)
        cmd = [sys.executable, "-u", "solution.py"]

        start = time.perf_counter()
        try:
            import functools
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
            try:
                proc.kill()
            except Exception:
                pass
            return {
                "stdout": "",
                "stderr": "Time limit exceeded.",
                "runtime_ms": time_limit_ms,
                "timed_out": True,
                "error": False,
            }


@app.get("/health/live")
async def health_live():
    return {"status": "ok", "service": "praxis-sandbox"}


@app.post("/execute", response_model=ExecuteResponse)
async def execute_endpoint(req: ExecuteRequest):
    result = await execute_code_locally(
        code=req.code,
        stdin_data=req.stdin_data,
        language=req.language,
        time_limit_ms=req.time_limit_ms,
    )
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8001")))
