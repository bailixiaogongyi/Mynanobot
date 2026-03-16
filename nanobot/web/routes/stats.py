"""Token statistics API routes for Web UI.

This module provides token usage statistics endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from fastapi import APIRouter, Query, Request
from typing import Any

router = APIRouter()


def _get_model_pricing(model_name: str) -> dict[str, Any]:
    """Get model information including pricing and capabilities.

    Args:
        model_name: Full model name (e.g., "deepseek/deepseek-chat")

    Returns:
        Dict with provider, input_price, output_price, max_tokens, display_name, etc.
    """
    from nanobot.providers.provider_models import get_model_by_id, _load_custom_models, PROVIDER_MODELS

    if "/" in model_name:
        provider, model_id = model_name.split("/", 1)
    else:
        provider = "unknown"
        model_id = model_name

    spec = get_model_by_id(provider, model_id)
    if spec:
        return {
            "provider": provider,
            "input_price": spec.input_price,
            "output_price": spec.output_price,
            "max_tokens": spec.max_tokens,
            "display_name": spec.display_name,
            "supports_vision": spec.supports_vision,
            "supports_function_calling": spec.supports_function_calling,
            "status": spec.status,
            "currency": spec.currency if hasattr(spec, 'currency') else "USD",
            "token_quota": spec.token_quota if hasattr(spec, 'token_quota') else 0,
            "token_used": spec.token_used if hasattr(spec, 'token_used') else 0,
        }

    custom_models = _load_custom_models()
    for provider_key, models in custom_models.items():
        for model_id_key, model_spec in models.items():
            if model_spec.get("model_id") == model_id:
                return {
                    "provider": model_spec.get("provider", provider_key),
                    "input_price": model_spec.get("input_price", 0.0),
                    "output_price": model_spec.get("output_price", 0.0),
                    "max_tokens": model_spec.get("max_tokens", 0),
                    "display_name": model_spec.get("display_name", model_id),
                    "supports_vision": model_spec.get("supports_vision", False),
                    "supports_function_calling": model_spec.get("supports_function_calling", True),
                    "status": model_spec.get("status", "unknown"),
                    "currency": model_spec.get("currency", "USD"),
                    "token_quota": model_spec.get("token_quota", 0),
                    "token_used": model_spec.get("token_used", 0),
                }

    for m in PROVIDER_MODELS:
        if m.model_id == model_id:
            return {
                "provider": m.provider,
                "input_price": m.input_price,
                "output_price": m.output_price,
                "max_tokens": m.max_tokens,
                "display_name": m.display_name,
                "supports_vision": m.supports_vision,
                "supports_function_calling": m.supports_function_calling,
                "status": m.status,
                "currency": m.currency if hasattr(m, 'currency') else "USD",
                "token_quota": m.token_quota if hasattr(m, 'token_quota') else 0,
                "token_used": m.token_used if hasattr(m, 'token_used') else 0,
            }

    return {
        "provider": provider,
        "input_price": 0.0,
        "output_price": 0.0,
        "max_tokens": 0,
        "display_name": model_id,
        "supports_vision": False,
        "supports_function_calling": True,
        "status": "unknown",
        "currency": "USD",
        "token_quota": 0,
        "token_used": 0,
    }


@router.get("/stats/tokens")
async def get_token_stats(
    request: Request,
    period: str = Query("all", description="Period: today, week, month, all"),
) -> dict[str, Any]:
    """Get token usage statistics.

    Args:
        request: FastAPI request object.
        period: Time period filter (today, week, month, all).

    Returns:
        Token usage statistics.
    """
    from nanobot.web.stats_storage import get_stats_storage
    
    stats_storage = get_stats_storage()
    stored_stats = stats_storage.get_all_stats()
    
    if stored_stats.get("by_model"):
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        total_requests = 0
        session_count = 0
        by_model = {}
        by_provider = {}
        
        for model_name, model_stats in stored_stats.get("by_model", {}).items():
            prompt_tokens = model_stats.get("total_prompt_tokens", 0)
            completion_tokens = model_stats.get("total_completion_tokens", 0)
            tokens = model_stats.get("total_tokens", 0)
            requests = model_stats.get("request_count", 0)
            provider = model_stats.get("provider", "unknown")
            
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            total_tokens += tokens
            total_requests += requests
            if tokens > 0:
                session_count += 1
            
            by_model[model_name] = {**model_stats}
            
            if provider not in by_provider:
                by_provider[provider] = {
                    "provider": provider,
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "total_tokens": 0,
                    "request_count": 0,
                    "session_count": 0,
                    "estimated_cost": 0.0,
                    "model_count": 0,
                }
            by_provider[provider]["total_prompt_tokens"] += prompt_tokens
            by_provider[provider]["total_completion_tokens"] += completion_tokens
            by_provider[provider]["total_tokens"] += tokens
            by_provider[provider]["request_count"] += requests
            by_provider[provider]["estimated_cost"] += model_stats.get("estimated_cost", 0)
            if tokens > 0:
                by_provider[provider]["session_count"] += 1
            by_provider[provider]["model_count"] = len([m for m in by_model if by_model[m].get("provider") == provider])
        
        return {
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "total_requests": total_requests,
            "active_sessions": session_count,
            "by_model": list(by_model.values()),
            "by_provider": list(by_provider.values()),
            "period": period,
        }
    
    session_manager = getattr(request.app.state, 'session_manager', None)

    if not session_manager:
        return {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "total_requests": 0,
            "period": period,
            "error": "Session manager not available",
        }

    sessions = session_manager.list_sessions()

    now = datetime.now()
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:
        start_date = None

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    total_requests = 0
    session_count = 0
    by_model: dict[str, dict[str, Any]] = {}
    by_provider: dict[str, dict[str, Any]] = {}

    for session_data in sessions:
        updated_at_str = session_data.get("updated_at")
        if updated_at_str:
            try:
                updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                if start_date and updated_at < start_date:
                    continue
            except (ValueError, TypeError):
                pass

        prompt_tokens = session_data.get("total_prompt_tokens", 0)
        completion_tokens = session_data.get("total_completion_tokens", 0)
        tokens = session_data.get("total_tokens", 0)
        requests = session_data.get("request_count", 0)
        used_model = session_data.get("used_model", "") or "unknown"

        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        total_tokens += tokens
        total_requests += requests
        if tokens > 0:
            session_count += 1

        model_info = _get_model_pricing(used_model)
        provider = model_info["provider"]
        input_price = model_info["input_price"]
        output_price = model_info["output_price"]
        estimated_cost = (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000

        if used_model not in by_model:
            by_model[used_model] = {
                "model": used_model,
                "provider": provider,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "request_count": 0,
                "session_count": 0,
                "estimated_cost": 0.0,
                "input_price": input_price,
                "output_price": output_price,
                "max_tokens": model_info["max_tokens"],
                "display_name": model_info["display_name"],
                "supports_vision": model_info["supports_vision"],
                "supports_function_calling": model_info["supports_function_calling"],
                "status": model_info["status"],
                "currency": model_info.get("currency", "USD"),
                "token_quota": model_info.get("token_quota", 0),
                "token_used": model_info.get("token_used", 0),
            }
        by_model[used_model]["total_prompt_tokens"] += prompt_tokens
        by_model[used_model]["total_completion_tokens"] += completion_tokens
        by_model[used_model]["total_tokens"] += tokens
        by_model[used_model]["request_count"] += requests
        by_model[used_model]["estimated_cost"] += estimated_cost
        if tokens > 0:
            by_model[used_model]["session_count"] += 1

        if provider not in by_provider:
            by_provider[provider] = {
                "provider": provider,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "request_count": 0,
                "session_count": 0,
                "estimated_cost": 0.0,
            }
        by_provider[provider]["total_prompt_tokens"] += prompt_tokens
        by_provider[provider]["total_completion_tokens"] += completion_tokens
        by_provider[provider]["total_tokens"] += tokens
        by_provider[provider]["request_count"] += requests
        by_provider[provider]["estimated_cost"] += estimated_cost
        if tokens > 0:
            by_provider[provider]["session_count"] += 1

    model_stats = sorted(by_model.values(), key=lambda x: x["total_tokens"], reverse=True)
    provider_stats = sorted(by_provider.values(), key=lambda x: x["total_tokens"], reverse=True)

    total_estimated_cost = sum(m.get("estimated_cost", 0) for m in model_stats)

    return {
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "total_requests": total_requests,
        "active_sessions": session_count,
        "period": period,
        "estimated_cost": total_estimated_cost,
        "by_model": model_stats,
        "by_provider": provider_stats,
    }


@router.get("/stats/tokens/sessions")
async def get_session_token_stats(
    request: Request,
    limit: int = Query(20, description="Number of sessions to return"),
) -> dict[str, Any]:
    """Get token usage for each session.

    Args:
        request: FastAPI request object.
        limit: Maximum number of sessions to return.

    Returns:
        List of sessions with token usage.
    """
    session_manager = getattr(request.app.state, 'session_manager', None)

    if not session_manager:
        return {
            "sessions": [],
            "error": "Session manager not available",
        }

    sessions = session_manager.list_sessions()

    session_list = []
    for session_data in sessions:
        if session_data.get("total_tokens", 0) > 0:
            session_list.append({
                "key": session_data.get("key", ""),
                "updated_at": session_data.get("updated_at"),
                "total_prompt_tokens": session_data.get("total_prompt_tokens", 0),
                "total_completion_tokens": session_data.get("total_completion_tokens", 0),
                "total_tokens": session_data.get("total_tokens", 0),
                "request_count": session_data.get("request_count", 0),
            })

    session_list.sort(key=lambda x: x.get("total_tokens", 0), reverse=True)
    return {
        "sessions": session_list[:limit],
        "total": len(session_list),
    }
