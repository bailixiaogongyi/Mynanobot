"""Custom model configuration storage.

This module provides functionality to store and retrieve custom model configurations
including token quotas, pricing, and other model-specific settings.
"""

import json
from pathlib import Path
from typing import Any


def get_custom_models_path() -> Path:
    """Get the path to custom models configuration file."""
    from nanobot.utils.helpers import get_data_path
    data_dir = get_data_path()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "custom_models.json"


def load_custom_models() -> dict[str, dict[str, Any]]:
    """Load custom model configurations from file.
    
    Returns:
        Dictionary mapping provider name to model configurations.
        Format: {provider_name: {model_id: model_config}}
    """
    path = get_custom_models_path()
    if not path.exists():
        return {}
    
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_custom_models(models: dict[str, dict[str, Any]]) -> None:
    """Save custom model configurations to file.
    
    Args:
        models: Dictionary mapping provider name to model configurations.
    """
    path = get_custom_models_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(models, f, indent=2, ensure_ascii=False)


def get_custom_model(provider: str, model_id: str) -> dict[str, Any] | None:
    """Get a specific custom model configuration.
    
    Args:
        provider: Provider name.
        model_id: Model identifier.
        
    Returns:
        Model configuration or None if not found.
    """
    models = load_custom_models()
    return models.get(provider, {}).get(model_id)


def set_custom_model(provider: str, model_id: str, config: dict[str, Any]) -> None:
    """Set a custom model configuration.
    
    Args:
        provider: Provider name.
        model_id: Model identifier.
        config: Model configuration.
    """
    models = load_custom_models()
    if provider not in models:
        models[provider] = {}
    models[provider][model_id] = config
    save_custom_models(models)


def delete_custom_model(provider: str, model_id: str) -> bool:
    """Delete a custom model configuration.
    
    Args:
        provider: Provider name.
        model_id: Model identifier.
        
    Returns:
        True if deleted, False if not found.
    """
    models = load_custom_models()
    if provider in models and model_id in models[provider]:
        del models[provider][model_id]
        if not models[provider]:
            del models[provider]
        save_custom_models(models)
        return True
    return False


def update_token_usage(provider: str, model_id: str, tokens_used: int) -> None:
    """Update token usage for a model.
    
    Args:
        provider: Provider name.
        model_id: Model identifier.
        tokens_used: Number of tokens used (in K).
    """
    model = get_custom_model(provider, model_id)
    if model:
        model["token_used"] = tokens_used
        set_custom_model(provider, model_id, model)
