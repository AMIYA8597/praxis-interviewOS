import yaml
import os
import logging
from typing import Optional, Dict

from packages.ai_gateway.base import LLMProvider
from packages.ai_gateway.budget import BudgetGuard
from packages.ai_gateway.resilience import CircuitBreaker

logger = logging.getLogger(__name__)

class RoutingContext:
    def __init__(self, fallback_count: int = 0):
        self.fallback_count = fallback_count

class NoAvailableProviderException(Exception):
    pass

class GatewayRouter:
    def __init__(self):
        self.budget_guard = BudgetGuard()
        self.local_only_mode = os.environ.get("LOCAL_ONLY_MODE", "true").lower() == "true"
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        with open("d:/work/interviewOS/config/models.yaml", "r") as f:
            self.config = yaml.safe_load(f)

    def _get_adapter(self, provider_name: str, model_id: str) -> Optional[LLMProvider]:
        if provider_name == "ollama":
            from packages.ai_gateway.providers.ollama import OllamaProvider
            return OllamaProvider(model_id)
        # Note: Groq, Gemini, etc., would be instantiated here.
        # Stubbing Groq for fallback tests:
        if provider_name == "groq":
            from packages.ai_gateway.providers.groq import GroqProvider
            return GroqProvider(model_id)
        return None

    def get_circuit_breaker(self, key: str) -> CircuitBreaker:
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = CircuitBreaker()
        return self.circuit_breakers[key]

    def route(self, task: str, context: RoutingContext) -> LLMProvider:
        if task not in self.config.get("aliases", {}):
            raise ValueError(f"Unknown routing task: {task}")
            
        candidates = self.config["aliases"][task]
        
        for candidate in candidates:
            provider_name = candidate["provider"]
            model_id = candidate["model"]
            cb_key = f"{provider_name}_{model_id}"
            
            # 1. Instantiate Adapter
            adapter = self._get_adapter(provider_name, model_id)
            if not adapter or not adapter.is_configured():
                continue
                
            caps = adapter.capabilities()
                
            # 2. Local Only Filter
            if self.local_only_mode and not caps.is_local:
                continue
                
            # 3. Budget Guard
            try:
                self.budget_guard.authorize(adapter)
            except Exception as e:
                logger.info(f"Skipping {provider_name}: {str(e)}")
                continue
                
            # 4. Circuit Breaker
            cb = self.get_circuit_breaker(cb_key)
            if not cb.can_execute():
                logger.warning(f"Skipping {provider_name} due to OPEN circuit breaker.")
                continue
                
            # Return first valid
            return adapter
            
        raise NoAvailableProviderException(f"No available providers for task: {task}")
