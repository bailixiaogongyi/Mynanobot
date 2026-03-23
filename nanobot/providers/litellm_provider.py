"""LiteLLM provider implementation for multi-provider support."""

import json
import json_repair
import os
from typing import Any, AsyncGenerator

import litellm
from loguru import logger
from litellm import acompletion

from nanobot.providers.base import LLMProvider, LLMResponse, StreamChunk, ToolCallRequest
from nanobot.providers.registry import find_by_model, find_gateway


# Standard OpenAI chat-completion message keys; extras (e.g. reasoning_content) are stripped for strict providers.
_ALLOWED_MSG_KEYS = frozenset({"role", "content", "tool_calls", "tool_call_id", "name"})
_ALLOWED_CONTENT_TYPES = frozenset({"text", "image_url", "image_url_detail"})


class LiteLLMProvider(LLMProvider):
    """
    LLM provider using LiteLLM for multi-provider support.
    
    Supports OpenRouter, Anthropic, OpenAI, Gemini, MiniMax, and many other providers through
    a unified interface.  Provider-specific logic is driven by the registry
    (see providers/registry.py) — no if-elif chains needed here.
    """
    
    def __init__(
        self, 
        api_key: str | None = None, 
        api_base: str | None = None,
        default_model: str = "anthropic/claude-opus-4-5",
        extra_headers: dict[str, str] | None = None,
        provider_name: str | None = None,
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self.extra_headers = extra_headers or {}
        
        # Detect gateway / local deployment.
        # provider_name (from config key) is the primary signal;
        # api_key / api_base are fallback for auto-detection.
        self._gateway = find_gateway(provider_name, api_key, api_base)
        self._gateway_provider: str | None = None  # LiteLLM provider name for gateway mode

        if self._gateway:
            logger.info(f"[LiteLLMProvider] Gateway mode: provider_name={provider_name}, litellm_prefix={self._gateway.litellm_prefix}")
        else:
            logger.warning(f"[LiteLLMProvider] No gateway detected: provider_name={provider_name}, api_key={'set' if api_key else None}, api_base={api_base}")
        
        # Configure environment variables
        if api_key:
            self._setup_env(api_key, api_base, default_model)
        
        if api_base:
            litellm.api_base = api_base
        
        # Disable LiteLLM logging noise
        litellm.suppress_debug_info = True
        # Drop unsupported parameters for providers (e.g., gpt-5 rejects some params)
        litellm.drop_params = True
        
        # Disable streaming usage calculation to avoid "Error building chunks" error
        # This error occurs when some providers don't return proper usage data in streams
        litellm.set_verbose = False
        
        # Configure LiteLLM timeout for long-running streaming requests
        # This prevents connection drops during long input processing
        litellm.request_timeout = 600  # 10 minutes total timeout
    
    def _setup_env(self, api_key: str, api_base: str | None, model: str) -> None:
        """Set environment variables based on detected provider."""
        spec = self._gateway or find_by_model(model)
        if not spec:
            return
        if not spec.env_key:
            return

        if self._gateway:
            os.environ[spec.env_key] = api_key
        else:
            os.environ.setdefault(spec.env_key, api_key)

        effective_base = api_base or spec.default_api_base
        for env_name, env_val in spec.env_extras:
            resolved = env_val.replace("{api_key}", api_key)
            resolved = resolved.replace("{api_base}", effective_base)
            os.environ.setdefault(env_name, resolved)

    def _get_api_key(self, model: str) -> str | None:
        """Get API key from instance (loaded at startup)."""
        return self.api_key

    def _get_api_base(self, model: str) -> str | None:
        """Get API base from instance (loaded at startup)."""
        return self.api_base
    
    def _resolve_model(self, model: str) -> str:
        """Resolve model name.

        For gateway mode, returns the model and sets _gateway_provider for routing.
        For standard mode, adds litellm_prefix if needed (e.g., zai/glm-4-flash).
        """
        if self._gateway:
            self._gateway_provider = self._gateway.litellm_prefix
            return model

        self._gateway_provider = None
        spec = find_by_model(model)
        if spec and spec.litellm_prefix:
            if not model.startswith(f"{spec.litellm_prefix}/"):
                model = f"{spec.litellm_prefix}/{model}"
        return model

    def _supports_cache_control(self, model: str) -> bool:
        """Return True when the provider supports cache_control on content blocks."""
        if self._gateway is not None:
            return self._gateway.supports_prompt_caching
        spec = find_by_model(model)
        return spec is not None and spec.supports_prompt_caching

    def _apply_cache_control(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]] | None]:
        """Return copies of messages and tools with cache_control injected."""
        new_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                content = msg["content"]
                if isinstance(content, str):
                    new_content = [{"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}]
                else:
                    new_content = list(content)
                    new_content[-1] = {**new_content[-1], "cache_control": {"type": "ephemeral"}}
                new_messages.append({**msg, "content": new_content})
            else:
                new_messages.append(msg)

        new_tools = tools
        if tools:
            new_tools = list(tools)
            new_tools[-1] = {**new_tools[-1], "cache_control": {"type": "ephemeral"}}

        return new_messages, new_tools

    def _apply_model_overrides(self, model: str, kwargs: dict[str, Any]) -> None:
        """Apply model-specific parameter overrides from the registry."""
        model_lower = model.lower()
        spec = find_by_model(model)
        if spec:
            for pattern, overrides in spec.model_overrides:
                if pattern in model_lower:
                    kwargs.update(overrides)
                    return
    
    @staticmethod
    def _sanitize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Strip non-standard keys, clean XML tool calls from content, and ensure proper format."""
        import re
        sanitized = []
        for msg in messages:
            clean = {k: v for k, v in msg.items() if k in _ALLOWED_MSG_KEYS}
            
            if clean.get("role") == "user" and "content" in msg:
                content = msg["content"]
                if isinstance(content, list):
                    valid_content = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") in _ALLOWED_CONTENT_TYPES:
                            valid_content.append(item)
                    if valid_content:
                        clean["content"] = valid_content
                    else:
                        text_content = next((item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"), "")
                        clean["content"] = text_content or ""
                elif isinstance(content, str):
                    pass
                else:
                    clean["content"] = str(content) if content else ""
            
            if clean.get("role") == "assistant":
                if "content" not in clean:
                    clean["content"] = None
                elif clean.get("tool_calls"):
                    content = clean.get("content", "") or ""
                    xml_pattern = r'<invoke\s+name="[^"]*"[^>]*>.*?</invoke>'
                    content = re.sub(xml_pattern, "", content, flags=re.DOTALL)
                    content = re.sub(r'\n\s*\n', '\n', content).strip()
                    clean["content"] = content if content else None
            
            sanitized.append(clean)
        return sanitized

    @staticmethod
    def _sanitize_empty_content(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ensure all messages have valid content (None -> empty string for compatibility)."""
        result = []
        for msg in messages:
            msg_copy = dict(msg)
            if msg_copy.get("content") is None:
                msg_copy["content"] = ""
            result.append(msg_copy)
        return result

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send a chat completion request via LiteLLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions in OpenAI format.
            model: Model identifier (e.g., 'anthropic/claude-sonnet-4-5').
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.
        
        Returns:
            LLMResponse with content and/or tool calls.
        """
        model = model or self.default_model
        model = self._resolve_model(model)

        if self._supports_cache_control(model):
            messages, tools = self._apply_cache_control(messages, tools)

        # Clamp max_tokens to at least 1 — negative or zero values cause
        # LiteLLM to reject the request with "max_tokens must be at least 1".
        max_tokens = max(1, max_tokens)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": self._sanitize_messages(self._sanitize_empty_content(messages)),
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Pass custom_llm_provider for gateway mode instead of prefixing model name
        if self._gateway_provider:
            kwargs["custom_llm_provider"] = self._gateway_provider

        # Apply model-specific overrides (e.g. kimi-k2.5 temperature)
        self._apply_model_overrides(model, kwargs)
        
        # Get API key dynamically from config
        api_key = self._get_api_key(model)
        if api_key:
            kwargs["api_key"] = api_key
        
        # Pass api_base for custom endpoints
        api_base = self._get_api_base(model)
        if api_base:
            kwargs["api_base"] = api_base
        
        # Pass extra headers (e.g. APP-Code for AiHubMix)
        if self.extra_headers:
            kwargs["extra_headers"] = self.extra_headers
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        try:
            response = await acompletion(**kwargs)
            return self._parse_response(response)
        except Exception as e:
            return LLMResponse(
                content=f"Error calling LLM: {str(e)}",
                finish_reason="error",
            )
    
    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream chat completion response via LiteLLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions in OpenAI format.
            model: Model identifier (e.g., 'anthropic/claude-sonnet-4-5').
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.
        
        Yields:
            StreamChunk objects representing incremental response.
        """
        model = model or self.default_model
        model = self._resolve_model(model)

        if self._supports_cache_control(model):
            messages, tools = self._apply_cache_control(messages, tools)

        max_tokens = max(1, max_tokens)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": self._sanitize_messages(self._sanitize_empty_content(messages)),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        # Pass custom_llm_provider for gateway mode instead of prefixing model name
        if self._gateway_provider:
            kwargs["custom_llm_provider"] = self._gateway_provider

        user_msg_after = next((m for m in kwargs['messages'] if m.get("role") == "user"), None)
        if user_msg_after:
            logger.info(f"[LiteLLM] User message after sanitize: {str(user_msg_after.get('content', ''))[:500]}...")
        
        
        self._apply_model_overrides(model, kwargs)
        
        api_key = self._get_api_key(model)
        if api_key:
            kwargs["api_key"] = api_key
        
        api_base = self._get_api_base(model)
        if api_base:
            kwargs["api_base"] = api_base
        
        if self.extra_headers:
            kwargs["extra_headers"] = self.extra_headers
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        tool_call_buffers: dict[int, dict[str, Any]] = {}
        usage: dict[str, int] = {}
        actual_model = model
        finish_reason = None
        
        try:
            logger.info(f"[LiteLLM] Starting stream with model={model}")
            response = await acompletion(**kwargs)
            chunk_count = 0
            async for chunk in response:
                if not chunk.choices:
                    if hasattr(chunk, "usage") and chunk.usage:
                        usage = {
                            "prompt_tokens": getattr(chunk.usage, "prompt_tokens", 0) or 0,
                            "completion_tokens": getattr(chunk.usage, "completion_tokens", 0) or 0,
                            "total_tokens": getattr(chunk.usage, "total_tokens", 0) or 0,
                        }
                        logger.debug(f"[LiteLLM] Usage received (no choices): {usage}")
                    continue
                
                chunk_count += 1
                delta = chunk.choices[0].delta
                chunk_finish_reason = chunk.choices[0].finish_reason
                
                if chunk_count <= 3:
                    logger.info(f"[LiteLLM] Chunk #{chunk_count}: has_content={hasattr(delta, 'content') and bool(delta.content)}, finish_reason={chunk_finish_reason}")
                
                if hasattr(delta, "content") and delta.content:
                    yield StreamChunk(type="text_delta", content=delta.content)
                
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    yield StreamChunk(type="reasoning_delta", content=delta.reasoning_content)
                
                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = getattr(tc, "index", id(tc))
                        if idx not in tool_call_buffers:
                            tool_call_buffers[idx] = {
                                "id": getattr(tc, "id", None) or "",
                                "name": "",
                                "arguments": "",
                            }
                        if hasattr(tc, "function") and tc.function:
                            if tc.function.name:
                                tool_call_buffers[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_call_buffers[idx]["arguments"] += tc.function.arguments
                            if not tool_call_buffers[idx]["id"] and hasattr(tc, "id"):
                                tool_call_buffers[idx]["id"] = tc.id or ""
                
                if hasattr(chunk, "usage") and chunk.usage:
                    usage = {
                        "prompt_tokens": getattr(chunk.usage, "prompt_tokens", 0) or 0,
                        "completion_tokens": getattr(chunk.usage, "completion_tokens", 0) or 0,
                        "total_tokens": getattr(chunk.usage, "total_tokens", 0) or 0,
                    }
                    logger.debug(f"[LiteLLM] Usage received: {usage}")
                
                if hasattr(chunk, "model") and chunk.model:
                    actual_model = chunk.model
                
                if chunk_finish_reason:
                    finish_reason = chunk_finish_reason
            
            logger.info(f"[LiteLLM] Stream finished with reason={finish_reason}, total_chunks={chunk_count}, usage={usage}")
            
            if tool_call_buffers:
                for buf in tool_call_buffers.values():
                    args = {}
                    if buf["arguments"]:
                        try:
                            args = json_repair.loads(buf["arguments"])
                        except Exception:
                            args = {"raw": buf["arguments"]}
                    yield StreamChunk(
                        type="tool_call",
                        tool_call=ToolCallRequest(
                            id=buf["id"] or f"call_{id(buf)}",
                            name=buf["name"],
                            arguments=args,
                        )
                    )
            
            yield StreamChunk(
                type="done", 
                finish_reason=finish_reason or "stop", 
                usage=usage,
                metadata={"model": actual_model} if actual_model else {},
            )
                    
        except Exception as e:
            logger.exception(f"[LiteLLM] Error in chat_stream: {str(e)}")
            yield StreamChunk(type="error", content=str(e))
    
    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse LiteLLM response into our standard format."""
        choice = response.choices[0]
        message = choice.message
        
        tool_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                # Parse arguments from JSON string if needed
                args = tc.function.arguments
                if isinstance(args, str):
                    args = json_repair.loads(args)
                
                tool_calls.append(ToolCallRequest(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))
        
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        
        reasoning_content = getattr(message, "reasoning_content", None) or None
        
        actual_model = getattr(response, "model", None) or self.default_model
        
        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
            reasoning_content=reasoning_content,
            model=actual_model,
        )
    
    def get_default_model(self) -> str:
        """Get the default model."""
        return self.default_model
