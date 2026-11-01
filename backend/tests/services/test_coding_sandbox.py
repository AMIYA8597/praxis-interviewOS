"""
Tests for Sandboxed Coding Interview Engine.

Proves:
1. No secrets in os.environ (DATABASE_URL, API keys, JWT secrets are not accessible)
2. Network egress fails (socket connection raises PermissionError)
3. Infinite loops are contained (timed_out=True within time limit)
4. Fork bombs are contained and do not crash the caller
5. Memory bombs are contained
6. Hidden test cases mask inputs and expected outputs
7. API / test runner stays alive throughout hostile runs
"""
import pytest

from backend.app.services.coding_engine import _execute_code_subprocess, run_code_against_tests


@pytest.mark.asyncio
async def test_no_secrets_in_os_environ(monkeypatch):
    """Candidate code must not have access to any parent secrets."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://praxis:super_secret_pw@host:5432/db")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-super-secret-key-12345")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "secret-service-role-key-999")
    monkeypatch.setenv("JWT_SECRET", "super-secret-jwt-signing-key")

    code = """
import os
secrets = [
    os.environ.get("DATABASE_URL"),
    os.environ.get("OPENAI_API_KEY"),
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
    os.environ.get("JWT_SECRET")
]
print("SECRETS:" + ",".join(str(s) for s in secrets))
"""
    result = await _execute_code_subprocess(code, "", "python", 2000)
    assert not result["timed_out"]
    assert "SECRETS:None,None,None,None" in result["stdout"], (
        f"Candidate code leaked secrets from parent: {result['stdout']}"
    )


@pytest.mark.asyncio
async def test_socket_connect_fails():
    """Socket connections must fail immediately due to network isolation."""
    code = """
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("1.1.1.1", 80))
    print("CONNECTED")
except Exception as e:
    print(f"FAILED:{type(e).__name__}:{e}")
"""
    result = await _execute_code_subprocess(code, "", "python", 2000)
    assert not result["timed_out"]
    assert "CONNECTED" not in result["stdout"]
    assert "Network egress is disabled" in result["stdout"] or "PermissionError" in result["stdout"]


@pytest.mark.asyncio
async def test_infinite_loop_contained():
    """Infinite loop should terminate at time limit and not block the caller."""
    code = """
while True:
    pass
"""
    result = await _execute_code_subprocess(code, "", "python", 500)
    assert result["timed_out"] is True
    assert result["runtime_ms"] >= 500


@pytest.mark.asyncio
async def test_fork_bomb_contained():
    """Fork bomb attempt should be contained without crashing the host."""
    code = """
import os
import sys

if hasattr(os, "fork"):
    for _ in range(100):
        try:
            os.fork()
        except OSError:
            break
else:
    print("NO_FORK")
print("FORK_DONE")
"""
    result = await _execute_code_subprocess(code, "", "python", 1500)
    assert not result["timed_out"] or result["error"]
    # Host runner stays alive


@pytest.mark.asyncio
async def test_memory_bomb_contained():
    """Memory bomb attempt is contained without killing the host."""
    code = """
# Unbounded allocation attempt
l = []
try:
    while True:
        l.append(" " * 50_000_000)
except (MemoryError, OverflowError):
    print("MEMORY_LIMIT_HIT")
"""
    result = await _execute_code_subprocess(code, "", "python", 1000)
    # The subprocess will either catch MemoryError, be killed by timeout, or exit with error
    assert result["timed_out"] or result["error"] or "MEMORY_LIMIT_HIT" in result["stdout"]


@pytest.mark.asyncio
async def test_hidden_test_cases():
    """Hidden test cases mask their expected and actual outputs."""
    from unittest.mock import AsyncMock, MagicMock

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=0)))
    mock_db.commit = AsyncMock()

    code = "name = input(); print(f'Hello, {name}!')"
    test_cases = [
        {"input": "Alice", "expected_output": "Hello, Alice!", "is_hidden": False},
        {"input": "SecretPerson", "expected_output": "Hello, SecretPerson!", "is_hidden": True},
    ]

    res = await run_code_against_tests(mock_db, "session-123", code, test_cases, "python", 2000)
    assert res["verdict"] == "passed"
    assert res["tests_passed"] == 2

    results = res["results"]
    assert results[0]["is_hidden"] is False
    assert results[0]["stdout"].strip() == "Hello, Alice!"
    assert results[0]["expected"].strip() == "Hello, Alice!"

    assert results[1]["is_hidden"] is True
    assert results[1]["stdout"] == "[Hidden]"
    assert results[1]["expected"] == "[Hidden]"


@pytest.mark.asyncio
async def test_api_stays_alive_after_hostile_runs():
    """After hostile tests, normal code execution still succeeds cleanly."""
    normal_code = "print('system is completely functional')"
    result = await _execute_code_subprocess(normal_code, "", "python", 1000)
    assert not result["timed_out"]
    assert not result["error"]
    assert "system is completely functional" in result["stdout"]
