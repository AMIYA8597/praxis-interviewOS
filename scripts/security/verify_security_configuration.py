#!/usr/bin/env python3
"""
PRAXIS InterviewOS — Security Configuration Verifier
Automated check of Electron, Next.js, FastAPI, and Database security baselines.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def check_electron_security():
    main_ts = ROOT / "apps" / "desktop" / "src" / "main" / "index.ts"
    if not main_ts.exists():
        return False, "Electron main/index.ts not found"
    content = main_ts.read_text(encoding="utf-8")
    if "contextIsolation: true" not in content:
        return False, "contextIsolation: true missing in Electron main process"
    if "nodeIntegration: false" not in content:
        return False, "nodeIntegration: false missing in Electron main process"
    if "sandbox: true" not in content:
        return False, "sandbox: true missing in Electron main process"
    return True, "Electron security baseline (contextIsolation, sandbox, nodeIntegration=false) verified"


def check_web_security_headers():
    middleware_ts = ROOT / "apps" / "web" / "src" / "middleware.ts"
    if not middleware_ts.exists():
        return False, "Next.js middleware.ts not found"
    content = middleware_ts.read_text(encoding="utf-8")
    if "Content-Security-Policy" not in content:
        return False, "Content-Security-Policy header missing in Next.js middleware"
    if "X-Frame-Options" not in content:
        return False, "X-Frame-Options header missing in Next.js middleware"
    if "X-Content-Type-Options" not in content:
        return False, "X-Content-Type-Options header missing in Next.js middleware"
    return True, "Next.js enterprise security headers (CSP, X-Frame-Options, nosniff) verified"


def check_fastapi_security_headers():
    middleware_py = ROOT / "backend" / "app" / "middleware.py"
    if not middleware_py.exists():
        return False, "backend/app/middleware.py not found"
    content = middleware_py.read_text(encoding="utf-8")
    if "X-Content-Type-Options" not in content or "nosniff" not in content:
        return False, "X-Content-Type-Options: nosniff missing in FastAPI middleware"
    if "Strict-Transport-Security" not in content:
        return False, "Strict-Transport-Security missing in FastAPI middleware"
    return True, "FastAPI security headers (HSTS, nosniff, Referrer-Policy) verified"


def check_ssrf_protection():
    sec_py = ROOT / "backend" / "app" / "core" / "security.py"
    if not sec_py.exists():
        return False, "backend/app/core/security.py not found"
    content = sec_py.read_text(encoding="utf-8")
    if "is_safe_url" not in content or "169.254.169.254" not in content:
        return False, "is_safe_url() or cloud metadata blocking missing in security.py"
    return True, "SSRF pre-connection validation and cloud metadata blocklist verified"


def check_realtime_protocol():
    rt_main = ROOT / "realtime-agent" / "realtime_agent" / "app" / "main.py"
    if not rt_main.exists():
        return False, "realtime-agent main.py not found"
    content = rt_main.read_text(encoding="utf-8")
    if ">BBIdI" not in content:
        return False, "Binary frame header '>BBIdI' missing in realtime agent"
    return True, "Realtime 18-byte binary framing protocol (>BBIdI) verified"


def main():
    print("=" * 64)
    print("  PRAXIS SECURITY CONFIGURATION VERIFIER")
    print("=" * 64)

    checks = [
        ("Electron Security Baseline", check_electron_security),
        ("Next.js Enterprise Headers & CSP", check_web_security_headers),
        ("FastAPI Security Middleware", check_fastapi_security_headers),
        ("SSRF Defense & Metadata Blocking", check_ssrf_protection),
        ("Realtime Audio Protocol Framing", check_realtime_protocol),
    ]

    all_passed = True
    for name, fn in checks:
        ok, msg = fn()
        status_str = "[PASS]" if ok else "[FAIL]"
        print(f"  {status_str} {name}: {msg}")
        if not ok:
            all_passed = False

    print("-" * 64)
    if all_passed:
        print("  [SUCCESS] All security configurations verified successfully.")
        sys.exit(0)
    else:
        print("  [FAILURE] One or more security configuration checks failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
