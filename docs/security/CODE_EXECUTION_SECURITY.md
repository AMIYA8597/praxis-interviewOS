# PRAXIS InterviewOS — Code Execution & Sandbox Security Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: SANDBOX SECURITY & EXECUTION ISOLATION REPORT  

---

## 1. High-Risk Capability Architecture

Candidate live coding exercises execute untrusted Python and JavaScript code. To protect the host operating system, database connection pools, and adjacent tenant sessions, code execution is completely decoupled from the primary API server.

```
[ Candidate Code Submission ]
              |
              v
[ Standalone Sandbox Service (backend/app/sandbox_service.py) ]
              |
              v
+=======================================================================+
| Process Isolation Invariants                                          |
|                                                                       |
| 1. Stripped Environment:                                              |
|    - DATABASE_URL, OPENAI_API_KEY, and JWT secrets scrubbed           |
|    - Only safe minimal PATH provided                                  |
|                                                                       |
| 2. Network Egress Blocked:                                            |
|    - socket.socket monkeypatched to raise PermissionError             |
|    - Container deployed with --network none                           |
|                                                                       |
| 3. Resource Quotas:                                                   |
|    - Execution Timeout: hard killed after 5.0 seconds (timed_out=True)|
|    - Memory Limit: RLIMIT_AS capped at 256MB                          |
|    - Ephemeral Storage: isolated tmpfs / TemporaryDirectory           |
+=======================================================================+
```

---

## 2. Adversarial Test Evidence (`backend/tests/services/test_coding_sandbox.py`)

| Test Case | Malicious Code Injected | Expected Defense | Status |
| :--- | :--- | :--- | :--- |
| **Secret Exfiltration** | Reads `os.environ.get("DATABASE_URL")` | Returns `None` | **PASS** |
| **Outbound C2 Connection**| `socket.connect(("1.1.1.1", 80))` | Raises `PermissionError: Network egress is disabled` | **PASS** |
| **Infinite Loop / Hang** | `while True: pass` | Process terminated at timeout; returns `timed_out=True` | **PASS** |
| **Memory Bomb** | Allocates 2GB byte array | Process aborted before memory exhaustion | **PASS** |
| **Filesystem Escape** | `open("/etc/shadow", "r")` | Access denied or file missing in ephemeral chroot | **PASS** |
