# PRAXIS InterviewOS — Phase 3 Authentication & Session Integration

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Date**: 2026-11-01  
**Classification**: SECURITY & AUTHENTICATION SPECIFICATION  

---

## 1. Authentication Architecture

PRAXIS utilizes Supabase Authentication backed by RS256 JWT tokens.

```
+-------------+         1. Login / Exchange         +---------------------+
| Client App  | ----------------------------------> | Supabase Auth API   |
| (Web/Desk)  | <---------------------------------- | (Issues RS256 JWT)  |
+-------------+         2. Access & Refresh Tokens  +---------------------+
       |
       | 3. Authenticated Request (Bearer <JWT>)
       v
+-----------------------+     4. JWKS Validation     +--------------------+
| PRAXIS Backend        | -------------------------> | Supabase JWKS Endpoint
| FastAPI / WebSocket   | <------------------------- | (Caches Public Keys)|
+-----------------------+                            +--------------------+
```

---

## 2. Web Client Authentication (`apps/web`)

### 2.1 Supabase SSR Integration
- Utilizes `@supabase/ssr` to maintain authentication state securely across server components, client components, and Next.js middleware.
- Cookies are HTTP-only and protected against XSS.
- Middleware (`apps/web/src/middleware.ts`) automatically intercepts unauthenticated requests to protected paths (`/sessions`, `/readiness`, `/study`, `/platform/*`) and redirects to `/auth`.

### 2.2 Token Refresh Lifecycle
- The Supabase client automatically refreshes access tokens before expiration.
- WebSocket connections retrieve the active `access_token` during initial handshake and prior to any reconnection attempt.

---

## 3. Desktop Client Authentication (`apps/desktop`)

### 3.1 Credential Storage
- Tokens are encrypted and stored via the native platform keychain / safe storage where available, with in-memory fallbacks.
- Renderer communicates through the context-isolated IPC channels:
  - `storageGet(key)`
  - `storageSet(key, value)`
  - `authLogout()`
- Tokens are never exposed to insecure local files or browser `localStorage`.

---

## 4. Realtime WebSocket Authorization

### Handshake Protocol
```
ws://<HOST>:8001/ws/sessions/{session_id}?token={JWT_ACCESS_TOKEN}
```
1. Connection rejected immediately (HTTP 401/403) if JWT is missing, expired, or signature fails RS256 JWKS verification.
2. Connection verified against session ownership: candidates can only connect to sessions belonging to their authenticated user ID.
3. If token expires during an active session, client initiates proactive token refresh and reconnects with sequence reconciliation to prevent turn loss.
