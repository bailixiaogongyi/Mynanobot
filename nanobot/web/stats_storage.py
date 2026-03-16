"""Token usage statistics storage module.

This module provides independent storage for token usage statistics,
separate from session data. This ensures statistics are preserved
even when sessions are cleared.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from nanobot.utils.helpers import get_data_path


class StatsStorage:
    """Independent storage for token usage statistics."""

    def __init__(self):
        self.data_dir = get_data_path()
        self.stats_file = self.data_dir / "token_stats.json"

    def _load(self) -> dict[str, Any]:
        """Load statistics from file."""
        if not self.stats_file.exists():
            return {"by_model": {}, "by_provider": {}, "last_updated": None}
        
        try:
            with open(self.stats_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"by_model": {}, "by_provider": {}, "last_updated": None}

    def _save(self, data: dict[str, Any]) -> None:
        """Save statistics to file."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        data["last_updated"] = datetime.now().isoformat()
        
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def update_model_stats(self, model_name: str, provider: str, stats: dict[str, Any]) -> None:
        """Update statistics for a specific model.
        
        Args:
            model_name: Model identifier (e.g., "zhipu/glm-4-flash")
            provider: Provider name
            stats: Dictionary containing:
                - prompt_tokens: Input tokens
                - completion_tokens: Output tokens
                - request_count: Number of requests
                - estimated_cost: Estimated cost
                - input_price: Input price per million tokens
                - output_price: Output price per million tokens
                - currency: Currency code (CNY/USD)
                - display_name: Model display name
                - supports_vision: Whether model supports vision
                - supports_function_calling: Whether model supports function calling
                - status: Model status
                - token_quota: Token quota (bytes)
                - token_used: Token used (bytes)
        """
        data = self._load()
        
        if model_name not in data["by_model"]:
            data["by_model"][model_name] = {
                "model": model_name,
                "provider": provider,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "request_count": 0,
                "session_count": 0,
                "estimated_cost": 0.0,
                "input_price": stats.get("input_price", 0),
                "output_price": stats.get("output_price", 0),
                "max_tokens": stats.get("max_tokens", 0),
                "display_name": stats.get("display_name", model_name),
                "supports_vision": stats.get("supports_vision", False),
                "supports_function_calling": stats.get("supports_function_calling", True),
                "status": stats.get("status", "unknown"),
                "currency": stats.get("currency", "USD"),
                "token_quota": stats.get("token_quota", 0),
                "token_used": stats.get("token_used", 0),
            }
        
        model_stats = data["by_model"][model_name]
        model_stats["total_prompt_tokens"] += stats.get("prompt_tokens", 0)
        model_stats["total_completion_tokens"] += stats.get("completion_tokens", 0)
        model_stats["total_tokens"] += stats.get("prompt_tokens", 0) + stats.get("completion_tokens", 0)
        model_stats["request_count"] += stats.get("request_count", 0)
        model_stats["estimated_cost"] += stats.get("estimated_cost", 0)
        
        if stats.get("prompt_tokens", 0) + stats.get("completion_tokens", 0) > 0:
            model_stats["session_count"] += 1
        
        self._save(data)

    def update_provider_stats(self, provider: str, stats: dict[str, Any]) -> None:
        """Update statistics for a specific provider."""
        data = self._load()
        
        if provider not in data["by_provider"]:
            data["by_provider"][provider] = {
                "provider": provider,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "request_count": 0,
                "session_count": 0,
                "estimated_cost": 0.0,
                "model_count": 0,
            }
        
        provider_stats = data["by_provider"][provider]
        provider_stats["total_prompt_tokens"] += stats.get("prompt_tokens", 0)
        provider_stats["total_completion_tokens"] += stats.get("completion_tokens", 0)
        provider_stats["total_tokens"] += stats.get("prompt_tokens", 0) + stats.get("completion_tokens", 0)
        provider_stats["request_count"] += stats.get("request_count", 0)
        provider_stats["estimated_cost"] += stats.get("estimated_cost", 0)
        
        if stats.get("prompt_tokens", 0) + stats.get("completion_tokens", 0) > 0:
            provider_stats["session_count"] += 1
        
        self._save(data)

    def get_all_stats(self) -> dict[str, Any]:
        """Get all statistics."""
        return self._load()

    def get_model_stats(self, model_name: str) -> dict[str, Any] | None:
        """Get statistics for a specific model."""
        data = self._load()
        return data["by_model"].get(model_name)

    def get_provider_stats(self, provider: str) -> dict[str, Any] | None:
        """Get statistics for a specific provider."""
        data = self._load()
        return data["by_provider"].get(provider)

    def clear_all_stats(self) -> None:
        """Clear all statistics."""
        self._save({"by_model": {}, "by_provider": {}, "last_updated": None})

    def merge_session_stats(self, sessions: list[dict[str, Any]], get_model_info_func) -> None:
        """Merge statistics from sessions into persistent storage.
        
        This should be called periodically or on startup to ensure
        statistics are preserved.
        """
        for session in sessions:
            prompt_tokens = session.get("total_prompt_tokens", 0)
            completion_tokens = session.get("total_completion_tokens", 0)
            if prompt_tokens + completion_tokens == 0:
                continue
            
            used_model = session.get("used_model", "") or "unknown"
            request_count = session.get("request_count", 0)
            
            model_info = get_model_info_func(used_model)
            provider = model_info.get("provider", "unknown")
            input_price = model_info.get("input_price", 0)
            output_price = model_info.get("output_price", 0)
            estimated_cost = (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000
            
            self.update_model_stats(used_model, provider, {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "request_count": request_count,
                "estimated_cost": estimated_cost,
                **model_info,
            })


_stats_storage: StatsStorage | None = None


def get_stats_storage() -> StatsStorage:
    """Get the global stats storage instance."""
    global _stats_storage
    if _stats_storage is None:
        _stats_storage = StatsStorage()
    return _stats_storage
