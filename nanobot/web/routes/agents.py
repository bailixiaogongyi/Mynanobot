"""Agent management API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from loguru import logger


router = APIRouter()


class TaskCreateRequest(BaseModel):
    """Request to create a new task."""
    title: str
    description: str
    role: str | None = None
    priority: str = "medium"
    context_hint: str | None = None


class TaskActionRequest(BaseModel):
    """Request for task action."""
    action: str  # pause, resume, cancel


class SpawnRequest(BaseModel):
    """Request to spawn a subagent."""
    task: str
    role: str | None = None
    title: str | None = None
    priority: str = "medium"
    context_hint: str | None = None


@router.get("/roles")
async def list_roles(request: Request) -> list[dict[str, Any]]:
    """List all available roles."""
    role_manager = request.app.state.role_manager
    return role_manager.list_roles()


@router.get("/subagents")
async def list_subagents(request: Request) -> list[dict[str, Any]]:
    """List all active subagents."""
    subagent_manager = request.app.state.subagent_manager
    return subagent_manager.list_active()


@router.get("/subagents/{task_id}")
async def get_subagent_status(task_id: str, request: Request) -> dict[str, Any]:
    """Get status of a specific subagent."""
    subagent_manager = request.app.state.subagent_manager
    status = subagent_manager.get_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Subagent {task_id} not found")
    return status


@router.post("/subagents/{task_id}/action")
async def subagent_action(
    task_id: str,
    req: TaskActionRequest,
    request: Request,
) -> dict[str, Any]:
    """Perform action on a subagent (pause/resume/cancel)."""
    subagent_manager = request.app.state.subagent_manager
    
    if req.action == "pause":
        success = await subagent_manager.pause(task_id)
        message = "Subagent paused" if success else "Failed to pause subagent"
    elif req.action == "resume":
        success = await subagent_manager.resume(task_id)
        message = "Subagent resumed" if success else "Failed to resume subagent"
    elif req.action == "cancel":
        success = await subagent_manager.cancel(task_id)
        message = "Subagent cancelled" if success else "Failed to cancel subagent"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"success": True, "message": message, "task_id": task_id}


@router.get("/subagents/{task_id}/logs")
async def get_subagent_logs(
    task_id: str,
    request: Request,
    since_index: int = 0,
) -> dict[str, Any]:
    """Get logs for a subagent."""
    subagent_manager = request.app.state.subagent_manager
    
    if not subagent_manager:
        raise HTTPException(status_code=500, detail="Subagent manager not available")
    
    logs = subagent_manager.get_logs(task_id, since_index)
    status = subagent_manager.get_status(task_id)
    
    return {
        "task_id": task_id,
        "logs": logs,
        "log_count": len(logs),
        "status": status["status"] if status else None,
    }


@router.get("/tasks")
async def list_tasks(
    request: Request,
    status: str | None = None,
    role: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List tasks with optional filters."""
    from nanobot.agent.tasks.models import TaskStatus
    
    task_manager = request.app.state.task_manager
    
    status_enum = None
    if status:
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            pass
    
    tasks = task_manager.list_tasks(status=status_enum, role=role, limit=limit)
    return [t.to_dict() for t in tasks]


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request) -> dict[str, Any]:
    """Get task details."""
    task_manager = request.app.state.task_manager
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task.to_dict()


@router.get("/tasks/statistics")
async def get_task_statistics(request: Request) -> dict[str, Any]:
    """Get task statistics."""
    task_manager = request.app.state.task_manager
    return task_manager.get_statistics()


@router.post("/spawn")
async def spawn_subagent(
    req: SpawnRequest,
    request: Request,
) -> dict[str, Any]:
    """Spawn a new subagent directly via API."""
    from nanobot.agent.tasks.models import TaskPriority, TaskContext
    from nanobot.agent.context.packer import ContextPacker
    
    subagent_manager = request.app.state.subagent_manager
    task_manager = request.app.state.task_manager
    role_manager = request.app.state.role_manager
    
    role = req.role
    if not role:
        role = role_manager.match_role_for_task(req.task)
    
    role_def = role_manager.get_role(role)
    if not role_def:
        raise HTTPException(status_code=400, detail=f"Role not found: {role}")
    
    task_title = req.title or req.task[:50]
    priority = TaskPriority.from_string(req.priority)
    
    packer = ContextPacker(
        session_history=[],
        memory_context=None,
        workspace_path=str(subagent_manager.workspace),
    )
    
    additional_context = {}
    if req.context_hint:
        additional_context["background"] = req.context_hint
    
    context_package = packer.pack_for_task(
        task_description=req.task,
        role_name=role,
        role_description=role_def.description,
        additional_context=additional_context,
    )
    
    task_context = TaskContext(
        background=context_package.task_background,
        requirements=context_package.user_requirements,
        constraints=context_package.constraints,
        reference_files=[],
        parent_session_key="api:direct",
        relevant_history=[],
    )
    
    task_obj = task_manager.create_task(
        title=task_title,
        description=req.task,
        context=task_context,
        role=role,
        priority=priority,
        origin_channel="api",
        origin_chat_id="direct",
    )
    
    result = await subagent_manager.spawn_with_role(
        task=task_obj,
        role_name=role,
        context=task_context,
        origin_channel="api",
        origin_chat_id="direct",
    )
    
    return {
        "success": True,
        "task_id": task_obj.id,
        "role": role,
        "message": result,
    }
