# PRAXIS InterviewOS — Server-Side Request Forgery (SSRF) Defenses

**Milestone**: Phase 4 — Enterprise Security Engineering  
**Branch**: `phase4-security`  
**Date**: 2026-11-01  
**Classification**: NETWORK SECURITY SPECIFICATION & AUDIT  

---

## 1. SSRF Threat Vectors

Features accepting external URLs (such as custom AI provider base URLs or webhook endpoints) risk Server-Side Request Forgery (SSRF). An attacker could submit URLs pointing to internal infrastructure:
- Cloud metadata service (`http://169.254.169.254/computeMetadata/v1/`) to steal GCP service account OAuth tokens.
- Internal Redis service (`http://127.0.0.1:6379/` or `redis://localhost:6379`).
- Internal database port (`http://127.0.0.1:5432/`).
- Private RFC1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).

---

## 2. Implemented Defense: DNS Resolution & IP Blocklist

PRAXIS implements pre-connection validation in `backend/app/core/security.py`:

```python
def is_safe_url(url: str) -> bool:
    """
    Resolves the hostname and ensures it does not map to a private 
    or cloud-metadata IP address. Prevents SSRF attacks.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
            
        ip_addr = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_addr)
        
        # Block Private IPs (10.0.0.0/8, 192.168.0.0/16, etc.)
        if ip.is_private:
            return False
            
        # Block Loopback (127.0.0.1, ::1)
        if ip.is_loopback:
            return False
            
        # Block Cloud Metadata (AWS, GCP, Azure: 169.254.169.254)
        if str(ip) == "169.254.169.254":
            return False
            
        return True
    except Exception:
        return False
```

---

## 3. Boundary Enforcement Invariants
1. **Scheme Restriction**: Only `https://` (and `http://` in development) are accepted; dangerous schemes (`file://`, `gopher://`, `dict://`, `ftp://`) are rejected.
2. **DNS Rebinding Prevention**: Resolved IP addresses are validated immediately prior to socket connection.
3. **No Credential Forwarding**: Authorization headers are stripped if a redirect traverses to an external domain.
