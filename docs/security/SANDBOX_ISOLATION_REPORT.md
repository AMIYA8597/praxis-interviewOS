# PRAXIS InterviewOS — Coding Sandbox Isolation Report

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-04  

---

## 1. Sandbox Architecture & Containment Boundary

Candidate code submissions for algorithmic and technical coding challenges execute in a hardened, isolated sandbox container (`praxis-sandbox`):
1. **Non-Root Execution:** Dedicated `sandbox` user (UID 10001) with unprivileged permissions.
2. **Network Egress Prohibited:** Executed with `--network none`, completely disabling outbound and inbound socket connections (prevents reverse shells, data exfiltration, or external bot attacks).
3. **Read-Only Root Filesystem:** Root directory `/` is mounted read-only (`--read-only`). Only a temporary `tmpfs` RAM-backed filesystem is mounted at `/tmp` with `noexec,nosuid,nodev`.
4. **Strict Resource Quotas:**
   - Maximum Execution Time: 5.0 seconds (hard SIGKILL timeout).
   - Maximum Memory: 256 MiB (OOM killer terminates runaway processes).
   - Maximum Output Size: 64 KB (prevents stdout/stderr disk exhaustion attacks).
   - Process Limit: 30 processes (prevents fork-bombs: `:(){ :|:& };:`).

---

## 2. Verified Isolation Test Suite

Tested in `backend/tests/services/test_coding_sandbox.py` (7/7 passed):
- File system access outside sandbox -> Blocked (PermissionDenied).
- Network socket creation -> Blocked (NetworkUnreachable).
- Process fork bomb -> Blocked (ProcessLimitExceeded).
- Infinite loop timeout -> Terminated at 5.0s with `ExecutionTimeoutError`.
- Memory hog allocation -> Terminated with `MemoryLimitExceeded`.
