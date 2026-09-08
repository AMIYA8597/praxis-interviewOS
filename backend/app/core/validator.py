import os
import yaml
import logging

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    pass

def validate_models_config():
    """
    Parses config/models.yaml and asserts that no <VERIFY_AT_BUILD> 
    placeholders remain. This forces the developer to explicitly verify
    and update external model IDs prior to launching the server.
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'config', 'models.yaml')
    
    if not os.path.exists(config_path):
        logger.warning(f"models.yaml not found at {config_path}. Skipping validation.")
        return

    with open(config_path, 'r') as file:
        try:
            config_data = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            raise ConfigurationError(f"Error parsing models.yaml: {exc}")

    aliases = config_data.get("aliases", {})
    
    for alias, providers in aliases.items():
        for provider_config in providers:
            model_id = provider_config.get("model", "")
            if "<VERIFY_AT_BUILD>" in model_id:
                raise ConfigurationError(
                    f"\n\n[CRITICAL FAILURE] Stale Model ID Detected!\n"
                    f"Alias '{alias}' for provider '{provider_config.get('provider')}' is using the placeholder '<VERIFY_AT_BUILD>'.\n"
                    f"You must manually verify the current API docs and replace this placeholder in config/models.yaml before the server will start.\n"
                )
                
    logger.info("Startup validation passed: No stale <VERIFY_AT_BUILD> placeholders found in models.yaml.")
