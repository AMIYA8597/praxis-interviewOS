"""
PRAXIS InterviewOS — SSRF Defense Regression Suite
Proves that private subnets, loopback addresses, and cloud metadata endpoints are blocked.
"""
from backend.app.core.security import is_safe_url


def test_public_allowed_domains_pass():
    assert is_safe_url("https://api.openai.com/v1/chat/completions") is True
    assert is_safe_url("https://openrouter.ai/api/v1") is True
    assert is_safe_url("https://generativelanguage.googleapis.com") is True


def test_cloud_metadata_is_blocked():
    # AWS/GCP/Azure instance metadata service
    assert is_safe_url("http://169.254.169.254/computeMetadata/v1/") is False
    assert is_safe_url("http://169.254.169.254/latest/meta-data/") is False


def test_loopback_is_blocked():
    assert is_safe_url("http://127.0.0.1:8000/api") is False
    assert is_safe_url("http://localhost:5432") is False


def test_private_subnets_are_blocked():
    # 10.0.0.0/8
    assert is_safe_url("http://10.0.0.1:8080") is False
    # 192.168.0.0/16
    assert is_safe_url("http://192.168.1.100/admin") is False
    # 172.16.0.0/12
    assert is_safe_url("http://172.20.0.5:6379") is False


def test_malformed_urls_are_rejected():
    assert is_safe_url("") is False
    assert is_safe_url("not_a_url") is False
    assert is_safe_url("http://") is False
    assert is_safe_url("file:///etc/passwd") is False
