import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class BudgetGuardException(Exception):
    pass

class AIGateway:
    """
    Central AI router that enforces ZERO_SPEND_MODE hierarchy.
    Hierarchy:
    1. Local/Open Source
    2. Free Cloud Tier
    3. User BYO Key
    4. Paid (Never auto)
    """
    
    def __init__(self):
        self.zero_spend_mode = settings.ZERO_SPEND_MODE
        
    def _check_budget(self, provider_tier: str):
        if self.zero_spend_mode and provider_tier not in ["LOCAL", "FREE_CLOUD"]:
            raise BudgetGuardException(
                f"Blocked billable call to {provider_tier}. ZERO_SPEND_MODE is active."
            )

    async def generate(self, prompt: str, provider: str = "LOCAL", model: str = "faster-whisper"):
        """
        Mock generate function that enforces the budget guard.
        """
        provider_tier = "LOCAL"
        if provider == "openai" or provider == "anthropic":
            provider_tier = "PAID"
        elif provider == "groq" or provider == "gemini":
            provider_tier = "FREE_CLOUD"
            
        self._check_budget(provider_tier)
        
        # In actual implementation, we map this to the specific provider SDK
        logger.info(f"Routing request to {provider} ({model})")
        return "Mock response from Gateway"

gateway = AIGateway()
