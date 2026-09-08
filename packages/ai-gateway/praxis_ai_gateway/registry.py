import yaml
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from praxis_ai_gateway.base import ProviderCapabilities, LLMProvider

class ConfigurationError(Exception):
    pass

class ModelRegistry:
    def __init__(self, config_path: str | Path):
        self._aliases: Dict[str, List[Dict[str, Any]]] = {}
        self._load_config(config_path)

    def _load_config(self, config_path: str | Path):
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        aliases = data.get("aliases", {})
        if not aliases:
            # Maybe the top-level is aliases
            aliases = data
            if "aliases" in aliases:
                aliases = aliases["aliases"]
                
        for alias, configs in aliases.items():
            for config in configs:
                model_name = config.get("model", "")
                if "<VERIFY_AT_BUILD>" in model_name:
                    raise ConfigurationError(
                        f"Unverified placeholder <VERIFY_AT_BUILD> found in config for alias '{alias}'"
                    )
        
        self._aliases = aliases

    def candidates_for(self, alias: str) -> List[Dict[str, Any]]:
        """Returns ordered list of dicts with provider details."""
        return self._aliases.get(alias, [])

    def filter_candidates(
        self,
        task: str,
        providers: Dict[str, LLMProvider],
        required_capabilities: Optional[ProviderCapabilities] = None,
        local_only: bool = False
    ) -> List[Tuple[LLMProvider, Dict[str, Any]]]:
        """
        Return valid (Provider, config_dict) tuples.
        """
        candidates = self.candidates_for(task)
        valid = []
        
        for config in candidates:
            provider_name = config["provider"]
            if provider_name not in providers:
                continue
                
            provider = providers[provider_name]
            caps = provider.capabilities()
            
            if local_only and not caps.is_local:
                continue
                
            if required_capabilities:
                # Check that all Truthy requirements in required_capabilities are met by caps
                # Pydantic v2 dump
                req_dict = required_capabilities.model_dump(exclude_unset=True)
                cap_dict = caps.model_dump()
                
                meets_requirements = True
                for k, v in req_dict.items():
                    if isinstance(v, bool) and v: # Only enforce True flags
                        if not cap_dict.get(k):
                            meets_requirements = False
                            break
                    elif isinstance(v, int) and k == "max_context_tokens":
                        if cap_dict.get(k, 0) < v:
                            meets_requirements = False
                            break
                            
                if not meets_requirements:
                    continue
                    
            valid.append((provider, config))
            
        return valid
