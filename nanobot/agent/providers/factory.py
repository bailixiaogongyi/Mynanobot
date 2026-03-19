"""Provider factory for creating independent provider instances for subagents."""

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from nanobot.config.schema import Config
    from nanobot.agent.roles.models import RoleModelConfig
    from nanobot.providers.base import LLMProvider


class ProviderFactory:
    """Factory for creating LLM provider instances for subagents.
    
    This factory enables each subagent role to use a different model/provider,
    allowing for optimal performance and cost efficiency:
    - Code tasks can use Claude/GPT-4 for better coding
    - Document tasks can use DeepSeek for Chinese text
    - Analysis tasks can use specialized models
    
    The factory supports:
    1. Role-specific model configuration (overrides main config)
    2. Independent API keys per role (optional)
    3. Fallback to main agent configuration
    """
    
    def __init__(self, main_config: "Config"):
        """Initialize the provider factory.
        
        Args:
            main_config: The main configuration object.
        """
        self.main_config = main_config
    
    def create_provider(
        self,
        role_model_config: "RoleModelConfig | None" = None,
    ) -> tuple["LLMProvider", str]:
        """Create a provider instance for a subagent.
        
        Args:
            role_model_config: Optional role-specific model configuration.
                If None, uses the main agent's configuration.
                
        Returns:
            Tuple of (provider_instance, model_name)
        """
        from nanobot.providers.litellm_provider import LiteLLMProvider
        from nanobot.providers.custom_provider import CustomProvider
        from nanobot.providers.registry import find_by_name
        
        if role_model_config is None or role_model_config.model is None:
            return self._create_from_main_config()
        
        model = role_model_config.model
        provider_name = role_model_config.provider
        
        if provider_name:
            provider_name = provider_name.lower()
        
        api_key = None
        api_base = None
        
        if role_model_config.api_key:
            api_key = role_model_config.api_key
            api_base = role_model_config.api_base
        else:
            provider_config = self._get_provider_config(provider_name)
            if provider_config:
                api_key = provider_config.api_key
                api_base = role_model_config.api_base or provider_config.api_base
        
        if provider_name == "custom":
            provider = CustomProvider(
                api_key=api_key or "no-key",
                api_base=api_base or "http://localhost:8000/v1",
                default_model=model,
            )
            logger.debug(f"Created CustomProvider for model: {model}")
            return provider, model
        
        if provider_name == "openai_codex":
            from nanobot.providers.openai_codex import OpenAICodexProvider
            provider = OpenAICodexProvider(default_model=model)
            logger.debug(f"Created OpenAICodexProvider for model: {model}")
            return provider, model
        
        if provider_name == "github_copilot":
            from nanobot.providers.github_copilot import GitHubCopilotProvider
            provider = GitHubCopilotProvider(default_model=model)
            logger.debug(f"Created GitHubCopilotProvider for model: {model}")
            return provider, model
        
        spec = None
        if provider_name:
            spec = find_by_name(provider_name)
        
        extra_headers = None
        if spec:
            provider_config = self._get_provider_config(provider_name)
            if provider_config and provider_config.extra_headers:
                extra_headers = provider_config.extra_headers
        
        provider = LiteLLMProvider(
            api_key=api_key,
            api_base=api_base,
            default_model=model,
            extra_headers=extra_headers,
            provider_name=provider_name,
        )
        
        logger.debug(f"Created LiteLLMProvider for role: provider={provider_name}, model={model}")
        return provider, model
    
    def _create_from_main_config(self) -> tuple["LLMProvider", str]:
        """Create provider using main agent configuration.
        
        Returns:
            Tuple of (provider_instance, model_name)
        """
        from nanobot.cli.commands import _make_provider
        
        model = self.main_config.agents.defaults.model
        provider = _make_provider(self.main_config)
        
        logger.debug(f"Created provider from main config: model={model}")
        return provider, model
    
    def _get_provider_config(self, provider_name: str | None):
        """Get provider configuration from main config.
        
        Args:
            provider_name: Name of the provider.
            
        Returns:
            Provider configuration object or None.
        """
        if not provider_name:
            return None
        
        return getattr(self.main_config.providers, provider_name, None)
    
    def get_model_info(self, role_model_config: "RoleModelConfig | None" = None) -> dict:
        """Get model information for display purposes.
        
        Args:
            role_model_config: Optional role-specific model configuration.
            
        Returns:
            Dictionary with model information.
        """
        if role_model_config and role_model_config.model:
            return {
                "provider": role_model_config.provider,
                "model": role_model_config.model,
                "temperature": role_model_config.temperature,
                "max_tokens": role_model_config.max_tokens,
                "is_custom": True,
            }
        
        return {
            "provider": self.main_config.get_provider_name(self.main_config.agents.defaults.model),
            "model": self.main_config.agents.defaults.model,
            "temperature": self.main_config.agents.defaults.temperature,
            "max_tokens": self.main_config.agents.defaults.max_tokens,
            "is_custom": False,
        }
