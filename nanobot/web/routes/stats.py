"""Token statistics API routes for Web UI.

This module provides token usage statistics endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from fastapi import APIRouter, Query, Request
from typing import Any

router = APIRouter()


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

        if used_model not in by_model:
            by_model[used_model] = {
                "model": used_model,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "request_count": 0,
                "session_count": 0,
            }
        by_model[used_model]["total_prompt_tokens"] += prompt_tokens
        by_model[used_model]["total_completion_tokens"] += completion_tokens
        by_model[used_model]["total_tokens"] += tokens
        by_model[used_model]["request_count"] += requests
        if tokens > 0:
            by_model[used_model]["session_count"] += 1

    model_stats = sorted(by_model.values(), key=lambda x: x["total_tokens"], reverse=True)

    return {
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "total_requests": total_requests,
        "active_sessions": session_count,
        "period": period,
        "by_model": model_stats,
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
