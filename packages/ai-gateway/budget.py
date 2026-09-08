import os
import logging
from packages.ai_gateway.base import LLMProvider

logger = logging.getLogger(__name__)

class BudgetGuardException(Exception):
    pass

class BudgetGuard:
    def __init__(self):
        self.zero_spend_mode = os.environ.get("ZERO_SPEND_MODE", "true").lower() == "true"

    def authorize(self, provider: LLMProvider):
        caps = provider.capabilities()
        if self.zero_spend_mode and not (caps.is_free_tier or caps.is_local):
            raise BudgetGuardException("Capability unavailable in zero-spend mode. Enable provider in Settings to use it.")
