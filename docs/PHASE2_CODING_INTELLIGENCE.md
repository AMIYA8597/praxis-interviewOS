# PRAXIS InterviewOS — Phase 2 Coding Intelligence Engine

**Date**: 2026-11-01  
**Project**: PRAXIS InterviewOS (`AMIYA8597/praxis-interviewOS`)  
**Workstream**: WORKSTREAM G — CODING INTELLIGENCE  
**Classification**: PRODUCTION SECURITY & EXECUTION SPECIFICATION  

---

## 1. Execution Sandbox & Security Architecture

The Coding Interview Engine (`backend/app/services/coding_engine.py`) runs candidate-submitted code in an isolated subprocess sandbox designed to withstand hostile code:

1. **Environment Sanitization**:
   - Zero access to parent environment variables. Database URLs, Supabase keys, AI API tokens, and JWT secrets are completely stripped from child process environment (`SECRETS:None,None,None,None`).
2. **Network Isolation**:
   - Subprocess socket creation and network egress are intercepted and blocked with `PermissionError: Network egress is disabled in this sandbox environment`.
3. **Resource & Denial-of-Service Containment**:
   - Execution Timeout: Strict per-run time limit (default 2000ms). Infinite loops (`while True: pass`) are killed cleanly without blocking the caller.
   - Memory Limits: Process address space bounded (`RLIMIT_AS` on Linux, allocation monitoring on Windows). Unbounded memory allocations trigger `MemoryError` or timeout rather than killing host.
   - Process Controls: Fork bombs blocked via `RLIMIT_NPROC` and process termination.
4. **Hidden Test Cases**:
   - Supports confidential evaluation test cases where inputs and outputs are marked `is_hidden: true`. Output values are masked with `[Hidden]` in candidate responses to prevent test leakage.
