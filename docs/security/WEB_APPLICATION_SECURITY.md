# PRAXIS InterviewOS — Web Application Security Specification

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: WEB APP & FRONTEND SECURITY REPORT  

---

## 1. Enterprise HTTP Security Headers

The Next.js 15 application enforces enterprise HTTP response headers on all routes via `apps/web/src/middleware.ts`:

| Header | Production Value | Security Purpose |
| :--- | :--- | :--- |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https: wss: ws:; media-src 'self' blob:; frame-ancestors 'none';` | Mitigates XSS, restricts script/media sources, prevents clickjacking |
| `X-Frame-Options` | `DENY` | Prevents rendering inside external `<iframe>` (Clickjacking defense) |
| `X-Content-Type-Options`| `nosniff` | Blocks MIME-sniffing attacks |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Protects sensitive URL paths from leaking across origins |
| `Permissions-Policy` | `camera=(), microphone=(self), geolocation=()` | Restricts microphone strictly to the application origin |
| `Strict-Transport-Security`| `max-age=63072000; includeSubDomains; preload` | Enforces HTTPS strictly in production environments |

---

## 2. Cross-Site Scripting (XSS) Defenses

1. **React JSX Auto-Escaping**:
   - All dynamic text (candidate names, transcripts, interviewer questions, and feedback rationale) is rendered through React's native string interpolation, preventing script execution.
2. **Untrusted Markdown & HTML Sanitization**:
   - AI-generated responses and job descriptions containing Markdown are parsed strictly through sanitized renderers with HTML tags stripped.
   - Raw `dangerouslySetInnerHTML` is prohibited across all client components.

---

## 3. Cross-Site Request Forgery (CSRF) & Cookie Governance

1. **SameSite Cookie Configuration**:
   - Supabase SSR authentication cookies enforce `SameSite=Lax; HttpOnly; Secure; Path=/`.
   - Browser automatically omits cookies on untrusted cross-origin POST/PATCH/DELETE requests.
2. **CORS Configuration**:
   - Production FastAPI backend enforces an explicit CORS allowlist matching trusted frontend origins.
   - Wildcard origins (`*`) are disallowed when `allow_credentials=True`.
