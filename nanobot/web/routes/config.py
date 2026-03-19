"""Config API routes for Web UI.

This module provides configuration management API endpoints for the Web UI.
Sensitive information (API keys) are masked for security.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

SENSITIVE_FIELDS = [
    "api_key", "token", "secret", "password", "app_secret", "client_secret",
    "bridge_token", "bot_token", "app_token", "verification_token", "encrypt_key"
]


class ProviderModelInfo(BaseModel):
    """Provider model information for UI display."""

    model_id: str
    display_name: str
    description: str = ""
    max_tokens: int = 4096
    supports_vision: bool = False
    supports_function_calling: bool = True
    input_price: float = 0.0
    output_price: float = 0.0
    status: str = "active"
    currency: str = "CNY"
    token_quota: int = 0
    token_used: int = 0
    is_custom: bool = False


class ProviderInfo(BaseModel):
    """Provider configuration info."""

    name: str
    display_name: str = ""
    description: str = ""
    enabled: bool
    has_key: bool
    key_masked: str = ""
    api_base: str = ""
    is_oauth: bool = False
    is_gateway: bool = False
    is_local: bool = False
    models: list[ProviderModelInfo] = []


class ModelInfo(BaseModel):
    """Model information."""

    current: str
    available: list[str]
    enable_reasoning: bool = True


class KnowledgeConfigInfo(BaseModel):
    """Knowledge configuration info."""

    enabled: bool
    embedding_model: str
    persist_dir: str
    use_bm25: bool
    use_vector: bool
    chunk_size: int = 512
    chunk_overlap: int = 50
    default_top_k: int = 5
    use_graph: bool = True
    use_llm_extract: bool = True


class AgentDefaultsInfo(BaseModel):
    """Agent defaults configuration info."""

    model: str
    provider: str = ""
    max_tokens: int
    temperature: float
    max_tool_iterations: int
    memory_window: int
    enable_reasoning: bool
    workspace: str


class SubagentConfigInfo(BaseModel):
    """Subagent configuration info."""

    enabled: bool
    max_concurrent: int
    default_timeout: int
    workspace_isolation: bool


class UploadConfigInfo(BaseModel):
    """Upload configuration info."""

    enabled: bool
    max_file_size: int
    allowed_image_types: list[str]
    allowed_doc_types: list[str]


class GatewayConfigInfo(BaseModel):
    """Gateway configuration info."""

    host: str
    port: int
    web_ui_enabled: bool
    web_ui_host: str
    web_ui_port: int
    web_ui_auth_enabled: bool


class ToolsConfigInfo(BaseModel):
    """Tools configuration info."""

    restrict_to_workspace: bool
    exec_timeout: int
    mcp_servers_count: int
    web_search_enabled: bool
    weather_enabled: bool


class ChannelInfo(BaseModel):
    """Channel configuration info."""

    name: str
    display_name: str = ""
    description: str = ""
    enabled: bool
    has_credentials: bool
    credentials_masked: dict[str, str] = {}


class ImageGenerationConfigInfo(BaseModel):
    """Image generation configuration info."""

    enabled: bool = False
    provider: str = "dashscope"
    model: str = "wan21-turbo"
    api_key: Optional[str] = ""
    api_base: Optional[str] = ""


class ConfigOverview(BaseModel):
    """Configuration overview."""

    model: ModelInfo
    providers: list[ProviderInfo]
    knowledge: KnowledgeConfigInfo
    channels: list[ChannelInfo]
    tools: dict[str, Any] = {}
    agent_defaults: AgentDefaultsInfo
    subagent: SubagentConfigInfo
    upload: UploadConfigInfo
    gateway: GatewayConfigInfo
    tools_config: ToolsConfigInfo
    recent_models: list[dict[str, str]] = []
    image_generation: ImageGenerationConfigInfo = ImageGenerationConfigInfo()


class ModelUpdate(BaseModel):
    """Model update request."""

    model: str
    provider: Optional[str] = None
    enable_reasoning: Optional[bool] = None


class ProviderKeyUpdate(BaseModel):
    """Provider API key update request."""

    api_key: Optional[str] = None
    api_base: Optional[str] = None


class ChannelConfigUpdate(BaseModel):
    """Channel configuration update request."""

    enabled: bool = False
    token: Optional[str] = None
    bridge_token: Optional[str] = None
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    secret: Optional[str] = None
    bot_token: Optional[str] = None
    base_url: Optional[str] = None
    claw_token: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_username: Optional[str] = None
    imap_password: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None


class ToolConfigUpdate(BaseModel):
    """Tool configuration update request."""

    api_key: Optional[str] = None
    max_results: Optional[int] = None


def _mask_sensitive(value: str, show_chars: int = 4) -> str:
    """Mask sensitive value.

    Args:
        value: Sensitive value to mask.
        show_chars: Number of characters to show at start and end.

    Returns:
        Masked value.
    """
    if not value:
        return ""

    if len(value) <= show_chars * 2:
        return "*" * len(value)

    return f"{value[:show_chars]}{'*' * 8}{value[-show_chars:]}"


def _get_config(request):
    """Get config from app state."""
    return request.app.state.config


@router.get("/", response_model=ConfigOverview)
async def get_config(request: Request) -> ConfigOverview:
    """Get configuration overview.

    Sensitive values are masked.

    Returns:
        Configuration overview with masked sensitive data.
    """
    from nanobot.providers.registry import PROVIDERS, find_by_name

    try:
        from nanobot.providers.provider_models import get_models_by_provider
    except Exception:
        logger.warning("Failed to import provider_models module")
        get_models_by_provider = None

    config = _get_config(request)

    providers = []
    for spec in PROVIDERS:
        provider_config = getattr(config.providers, spec.name, None)
        if not provider_config:
            continue

        has_key = bool(provider_config.api_key)
        
        model_infos = []
        if get_models_by_provider:
            try:
                provider_models = get_models_by_provider(spec.name)
                model_infos = [
                    ProviderModelInfo(
                        model_id=pm.model_id,
                        display_name=pm.display_name,
                        description=pm.description,
                        max_tokens=pm.max_tokens,
                        supports_vision=pm.supports_vision,
                        supports_function_calling=pm.supports_function_calling,
                        input_price=pm.input_price,
                        output_price=pm.output_price,
                        status=pm.status,
                        currency=getattr(pm, 'currency', 'CNY'),
                        token_quota=getattr(pm, 'token_quota', 0),
                        token_used=getattr(pm, 'token_used', 0),
                        is_custom=getattr(pm, 'is_custom', False),
                    )
                    for pm in provider_models
                ]
            except Exception as e:
                logger.warning(f"Failed to get models for provider {spec.name}: {e}")

        providers.append(ProviderInfo(
            name=spec.name,
            display_name=spec.display_name or spec.name.title(),
            description=spec.description,
            enabled=has_key,
            has_key=has_key,
            key_masked=_mask_sensitive(provider_config.api_key) if has_key else "",
            api_base=provider_config.api_base or "",
            is_oauth=spec.is_oauth,
            is_gateway=spec.is_gateway,
            is_local=spec.is_local,
            models=model_infos,
        ))

    channels = [
        ChannelInfo(
            name="telegram",
            display_name="Telegram",
            description="Telegram 机器人",
            enabled=config.channels.telegram.enabled,
            has_credentials=bool(config.channels.telegram.token),
            credentials_masked={"token": _mask_sensitive(config.channels.telegram.token) if config.channels.telegram.token else ""},
        ),
        ChannelInfo(
            name="whatsapp",
            display_name="WhatsApp",
            description="WhatsApp 消息 (通过桥接服务)",
            enabled=config.channels.whatsapp.enabled,
            has_credentials=bool(config.channels.whatsapp.bridge_token),
            credentials_masked={"bridge_token": _mask_sensitive(config.channels.whatsapp.bridge_token) if config.channels.whatsapp.bridge_token else ""},
        ),
        ChannelInfo(
            name="feishu",
            display_name="飞书",
            description="飞书机器人",
            enabled=config.channels.feishu.enabled,
            has_credentials=bool(config.channels.feishu.app_id and config.channels.feishu.app_secret),
            credentials_masked={
                "app_id": config.channels.feishu.app_id or "",
                "app_secret": _mask_sensitive(config.channels.feishu.app_secret) if config.channels.feishu.app_secret else "",
            },
        ),
        ChannelInfo(
            name="dingtalk",
            display_name="钉钉",
            description="钉钉机器人",
            enabled=config.channels.dingtalk.enabled,
            has_credentials=bool(config.channels.dingtalk.client_id and config.channels.dingtalk.client_secret),
            credentials_masked={
                "client_id": config.channels.dingtalk.client_id or "",
                "client_secret": _mask_sensitive(config.channels.dingtalk.client_secret) if config.channels.dingtalk.client_secret else "",
            },
        ),
        ChannelInfo(
            name="discord",
            display_name="Discord",
            description="Discord 机器人",
            enabled=config.channels.discord.enabled,
            has_credentials=bool(config.channels.discord.token),
            credentials_masked={"token": _mask_sensitive(config.channels.discord.token) if config.channels.discord.token else ""},
        ),
        ChannelInfo(
            name="slack",
            display_name="Slack",
            description="Slack 应用",
            enabled=config.channels.slack.enabled,
            has_credentials=bool(config.channels.slack.bot_token),
            credentials_masked={"bot_token": _mask_sensitive(config.channels.slack.bot_token) if config.channels.slack.bot_token else ""},
        ),
        ChannelInfo(
            name="email",
            display_name="Email",
            description="邮件收发",
            enabled=config.channels.email.enabled,
            has_credentials=bool(config.channels.email.imap_host and config.channels.email.smtp_host),
            credentials_masked={
                "imap_host": config.channels.email.imap_host or "",
                "imap_username": config.channels.email.imap_username or "",
                "smtp_host": config.channels.email.smtp_host or "",
                "smtp_username": config.channels.email.smtp_username or "",
            },
        ),
        ChannelInfo(
            name="mochat",
            display_name="Mochat",
            description="Mochat 渠道",
            enabled=config.channels.mochat.enabled,
            has_credentials=bool(getattr(config.channels.mochat, 'clawToken', None) or getattr(config.channels.mochat, 'claw_token', "") or ""),
            credentials_masked={
                "base_url": getattr(config.channels.mochat, 'baseUrl', None) or getattr(config.channels.mochat, 'base_url', "") or "",
                "claw_token": _mask_sensitive(getattr(config.channels.mochat, 'clawToken', None) or getattr(config.channels.mochat, 'claw_token', "") or "") if (getattr(config.channels.mochat, 'clawToken', None) or getattr(config.channels.mochat, 'claw_token', "")) else "",
            },
        ),
        ChannelInfo(
            name="qq",
            display_name="QQ",
            description="QQ 机器人",
            enabled=config.channels.qq.enabled,
            has_credentials=bool(config.channels.qq.app_id and config.channels.qq.secret),
            credentials_masked={
                "app_id": config.channels.qq.app_id or "",
                "secret": _mask_sensitive(config.channels.qq.secret) if config.channels.qq.secret else "",
            },
        ),
    ]

    return ConfigOverview(
        model=ModelInfo(
            current=config.agents.defaults.model,
            available=_get_available_models(config),
            enable_reasoning=config.agents.defaults.enable_reasoning,
        ),
        providers=providers,
        knowledge=KnowledgeConfigInfo(
            enabled=config.tools.knowledge.index.enabled,
            embedding_model=config.tools.knowledge.index.embedding_model,
            persist_dir=config.tools.knowledge.index.persist_dir,
            use_bm25=config.tools.knowledge.index.use_bm25,
            use_vector=config.tools.knowledge.index.use_vector,
            chunk_size=config.tools.knowledge.index.chunk_size,
            chunk_overlap=config.tools.knowledge.index.chunk_overlap,
            default_top_k=config.tools.knowledge.search.default_top_k,
            use_graph=config.tools.knowledge.index.use_graph,
            use_llm_extract=config.tools.knowledge.index.use_llm_extract,
        ),
        channels=channels,
        tools={
            "web_search": getattr(config.tools.web.search, 'enabled', True),
            "web_search_api_key": getattr(config.tools.web.search, 'api_key', "") or "",
            "web_search_api_key_masked": _mask_sensitive(getattr(config.tools.web.search, 'api_key', "") or "") if getattr(config.tools.web.search, 'api_key', "") else "",
            "web_search_max_results": getattr(config.tools.web.search, 'max_results', 10) or 10,
            "weather": getattr(config.tools.weather.weather, 'enabled', True),
            "weather_api_key": getattr(config.tools.weather.weather, 'api_key', "") or "",
            "weather_api_key_masked": _mask_sensitive(getattr(config.tools.weather.weather, 'api_key', "") or "") if getattr(config.tools.weather.weather, 'api_key', "") else "",
            "mcp": config.tools.mcp_enabled if hasattr(config.tools, 'mcp_enabled') else False,
        },
        agent_defaults=AgentDefaultsInfo(
            model=config.agents.defaults.model,
            provider=getattr(config.agents.defaults, 'provider', ''),
            max_tokens=config.agents.defaults.max_tokens,
            temperature=config.agents.defaults.temperature,
            max_tool_iterations=config.agents.defaults.max_tool_iterations,
            memory_window=config.agents.defaults.memory_window,
            enable_reasoning=config.agents.defaults.enable_reasoning,
            workspace=config.agents.defaults.workspace,
        ),
        subagent=SubagentConfigInfo(
            enabled=config.agents.subagent.enabled,
            max_concurrent=config.agents.subagent.max_concurrent,
            default_timeout=config.agents.subagent.default_timeout,
            workspace_isolation=config.agents.subagent.workspace_isolation,
        ),
        image_generation=ImageGenerationConfigInfo(
            enabled=config.tools.image_generation.enabled,
            provider=config.tools.image_generation.provider,
            model=config.tools.image_generation.model,
            api_key="",  # Don't expose API key
            api_base=config.tools.image_generation.api_base,
        ),
        upload=UploadConfigInfo(
            enabled=config.upload.enabled,
            max_file_size=config.upload.max_file_size,
            allowed_image_types=config.upload.allowed_image_types,
            allowed_doc_types=config.upload.allowed_doc_types,
        ),
        gateway=GatewayConfigInfo(
            host=config.gateway.host,
            port=config.gateway.port,
            web_ui_enabled=config.gateway.web_ui.enabled,
            web_ui_host=config.gateway.web_ui.host,
            web_ui_port=config.gateway.web_ui.port,
            web_ui_auth_enabled=config.gateway.web_ui.auth.enabled,
        ),
        tools_config=ToolsConfigInfo(
            restrict_to_workspace=config.tools.restrict_to_workspace,
            exec_timeout=config.tools.exec.timeout,
            mcp_servers_count=len(config.tools.mcp_servers),
            web_search_enabled=bool(getattr(config.tools.web.search, 'apiKey', None) or getattr(config.tools.web.search, 'api_key', "") or ""),
            weather_enabled=bool(getattr(config.tools.weather.weather, 'apiKey', None) or getattr(config.tools.weather.weather, 'api_key', "") or ""),
        ),
        recent_models=config.agents.recent_models[:5],
    )


@router.post("/model")
async def set_model(update: ModelUpdate, request: Request) -> dict[str, Any]:
    """Set the default model.

    Args:
        update: Model update request.

    Returns:
        Update result.
    """
    from datetime import datetime

    config = _get_config(request)

    config.agents.defaults.model = update.model
    if update.provider:
        config.agents.defaults.provider = update.provider
    if update.enable_reasoning is not None:
        config.agents.defaults.enable_reasoning = update.enable_reasoning

    # Update recent_models
    current_model_info = {
        "model": update.model,
        "provider": update.provider,
        "timestamp": datetime.now().isoformat(),
    }
    recent_models = config.agents.recent_models
    # Remove if already exists
    recent_models = [m for m in recent_models if m.get("model") != update.model]
    # Add to front
    recent_models.insert(0, current_model_info)
    # Keep only last 5
    config.agents.recent_models = recent_models[:5]

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "updated",
        "model": update.model,
        "provider": config.agents.defaults.provider,
        "enable_reasoning": config.agents.defaults.enable_reasoning,
        "message": "Model updated successfully.",
    }


@router.post("/provider/{provider_name}")
async def set_provider_api_key(
    provider_name: str,
    update: ProviderKeyUpdate,
    request: Request,
) -> dict[str, Any]:
    """Set provider API key.

    Args:
        provider_name: Provider name.
        update: API key update request.

    Returns:
        Update result.
    """
    config = _get_config(request)

    provider = getattr(config.providers, provider_name, None)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_name}")

    if update.api_key is not None:
        provider.api_key = update.api_key
    if update.api_base:
        provider.api_base = update.api_base

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "updated",
        "provider": provider_name,
        "has_key": bool(update.api_key),
        "message": "API key updated. Restart may be required for changes to take effect.",
    }


class TestConnectionResult(BaseModel):
    """Result of provider connection test."""

    success: bool
    message: str
    model_used: str = ""
    latency_ms: int = 0


@router.post("/provider/{provider_name}/test", response_model=TestConnectionResult)
async def test_provider_connection(
    provider_name: str,
    request: Request,
) -> TestConnectionResult:
    """Test provider API connection.

    Args:
        provider_name: Provider name.

    Returns:
        Test result with success status and message.
    """
    import time

    config = _get_config(request)

    provider = getattr(config.providers, provider_name, None)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_name}")

    if not provider.api_key:
        return TestConnectionResult(
            success=False,
            message="API key not configured",
        )

    from nanobot.providers.provider_models import get_models_by_provider
    from nanobot.providers.registry import find_by_name, PROVIDERS
    from litellm import acompletion

    spec = find_by_name(provider_name)
    if not spec:
        return TestConnectionResult(
            success=False,
            message=f"Provider spec not found: {provider_name}",
        )

    models = get_models_by_provider(provider_name)
    if not models:
        default_model = "gpt-3.5-turbo"
        if spec.litellm_prefix:
            default_model = f"{spec.litellm_prefix}/{default_model}"
    else:
        first_model = models[0]
        model_id = first_model.model_id
        if spec.litellm_prefix and not model_id.startswith(spec.litellm_prefix):
            default_model = f"{spec.litellm_prefix}/{model_id}"
        else:
            default_model = model_id

    try:
        start_time = time.time()

        response = await acompletion(
            model=default_model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
            api_key=provider.api_key,
            api_base=provider.api_base or spec.default_api_base,
            timeout=30,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        return TestConnectionResult(
            success=True,
            message="Connection successful",
            model_used=default_model,
            latency_ms=latency_ms,
        )

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg or "invalid" in error_msg.lower():
            message = "Invalid API key"
        elif "403" in error_msg or "Forbidden" in error_msg:
            message = "Access forbidden - check API permissions"
        elif "404" in error_msg or "Not Found" in error_msg:
            message = "API endpoint not found"
        elif "timeout" in error_msg.lower():
            message = "Connection timeout"
        elif "connection" in error_msg.lower():
            message = "Connection failed - check network"
        else:
            message = f"Error: {error_msg[:100]}"

        return TestConnectionResult(
            success=False,
            message=message,
            model_used=default_model,
        )


@router.post("/knowledge/toggle")
async def toggle_knowledge(
    request: Request,
    enabled: bool = Query(..., description="Enable or disable knowledge retrieval"),
) -> dict[str, Any]:
    """Toggle knowledge retrieval.

    Args:
        enabled: Enable or disable.

    Returns:
        Update result.
    """
    config = _get_config(request)

    config.tools.knowledge.index.enabled = enabled

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "updated",
        "enabled": enabled,
        "message": f"Knowledge retrieval {'enabled' if enabled else 'disabled'}.",
    }


@router.post("/channel/{channel_name}")
async def set_channel_config(
    channel_name: str,
    update: ChannelConfigUpdate,
    request: Request,
) -> dict[str, Any]:
    """Set channel configuration.

    Args:
        channel_name: Channel name.
        update: Channel configuration update request.

    Returns:
        Update result.
    """
    config = _get_config(request)

    channel = getattr(config.channels, channel_name, None)
    if not channel:
        raise HTTPException(status_code=404, detail=f"Channel not found: {channel_name}")

    channel.enabled = update.enabled

    if channel_name == "telegram" and update.token:
        channel.token = update.token
    elif channel_name == "whatsapp" and update.bridge_token:
        channel.bridge_token = update.bridge_token
    elif channel_name == "feishu":
        if update.app_id:
            channel.app_id = update.app_id
        if update.app_secret:
            channel.app_secret = update.app_secret
    elif channel_name == "dingtalk":
        if update.client_id:
            channel.client_id = update.client_id
        if update.client_secret:
            channel.client_secret = update.client_secret
    elif channel_name == "discord" and update.token:
        channel.token = update.token
    elif channel_name == "slack" and update.bot_token:
        channel.bot_token = update.bot_token
    elif channel_name == "email":
        if update.imap_host:
            channel.imap_host = update.imap_host
        if update.imap_port:
            channel.imap_port = update.imap_port
        if update.imap_username:
            channel.imap_username = update.imap_username
        if update.imap_password:
            channel.imap_password = update.imap_password
        if update.smtp_host:
            channel.smtp_host = update.smtp_host
        if update.smtp_port:
            channel.smtp_port = update.smtp_port
        if update.smtp_username:
            channel.smtp_username = update.smtp_username
        if update.smtp_password:
            channel.smtp_password = update.smtp_password
    elif channel_name == "mochat":
        if update.base_url:
            channel.baseUrl = update.base_url
            channel.base_url = update.base_url
        if update.claw_token:
            channel.clawToken = update.claw_token
            channel.claw_token = update.claw_token
    elif channel_name == "qq":
        if update.app_id:
            channel.app_id = update.app_id
        if update.secret:
            channel.secret = update.secret

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "updated",
        "channel": channel_name,
        "enabled": update.enabled,
        "message": f"Channel {channel_name} configuration updated.",
    }


@router.post("/tool/{tool_name}")
async def set_tool_config(
    tool_name: str,
    update: ToolConfigUpdate,
    request: Request,
) -> dict[str, Any]:
    """Set tool configuration.

    Args:
        tool_name: Tool name.
        update: Tool configuration update request.

    Returns:
        Update result.
    """
    config = _get_config(request)

    if tool_name == "web_search":
        if update.api_key:
            config.tools.web.search.apiKey = update.api_key
            config.tools.web.search.api_key = update.api_key
        if update.max_results is not None:
            config.tools.web.search.maxResults = update.max_results
            config.tools.web.search.max_results = update.max_results
    elif tool_name == "weather":
        if update.api_key:
            config.tools.weather.weather.apiKey = update.api_key
            config.tools.weather.weather.api_key = update.api_key
    else:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "updated",
        "tool": tool_name,
        "message": f"Tool {tool_name} configuration updated. Restart required for changes to take effect.",
    }


class AgentDefaultsUpdate(BaseModel):
    """Agent defaults update request."""

    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    max_tool_iterations: Optional[int] = None
    memory_window: Optional[int] = None
    enable_reasoning: Optional[bool] = None
    workspace: Optional[str] = None


class SubagentUpdate(BaseModel):
    """Subagent configuration update request."""

    enabled: Optional[bool] = None
    max_concurrent: Optional[int] = None
    default_timeout: Optional[int] = None
    workspace_isolation: Optional[bool] = None


class UploadUpdate(BaseModel):
    """Upload configuration update request."""

    enabled: Optional[bool] = None
    max_file_size: Optional[int] = None


class GatewayUpdate(BaseModel):
    """Gateway configuration update request."""

    host: Optional[str] = None
    port: Optional[int] = None


class WebUIUpdate(BaseModel):
    """Web UI configuration update request."""

    enabled: Optional[bool] = None
    host: Optional[str] = None
    port: Optional[int] = None
    auth_enabled: Optional[bool] = None
    auth_password: Optional[str] = None


class ToolsConfigUpdate(BaseModel):
    """Tools configuration update request."""

    restrict_to_workspace: Optional[bool] = None
    exec_timeout: Optional[int] = None
    web_search_enabled: Optional[bool] = None
    web_search_api_key: Optional[str] = None
    web_search_max_results: Optional[int] = None
    weather_enabled: Optional[bool] = None
    weather_api_key: Optional[str] = None
    mcp_enabled: Optional[bool] = None


class KnowledgeUpdate(BaseModel):
    """Knowledge configuration update request."""

    enabled: Optional[bool] = None
    embedding_model: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    use_bm25: Optional[bool] = None
    use_vector: Optional[bool] = None
    default_top_k: Optional[int] = None
    use_graph: Optional[bool] = None
    use_llm_extract: Optional[bool] = None


@router.post("/agent/defaults")
async def set_agent_defaults(
    update: AgentDefaultsUpdate,
    request: Request,
) -> dict[str, Any]:
    """Set agent defaults configuration.

    Args:
        update: Agent defaults update request.

    Returns:
        Update result.
    """
    config = _get_config(request)

    if update.max_tokens is not None:
        config.agents.defaults.max_tokens = update.max_tokens
    if update.temperature is not None:
        config.agents.defaults.temperature = update.temperature
    if update.max_tool_iterations is not None:
        config.agents.defaults.max_tool_iterations = update.max_tool_iterations
    if update.memory_window is not None:
        config.agents.defaults.memory_window = update.memory_window
    if update.enable_reasoning is not None:
        config.agents.defaults.enable_reasoning = update.enable_reasoning
    if update.workspace is not None:
        config.agents.defaults.workspace = update.workspace

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "updated",
        "message": "Agent defaults updated.",
    }


@router.post("/subagent")
async def set_subagent_config(
    update: SubagentUpdate,
    request: Request,
) -> dict[str, Any]:
    """Set subagent configuration.

    Args:
        update: Subagent update request.

    Returns:
        Update result.
    """
    config = _get_config(request)

    if update.enabled is not None:
        config.agents.subagent.enabled = update.enabled
    if update.max_concurrent is not None:
        config.agents.subagent.max_concurrent = update.max_concurrent
    if update.default_timeout is not None:
        config.agents.subagent.default_timeout = update.default_timeout
    if update.workspace_isolation is not None:
        config.agents.subagent.workspace_isolation = update.workspace_isolation

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "updated",
        "message": "Subagent configuration updated.",
    }


@router.post("/upload")
async def set_upload_config(
    update: UploadUpdate,
    request: Request,
) -> dict[str, Any]:
    """Set upload configuration.

    Args:
        update: Upload update request.

    Returns:
        Update result.
    """
    config = _get_config(request)

    if update.enabled is not None:
        config.upload.enabled = update.enabled
    if update.max_file_size is not None:
        config.upload.max_file_size = update.max_file_size

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "updated",
        "message": "Upload configuration updated.",
    }


@router.post("/image_generation")
async def set_image_generation_config(
    update: ImageGenerationConfigInfo,
    request: Request,
) -> dict[str, Any]:
    """Set image generation configuration.

    Args:
        update: Image generation update request.

    Returns:
        Update result.
    """
    config = _get_config(request)

    if update.enabled is not None:
        config.tools.image_generation.enabled = update.enabled
    if update.provider is not None:
        config.tools.image_generation.provider = update.provider
    if update.model is not None:
        config.tools.image_generation.model = update.model
    if update.api_key is not None:
        config.tools.image_generation.api_key = update.api_key
    if update.api_base is not None:
        config.tools.image_generation.api_base = update.api_base

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "updated",
        "message": "Image generation configuration updated.",
    }


@router.post("/gateway")
async def set_gateway_config(
    update: GatewayUpdate,
    request: Request,
) -> dict[str, Any]:
    """Set gateway configuration.

    Args:
        update: Gateway update request.

    Returns:
        Update result.
    """
    config = _get_config(request)

    if update.host is not None:
        config.gateway.host = update.host
    if update.port is not None:
        config.gateway.port = update.port

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "updated",
        "message": "Gateway configuration updated. Restart required.",
    }


@router.post("/webui")
async def set_webui_config(
    update: WebUIUpdate,
    request: Request,
) -> dict[str, Any]:
    """Set Web UI configuration.

    Args:
        update: Web UI update request.

    Returns:
        Update result.
    """
    config = _get_config(request)

    if update.enabled is not None:
        config.gateway.web_ui.enabled = update.enabled
    if update.host is not None:
        config.gateway.web_ui.host = update.host
    if update.port is not None:
        config.gateway.web_ui.port = update.port
    if update.auth_enabled is not None:
        config.gateway.web_ui.auth.enabled = update.auth_enabled
    if update.auth_password is not None:
        config.gateway.web_ui.auth.password = update.auth_password

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "updated",
        "message": "Web UI configuration updated. Restart required.",
    }


@router.post("/tools/config")
async def set_tools_config(
    update: ToolsConfigUpdate,
    request: Request,
) -> dict[str, Any]:
    """Set tools configuration.

    Args:
        update: Tools config update request.

    Returns:
        Update result.
    """
    config = _get_config(request)

    if update.restrict_to_workspace is not None:
        config.tools.restrict_to_workspace = update.restrict_to_workspace
    if update.exec_timeout is not None:
        config.tools.exec.timeout = update.exec_timeout

    if update.web_search_enabled is not None:
        if not hasattr(config.tools.web.search, 'enabled'):
            config.tools.web.search.enabled = update.web_search_enabled
        else:
            config.tools.web.search.enabled = update.web_search_enabled
    if update.web_search_api_key is not None:
        config.tools.web.search.api_key = update.web_search_api_key
    if update.web_search_max_results is not None:
        config.tools.web.search.max_results = update.web_search_max_results

    if update.weather_enabled is not None:
        if not hasattr(config.tools.weather.weather, 'enabled'):
            config.tools.weather.weather.enabled = update.weather_enabled
        else:
            config.tools.weather.weather.enabled = update.weather_enabled
    if update.weather_api_key is not None:
        config.tools.weather.weather.api_key = update.weather_api_key

    if update.mcp_enabled is not None:
        config.tools.mcp_enabled = update.mcp_enabled

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "updated",
        "message": "Tools configuration updated.",
    }


@router.post("/knowledge/config")
async def set_knowledge_config(
    update: KnowledgeUpdate,
    request: Request,
) -> dict[str, Any]:
    """Set knowledge configuration.

    Args:
        update: Knowledge update request.

    Returns:
        Update result.
    """
    config = _get_config(request)

    if update.enabled is not None:
        config.tools.knowledge.index.enabled = update.enabled
    if update.embedding_model is not None:
        config.tools.knowledge.index.embedding_model = update.embedding_model
    if update.chunk_size is not None:
        config.tools.knowledge.index.chunk_size = update.chunk_size
    if update.chunk_overlap is not None:
        config.tools.knowledge.index.chunk_overlap = update.chunk_overlap
    if update.use_bm25 is not None:
        config.tools.knowledge.index.use_bm25 = update.use_bm25
    if update.use_vector is not None:
        config.tools.knowledge.index.use_vector = update.use_vector
    if update.default_top_k is not None:
        config.tools.knowledge.search.default_top_k = update.default_top_k
    if update.use_graph is not None:
        config.tools.knowledge.index.use_graph = update.use_graph
    if update.use_llm_extract is not None:
        config.tools.knowledge.index.use_llm_extract = update.use_llm_extract

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "updated",
        "message": "Knowledge configuration updated.",
    }


@router.get("/workspace")
async def get_workspace_info(request: Request) -> dict[str, Any]:
    """Get workspace information.

    Returns:
        Workspace information.
    """
    config = _get_config(request)
    workspace = config.workspace_path

    return {
        "path": str(workspace),
        "exists": workspace.exists(),
        "directories": _list_workspace_dirs(workspace),
    }


@router.get("/providers/models")
async def list_available_models(request: Request) -> list[dict[str, str]]:
    """List available models from all providers.

    Returns:
        List of available models.
    """
    config = _get_config(request)
    return [{"id": m, "name": m} for m in _get_available_models(config)]


def _get_available_models(config) -> list[str]:
    """Get list of available models.

    Args:
        config: Configuration.

    Returns:
        List of model identifiers.
    """
    common_models = [
        "anthropic/claude-opus-4-5",
        "anthropic/claude-sonnet-4-5",
        "anthropic/claude-3-5-sonnet",
        "anthropic/claude-3-opus",
        "openai/gpt-4o",
        "openai/gpt-4-turbo",
        "openai/gpt-4",
        "openai/gpt-3.5-turbo",
        "deepseek/deepseek-chat",
        "deepseek/deepseek-reasoner",
        "zhipu/glm-4.5-plus",
        "zhipu/glm-4.5-air",
        "zhipu/glm-4.5-flash",
        "zhipu/glm-4.5-long",
        "openrouter/anthropic/claude-opus-4",
        "openrouter/openai/gpt-4o",
        "groq/llama-3.3-70b-versatile",
        "groq/llama-3.1-8b-instant",
        "minimax/abab6.5s-chat",
        "siliconflow/deepseek-ai/DeepSeek-V3",
    ]

    current = config.agents.defaults.model
    if current and current not in common_models:
        common_models.insert(0, current)

    return common_models


def _list_workspace_dirs(workspace) -> list[str]:
    """List directories in workspace.

    Args:
        workspace: Workspace path.

    Returns:
        List of directory names.
    """
    if not workspace.exists():
        return []

    dirs = []
    for item in workspace.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            dirs.append(item.name)

    return sorted(dirs)


@router.post("/reset")
async def reset_config(request: Request) -> dict[str, Any]:
    """Reset configuration to defaults.

    Returns:
        Reset result.
    """
    from nanobot.config.schema import Config

    config = _get_config(request)
    default_config = Config()

    config.agents.defaults.model = default_config.agents.defaults.model
    config.tools.knowledge.index.enabled = default_config.tools.knowledge.index.enabled

    from nanobot.config.loader import save_config, load_config, get_config_path
    save_config(config)
    
    config_path = get_config_path()
    request.app.state.config = load_config(config_path)

    return {
        "status": "reset",
        "message": "Configuration reset to defaults. Restart required for some changes to take effect.",
    }


@router.post("/restart")
async def restart_service(request: Request) -> dict[str, Any]:
    """Restart the nanobot service.

    Supports both Docker and Windows direct execution environments.

    Returns:
        Restart result (response may not be received if shutdown is quick).
    """
    import asyncio
    import os
    import signal
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    logger.info("Service restart requested via Web UI")

    def is_docker() -> bool:
        if os.path.exists("/.dockerenv"):
            return True
        try:
            with open("/proc/1/cgroup", "r") as f:
                return "docker" in f.read() or "kubepods" in f.read()
        except Exception:
            return False

    def get_restart_marker_file() -> Path:
        data_dir = Path.home() / ".nanobot"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / ".restart_marker"

    def write_restart_marker():
        marker_file = get_restart_marker_file()
        marker_file.write_text(str(os.getpid()))
        logger.info(f"Written restart marker: {marker_file}")

    def clear_restart_marker():
        marker_file = get_restart_marker_file()
        if marker_file.exists():
            marker_file.unlink()
            logger.info(f"Cleared restart marker: {marker_file}")

    async def delayed_shutdown():
        await asyncio.sleep(0.5)
        logger.info("Shutting down for restart...")
        
        in_docker = is_docker()
        
        if in_docker:
            logger.info("Running in Docker, exiting for container restart...")
            os._exit(0)
        elif sys.platform == "win32":
            logger.info("Running on Windows, spawning new process...")
            write_restart_marker()
            
            log_dir = Path.home() / ".nanobot" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "restart.log"
            
            try:
                exe = sys.executable
                cwd = os.getcwd()
                
                with open(log_file, "a", encoding="utf-8") as log_f:
                    log_f.write(f"\n--- Restart at {__import__('datetime').datetime.now()} ---\n")
                    log_f.write(f"Python: {exe}\n")
                    log_f.write(f"CWD: {cwd}\n")
                    log_f.flush()
                    
                    process = subprocess.Popen(
                        [exe, "-m", "nanobot", "gateway"],
                        cwd=cwd,
                        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                        stdout=log_f,
                        stderr=log_f,
                    )
                    log_f.write(f"New process PID: {process.pid}\n")
                    log_f.flush()
                    
                logger.info(f"Spawned new process with PID: {process.pid}")
                
                await asyncio.sleep(1)
                
                try:
                    exit_code = process.poll()
                    if exit_code is not None:
                        logger.error(f"New process exited immediately with code: {exit_code}")
                        clear_restart_marker()
                    else:
                        logger.info("New process is running")
                except Exception as poll_err:
                    logger.warning(f"Could not check new process status: {poll_err}")
                    
            except Exception as e:
                logger.error(f"Failed to spawn new process: {e}")
                clear_restart_marker()
            finally:
                os._exit(0)
        else:
            logger.info("Running on Unix, sending SIGTERM...")
            try:
                signal.raise_signal(signal.SIGTERM)
            except Exception as e:
                logger.error(f"Failed to send SIGTERM: {e}")
                os._exit(0)

    asyncio.create_task(delayed_shutdown())

    return {
        "status": "restarting",
        "message": "Service is restarting. Please wait and refresh the page.",
    }


@router.get("/restart/status")
async def get_restart_status(request: Request) -> dict[str, Any]:
    """Check if the service has restarted successfully.
    
    Returns:
        Restart status information.
    """
    import os
    from pathlib import Path
    import time
    
    def get_restart_marker_file() -> Path:
        data_dir = Path.home() / ".nanobot"
        return data_dir / ".restart_marker"
    
    marker_file = get_restart_marker_file()
    
    if marker_file.exists():
        try:
            old_pid = int(marker_file.read_text().strip())
            current_pid = os.getpid()
            
            if old_pid != current_pid:
                marker_file.unlink()
                return {
                    "status": "restarted",
                    "message": "Service has restarted successfully.",
                    "old_pid": old_pid,
                    "new_pid": current_pid,
                }
            else:
                return {
                    "status": "restarting",
                    "message": "Service is still restarting...",
                }
        except Exception as e:
            return {
                "status": "unknown",
                "message": f"Could not determine restart status: {e}",
            }
    
    return {
        "status": "no_restart",
        "message": "No restart in progress.",
    }


class CustomModelConfig(BaseModel):
    """Custom model configuration."""

    model_id: str
    display_name: str = ""
    description: str = ""
    max_tokens: int = 4096
    supports_vision: bool = False
    supports_function_calling: bool = True
    supports_streaming: bool = True
    input_price: float = 0.0
    output_price: float = 0.0
    status: str = "active"
    currency: str = "CNY"
    token_quota: int = 0
    token_used: int = 0


@router.get("/provider/{provider_name}/models/custom")
async def get_custom_models(provider_name: str) -> list[dict[str, Any]]:
    """Get custom models for a provider.
    
    Args:
        provider_name: Provider name.
        
    Returns:
        List of custom model configurations.
    """
    from nanobot.config.custom_models import load_custom_models
    
    models = load_custom_models()
    provider_models = models.get(provider_name, {})
    return list(provider_models.values())


@router.post("/provider/{provider_name}/models/custom")
async def save_custom_model(
    provider_name: str,
    model_config: CustomModelConfig,
    request: Request,
) -> dict[str, Any]:
    """Save a custom model configuration.
    
    Args:
        provider_name: Provider name.
        model_config: Model configuration.
        
    Returns:
        Save result.
    """
    from nanobot.config.custom_models import set_custom_model
    
    config_dict = model_config.model_dump()
    config_dict["is_custom"] = True
    set_custom_model(provider_name, model_config.model_id, config_dict)
    
    return {
        "status": "saved",
        "provider": provider_name,
        "model_id": model_config.model_id,
        "message": "Custom model saved successfully.",
    }


@router.delete("/provider/{provider_name}/models/custom")
async def delete_custom_model(
    provider_name: str,
    model_id: str,
    request: Request,
) -> dict[str, Any]:
    """Delete a model configuration (custom or predefined).

    Args:
        provider_name: Provider name.
        model_id: Model identifier (passed as query parameter since it may contain /).

    Returns:
        Delete result.
    """
    from nanobot.config.custom_models import delete_custom_model as delete_model, load_custom_models

    custom_models = load_custom_models()
    provider_models = custom_models.get(provider_name, {})

    if model_id in provider_models:
        deleted = delete_model(provider_name, model_id)
        if deleted:
            return {
                "status": "deleted",
                "provider": provider_name,
                "model_id": model_id,
                "message": "Custom model deleted successfully.",
            }

    return {
        "status": "deleted",
        "provider": provider_name,
        "model_id": model_id,
        "message": "Model reference removed (predefined model).",
    }
