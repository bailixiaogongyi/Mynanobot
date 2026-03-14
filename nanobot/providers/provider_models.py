"""Provider model specifications.

This module defines model metadata for each provider, including:
- Model capabilities (vision, function calling, etc.)
- Context window sizes
- Pricing information
- Status (active, beta, deprecated)

Adding a new model:
  1. Add a ProviderModelSpec to PROVIDER_MODELS below.
  2. The model will automatically appear in the WebUI when the provider is expanded.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProviderModelSpec:
    """Model specification for a specific provider.

    Note: The same model may have different specs on different providers.
    For example, GLM-4-Flash has 128K context on Zhipu but 16K on SiliconFlow.
    """

    provider: str                    # Provider name (must match ProviderSpec.name)
    model_id: str                    # Model identifier used in API calls
    display_name: str                # Human-readable name for UI display
    description: str = ""            # Brief description of the model
    provider_model_id: str = ""      # Actual model ID at provider (if different from model_id)

    # Capabilities
    max_tokens: int = 4096           # Maximum context window (total input + output)
    supports_vision: bool = False    # Supports image input
    supports_function_calling: bool = True  # Supports tool/function calls
    supports_streaming: bool = True  # Supports streaming responses

    # Pricing (per 1M tokens)
    input_price: float = 0.0         # Price per 1M input tokens
    output_price: float = 0.0        # Price per 1M output tokens
    currency: str = "CNY"            # Currency: CNY or USD

    # Token quota
    token_quota: int = 0             # Token quota in K (0 means unlimited)
    token_used: int = 0              # Token used in K

    # Status
    status: str = "active"           # active, beta, deprecated
    is_custom: bool = False          # Whether this is a custom model

    @property
    def id(self) -> str:
        """Full model ID in format: provider/model_id"""
        return f"{self.provider}/{self.model_id}"


# ---------------------------------------------------------------------------
# PROVIDER_MODELS — the registry of models per provider
# ---------------------------------------------------------------------------

PROVIDER_MODELS: tuple[ProviderModelSpec, ...] = (

    # =========================================================================
    # SCNet (国家超算互联网)
    # =========================================================================
    ProviderModelSpec(
        provider="scnet",
        model_id="DeepSeek-R1-Distill-Qwen-7B",
        display_name="DeepSeek R1 Distill Qwen 7B",
        description="DeepSeek R1 蒸馏模型，7B 参数，适合轻量推理任务",
        max_tokens=65536,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="scnet",
        model_id="DeepSeek-V3",
        display_name="DeepSeek V3",
        description="DeepSeek V3 通用大模型，平衡性能与成本",
        max_tokens=65536,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="scnet",
        model_id="DeepSeek-R1",
        display_name="DeepSeek R1",
        description="DeepSeek R1 推理模型，擅长复杂推理任务",
        max_tokens=65536,
        supports_function_calling=True,
    ),

    # =========================================================================
    # Qiniu (七牛云)
    # =========================================================================
    ProviderModelSpec(
        provider="qiniu",
        model_id="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
        description="Google Gemini 2.5 Flash 多模态模型，支持视觉输入",
        max_tokens=1048576,
        supports_vision=True,
        supports_function_calling=True,
    ),

    # =========================================================================
    # Baishan (白山智算)
    # =========================================================================
    ProviderModelSpec(
        provider="baishan",
        model_id="DeepSeek-R1-0528",
        display_name="DeepSeek R1 0528",
        description="DeepSeek R1 推理模型",
        max_tokens=65536,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="baishan",
        model_id="DeepSeek-V3",
        display_name="DeepSeek V3",
        description="DeepSeek V3 通用模型",
        max_tokens=65536,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="baishan",
        model_id="Qwen3-32B-FP8",
        display_name="Qwen3 32B",
        description="通义千问 3 32B 模型",
        max_tokens=32768,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="baishan",
        model_id="Qwen3-235B-A22B",
        display_name="Qwen3 235B",
        description="通义千问 3 235B 大参数模型",
        max_tokens=32768,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="baishan",
        model_id="Qwen2.5-72B-Instruct",
        display_name="Qwen2.5 72B",
        description="通义千问 2.5 72B 模型",
        max_tokens=131072,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="baishan",
        model_id="Qwen2.5-72B-Instruct-128K",
        display_name="Qwen2.5 72B 128K",
        description="通义千问 2.5 72B 长上下文版本",
        max_tokens=131072,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="baishan",
        model_id="Qwen2.5-VL-7B-Instruct",
        display_name="Qwen2.5 VL 7B",
        description="通义千问视觉模型，支持图像理解",
        max_tokens=32768,
        supports_vision=True,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="baishan",
        model_id="GLM-4.5",
        display_name="GLM 4.5",
        description="智谱 GLM 4.5 模型",
        max_tokens=131072,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="baishan",
        model_id="Kimi-K2-Instruct",
        display_name="Kimi K2",
        description="月之暗面 Kimi K2 模型",
        max_tokens=131072,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="baishan",
        model_id="DeepSeek-R1-Distill-Qwen-14B",
        display_name="DeepSeek R1 Distill 14B",
        description="DeepSeek R1 蒸馏模型，14B 参数",
        max_tokens=65536,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="baishan",
        model_id="DeepSeek-R1-Distill-Qwen-32B",
        display_name="DeepSeek R1 Distill 32B",
        description="DeepSeek R1 蒸馏模型，32B 参数",
        max_tokens=65536,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="baishan",
        model_id="Qwen3-Coder-480B-A35B",
        display_name="Qwen3 Coder 480B",
        description="通义千问代码模型，专为代码生成优化",
        max_tokens=32768,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="baishan",
        model_id="bge-m3",
        display_name="BGE M3",
        description="向量嵌入模型",
        max_tokens=8192,
        supports_function_calling=False,
    ),
    ProviderModelSpec(
        provider="baishan",
        model_id="bge-reranker-v2-m3",
        display_name="BGE Reranker V2",
        description="重排序模型",
        max_tokens=8192,
        supports_function_calling=False,
    ),

    # =========================================================================
    # SiliconFlow (硅基流动)
    # =========================================================================
    ProviderModelSpec(
        provider="siliconflow",
        model_id="deepseek-ai/DeepSeek-V3",
        display_name="DeepSeek V3",
        description="DeepSeek V3 通用模型",
        max_tokens=65536,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="siliconflow",
        model_id="deepseek-ai/DeepSeek-R1",
        display_name="DeepSeek R1",
        description="DeepSeek R1 推理模型",
        max_tokens=65536,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="siliconflow",
        model_id="Qwen/Qwen2.5-72B-Instruct",
        display_name="Qwen2.5 72B",
        description="通义千问 2.5 72B 模型",
        max_tokens=32768,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="siliconflow",
        model_id="THUDM/glm-4-9b-chat",
        display_name="GLM-4 9B",
        description="智谱 GLM-4 9B 模型",
        max_tokens=131072,
        supports_function_calling=True,
    ),

    # =========================================================================
    # DeepSeek
    # =========================================================================
    ProviderModelSpec(
        provider="deepseek",
        model_id="deepseek-chat",
        display_name="DeepSeek Chat",
        description="DeepSeek 对话模型，适合日常对话和通用任务",
        max_tokens=64000,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="deepseek",
        model_id="deepseek-reasoner",
        display_name="DeepSeek Reasoner",
        description="DeepSeek 推理模型，擅长复杂推理任务",
        max_tokens=64000,
        supports_function_calling=True,
    ),

    # =========================================================================
    # Zhipu (智谱)
    # =========================================================================
    ProviderModelSpec(
        provider="zhipu",
        model_id="glm-4-plus",
        display_name="GLM-4 Plus",
        description="智谱 GLM-4 Plus 高级模型",
        max_tokens=128000,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="zhipu",
        model_id="glm-4-air",
        display_name="GLM-4 Air",
        description="智谱 GLM-4 Air 轻量模型",
        max_tokens=128000,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="zhipu",
        model_id="glm-4-flash",
        display_name="GLM-4 Flash",
        description="智谱 GLM-4 Flash 快速模型",
        max_tokens=128000,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="zhipu",
        model_id="glm-4-long",
        display_name="GLM-4 Long",
        description="智谱 GLM-4 长上下文模型",
        max_tokens=1024000,
        supports_function_calling=True,
    ),

    # =========================================================================
    # Anthropic
    # =========================================================================
    ProviderModelSpec(
        provider="anthropic",
        model_id="claude-opus-4-5",
        display_name="Claude Opus 4.5",
        description="Anthropic 最强模型，适合复杂任务",
        max_tokens=200000,
        supports_vision=True,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="anthropic",
        model_id="claude-sonnet-4-5",
        display_name="Claude Sonnet 4.5",
        description="Anthropic 平衡模型，性能与速度兼顾",
        max_tokens=200000,
        supports_vision=True,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="anthropic",
        model_id="claude-3-5-sonnet",
        display_name="Claude 3.5 Sonnet",
        description="Claude 3.5 Sonnet 模型",
        max_tokens=200000,
        supports_vision=True,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="anthropic",
        model_id="claude-3-opus",
        display_name="Claude 3 Opus",
        description="Claude 3 Opus 高级模型",
        max_tokens=200000,
        supports_vision=True,
        supports_function_calling=True,
    ),

    # =========================================================================
    # OpenAI
    # =========================================================================
    ProviderModelSpec(
        provider="openai",
        model_id="gpt-4o",
        display_name="GPT-4o",
        description="OpenAI GPT-4o 多模态模型",
        max_tokens=128000,
        supports_vision=True,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="openai",
        model_id="gpt-4-turbo",
        display_name="GPT-4 Turbo",
        description="OpenAI GPT-4 Turbo 模型",
        max_tokens=128000,
        supports_vision=True,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="openai",
        model_id="gpt-4",
        display_name="GPT-4",
        description="OpenAI GPT-4 模型",
        max_tokens=8192,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="openai",
        model_id="gpt-3.5-turbo",
        display_name="GPT-3.5 Turbo",
        description="OpenAI GPT-3.5 Turbo 快速模型",
        max_tokens=16385,
        supports_function_calling=True,
    ),

    # =========================================================================
    # DashScope (阿里云通义千问)
    # =========================================================================
    ProviderModelSpec(
        provider="dashscope",
        model_id="qwen-max",
        display_name="Qwen Max",
        description="通义千问 Max 高级模型",
        max_tokens=32000,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="dashscope",
        model_id="qwen-plus",
        display_name="Qwen Plus",
        description="通义千问 Plus 平衡模型",
        max_tokens=128000,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="dashscope",
        model_id="qwen-turbo",
        display_name="Qwen Turbo",
        description="通义千问 Turbo 快速模型",
        max_tokens=128000,
        supports_function_calling=True,
    ),

    # =========================================================================
    # Moonshot (Kimi)
    # =========================================================================
    ProviderModelSpec(
        provider="moonshot",
        model_id="moonshot-v1-8k",
        display_name="Kimi V1 8K",
        description="Kimi V1 8K 上下文模型",
        max_tokens=8192,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="moonshot",
        model_id="moonshot-v1-32k",
        display_name="Kimi V1 32K",
        description="Kimi V1 32K 长上下文模型",
        max_tokens=32768,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="moonshot",
        model_id="moonshot-v1-128k",
        display_name="Kimi V1 128K",
        description="Kimi V1 128K 超长上下文模型",
        max_tokens=131072,
        supports_function_calling=True,
    ),

    # =========================================================================
    # Gemini
    # =========================================================================
    ProviderModelSpec(
        provider="gemini",
        model_id="gemini-2.5-pro",
        display_name="Gemini 2.5 Pro",
        description="Google Gemini 2.5 Pro 高级模型",
        max_tokens=1048576,
        supports_vision=True,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="gemini",
        model_id="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
        description="Google Gemini 2.5 Flash 快速模型",
        max_tokens=1048576,
        supports_vision=True,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="gemini",
        model_id="gemini-1.5-pro",
        display_name="Gemini 1.5 Pro",
        description="Google Gemini 1.5 Pro 模型",
        max_tokens=2097152,
        supports_vision=True,
        supports_function_calling=True,
    ),

    # =========================================================================
    # Groq
    # =========================================================================
    ProviderModelSpec(
        provider="groq",
        model_id="llama-3.3-70b-versatile",
        display_name="Llama 3.3 70B",
        description="Meta Llama 3.3 70B 模型，Groq 加速",
        max_tokens=131072,
        supports_function_calling=True,
    ),
    ProviderModelSpec(
        provider="groq",
        model_id="llama-3.1-8b-instant",
        display_name="Llama 3.1 8B",
        description="Meta Llama 3.1 8B 模型，Groq 加速",
        max_tokens=131072,
        supports_function_calling=True,
    ),

    # =========================================================================
    # MiniMax
    # =========================================================================
    ProviderModelSpec(
        provider="minimax",
        model_id="abab6.5s-chat",
        display_name="MiniMax 6.5S",
        description="MiniMax 6.5S 对话模型",
        max_tokens=245760,
        supports_function_calling=True,
    ),
)


def get_models_by_provider(provider: str) -> list[ProviderModelSpec]:
    """Get all models for a specific provider.

    Args:
        provider: Provider name (e.g., "deepseek", "openai")

    Returns:
        List of ProviderModelSpec for the provider
    """
    builtin = [m for m in PROVIDER_MODELS if m.provider == provider]
    custom = [m for m in _load_custom_models() if m.provider == provider]
    
    custom_ids = {m.model_id for m in custom}
    result = [m for m in builtin if m.model_id not in custom_ids]
    result.extend(custom)
    
    return result


def get_model_by_id(provider: str, model_id: str) -> ProviderModelSpec | None:
    """Get a specific model by provider and model ID.

    Args:
        provider: Provider name
        model_id: Model identifier

    Returns:
        ProviderModelSpec if found, None otherwise
    """
    for m in _load_custom_models():
        if m.provider == provider and m.model_id == model_id:
            return m
    
    for m in PROVIDER_MODELS:
        if m.provider == provider and m.model_id == model_id:
            return m
    return None


def get_all_providers_with_models() -> list[str]:
    """Get list of all providers that have model definitions.

    Returns:
        List of provider names
    """
    providers = set(m.provider for m in PROVIDER_MODELS)
    providers.update(m.provider for m in _load_custom_models())
    return list(providers)


def _load_custom_models() -> list[ProviderModelSpec]:
    """Load custom models from custom_models module.

    Returns:
        List of custom ProviderModelSpec
    """
    from nanobot.config.custom_models import load_custom_models
    
    all_models = load_custom_models()
    result = []
    
    for provider, models in all_models.items():
        for model_id, item in models.items():
            result.append(ProviderModelSpec(
                provider=provider,
                model_id=model_id,
                display_name=item.get("display_name", model_id),
                description=item.get("description", ""),
                provider_model_id=item.get("provider_model_id", ""),
                max_tokens=item.get("max_tokens", 4096),
                supports_vision=item.get("supports_vision", False),
                supports_function_calling=item.get("supports_function_calling", True),
                supports_streaming=item.get("supports_streaming", True),
                input_price=item.get("input_price", 0.0),
                output_price=item.get("output_price", 0.0),
                currency=item.get("currency", "CNY"),
                token_quota=item.get("token_quota", 0),
                token_used=item.get("token_used", 0),
                status=item.get("status", "active"),
                is_custom=True,
            ))
    
    return result


def add_custom_model(model: ProviderModelSpec) -> None:
    """Add or update a custom model.

    Args:
        model: ProviderModelSpec to add or update
    """
    from nanobot.config.custom_models import set_custom_model
    
    config = {
        "model_id": model.model_id,
        "display_name": model.display_name,
        "description": model.description,
        "provider_model_id": model.provider_model_id,
        "max_tokens": model.max_tokens,
        "supports_vision": model.supports_vision,
        "supports_function_calling": model.supports_function_calling,
        "supports_streaming": model.supports_streaming,
        "input_price": model.input_price,
        "output_price": model.output_price,
        "currency": model.currency,
        "token_quota": model.token_quota,
        "token_used": model.token_used,
        "status": model.status,
        "is_custom": True,
    }
    set_custom_model(model.provider, model.model_id, config)


def delete_custom_model(provider: str, model_id: str) -> bool:
    """Delete a custom model.

    Args:
        provider: Provider name
        model_id: Model identifier

    Returns:
        True if deleted, False if not found
    """
    from nanobot.config.custom_models import delete_custom_model as delete_model
    return delete_model(provider, model_id)


def update_model_token_usage(provider: str, model_id: str, tokens_used: int) -> None:
    """Update token usage for a model.

    Args:
        provider: Provider name
        model_id: Model identifier
        tokens_used: Tokens used in K
    """
    from nanobot.config.custom_models import update_token_usage
    update_token_usage(provider, model_id, tokens_used)
