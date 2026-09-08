import socket
import ipaddress
import urllib.parse
from fastapi import HTTPException

# SSRF Protection
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
            
        # Block Loopback
        if ip.is_loopback:
            return False
            
        # Block Cloud Metadata (AWS, GCP, Azure)
        if str(ip) == "169.254.169.254":
            return False
            
        return True
    except Exception:
        return False

# Magic Byte Validation
def validate_file_magic_bytes(header: bytes) -> str:
    """
    Validates file integrity by examining the first few bytes (Magic Numbers).
    Never trust the file extension.
    """
    # PDF: %PDF- (25 50 44 46 2D)
    if header.startswith(b"%PDF-"):
        return "application/pdf"
        
    # Docx: ZIP signature PK.. (50 4B 03 04)
    if header.startswith(b"PK\x03\x04"):
        # Could be any zip, but we accept it as potential docx for the parser
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        
    raise HTTPException(status_code=400, detail="Invalid file type. Only PDF and DOCX are allowed based on file signatures.")
