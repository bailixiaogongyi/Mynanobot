from fastapi import APIRouter, Request
from typing import Any

router = APIRouter()


@router.get("/dashboard/tasks")
async def get_tasks(request: Request, status: str | None = None):
    """Get task list with optional status filter."""
    task_manager = getattr(request.app.state, 'task_manager', None)

    if not task_manager:
        return {"tasks": [], "total": 0, "error": "Task manager not available"}

    tasks = []
    for task in task_manager.tasks.values():
        if status and task.status.value != status:
            continue
        tasks.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "progress": task.progress,
            "progress_message": task.progress_message,
            "role": task.role,
            "priority": task.priority.value,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": task.result,
            "error": task.error,
        })

    return {"tasks": tasks, "total": len(tasks)}


@router.get("/dashboard/tasks/{task_id}")
async def get_task_detail(task_id: str, request: Request):
    """Get detailed task information."""
    task_manager = getattr(request.app.state, 'task_manager', None)

    if not task_manager:
        return {"error": "Task manager not available"}, 404

    task = task_manager.get_task(task_id)

    if not task:
        return {"error": "Task not found"}, 404

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "progress": task.progress,
        "progress_message": task.progress_message,
        "role": task.role,
        "priority": task.priority.value,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "result": task.result,
        "error": task.error,
        "checkpoints": [cp.to_dict() for cp in task.checkpoints],
        "context": task.context.to_dict() if task.context else None,
    }


@router.get("/dashboard/tasks/{task_id}/logs")
async def get_task_logs(task_id: str, request: Request, since: int = 0, limit: int = 100):
    """Get task execution logs with pagination."""
    subagent_manager = getattr(request.app.state, 'subagent_manager', None)
    task_manager = getattr(request.app.state, 'task_manager', None)

    if not subagent_manager:
        return {"logs": [], "total": 0, "error": "Subagent manager not available"}

    logs = subagent_manager.get_logs(task_id, since_index=since)
    
    return {
        "logs": logs[:limit],
        "total": len(logs),
        "has_more": len(logs) > limit,
    }


@router.post("/dashboard/tasks/{task_id}/pause")
async def pause_task(task_id: str, request: Request):
    """Pause a running task."""
    subagent_manager = getattr(request.app.state, 'subagent_manager', None)

    if not subagent_manager:
        return {"success": False, "error": "Subagent manager not available"}

    success = await subagent_manager.pause(task_id)
    return {"success": success}


@router.post("/dashboard/tasks/{task_id}/resume")
async def resume_task(task_id: str, request: Request):
    """Resume a paused task."""
    subagent_manager = getattr(request.app.state, 'subagent_manager', None)

    if not subagent_manager:
        return {"success": False, "error": "Subagent manager not available"}

    success = await subagent_manager.resume(task_id)
    return {"success": success}


@router.post("/dashboard/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, request: Request):
    """Cancel a running task."""
    subagent_manager = getattr(request.app.state, 'subagent_manager', None)

    if not subagent_manager:
        return {"success": False, "error": "Subagent manager not available"}

    success = await subagent_manager.cancel(task_id)
    return {"success": success}


@router.delete("/dashboard/tasks/{task_id}")
async def delete_task(task_id: str, request: Request):
    """Delete a task."""
    task_manager = getattr(request.app.state, 'task_manager', None)

    if not task_manager:
        return {"success": False, "error": "Task manager not available"}

    success = task_manager.delete_task(task_id)
    return {"success": success}


@router.post("/dashboard/tasks/{task_id}/restart")
async def restart_task(task_id: str, request: Request):
    """Restart a pending/failed/cancelled task."""
    task_manager = getattr(request.app.state, 'task_manager', None)
    subagent_manager = getattr(request.app.state, 'subagent_manager', None)

    if not task_manager:
        return {"success": False, "error": "Task manager not available"}

    task = task_manager.restart_task(task_id)
    if not task:
        return {"success": False, "error": "Task not found or cannot be restarted"}
    
    if subagent_manager:
        from nanobot.agent.tasks.models import TaskContext
        try:
            await subagent_manager.spawn_with_role(
                task=task,
                role_name=task.role,
                context=task.context,
                origin_channel=task.origin_channel,
                origin_chat_id=task.origin_chat_id,
            )
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    return {"success": True, "task_id": task_id}


@router.get("/dashboard/agents")
async def get_agents(request: Request):
    """Get agent status list."""
    subagent_manager = getattr(request.app.state, 'subagent_manager', None)

    if not subagent_manager:
        return {"agents": [], "count": 0, "error": "Subagent manager not available"}

    agents = subagent_manager.list_active()
    return {"agents": agents, "count": len(agents)}


@router.get("/dashboard/stats")
async def get_stats(request: Request):
    """Get statistics dashboard data."""
    task_manager = getattr(request.app.state, 'task_manager', None)

    if not task_manager:
        return {"error": "Task manager not available"}

    tasks = list(task_manager.tasks.values())

    total = len(tasks)
    completed = sum(1 for t in tasks if t.status.value == "completed")
    failed = sum(1 for t in tasks if t.status.value == "failed")
    running = sum(1 for t in tasks if t.status.value == "running")
    pending = sum(1 for t in tasks if t.status.value == "pending")

    success_rate = round(completed / total * 100, 1) if total > 0 else 0

    completed_tasks = [t for t in tasks if t.completed_at and t.started_at]
    avg_duration = 0
    if completed_tasks:
        total_duration = sum(
            (t.completed_at - t.started_at).total_seconds()
            for t in completed_tasks
        )
        avg_duration = round(total_duration / len(completed_tasks), 1)

    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "running": running,
        "pending": pending,
        "success_rate": success_rate,
        "avg_duration_seconds": avg_duration,
    }


@router.get("/dashboard/events")
async def get_events(request: Request, limit: int = 100):
    """Get event log."""
    bus = getattr(request.app.state, 'bus', None)
    if bus and bus.shared_context:
        events = bus.shared_context.get_events(limit=limit)
    else:
        events = []

    return {"events": events}


@router.get("/dashboard/memory")
async def get_memory_stats(request: Request):
    """Get memory system statistics."""
    memory_store = getattr(request.app.state, 'memory_store', None)

    if not memory_store:
        return {"error": "Memory store not available"}

    layer_stats = memory_store.get_layer_stats()
    index_status = memory_store.get_index_status()

    return {
        "layer": layer_stats,
        "index": index_status,
    }
