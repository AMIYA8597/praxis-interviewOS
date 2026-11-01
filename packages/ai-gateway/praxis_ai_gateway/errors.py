class ProviderError(Exception):
    pass

class ProviderAuthError(ProviderError):
    """Bad or missing API key. Not retryable."""
    pass

class ProviderRateLimitError(ProviderError):
    """Rate limited by the provider. Retryable after backoff."""
    pass

class ProviderTimeoutError(ProviderError):
    """Request to the provider timed out. Retryable."""
    pass

class ProviderServerError(ProviderError):
    """Provider returned a 5xx error. Retryable."""
    pass

class AIProviderNotConfiguredError(ProviderError):
    """Raised when no compatible, configured AI provider is available for the requested task."""
    error_code = "AI_PROVIDER_NOT_CONFIGURED"

