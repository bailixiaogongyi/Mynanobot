"""Task manager for coordinating multi-agent tasks."""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.agent.tasks.models import Task, TaskStatus, TaskPriority, TaskContext
from nanobot.bus.queue import MessageBus
from nanobot.utils.helpers import ensure_dir


class TaskManager:
    """Manages task lifecycle for multi-agent coordination.
    
    Responsibilities:
    - Create and track tasks
    - Persist task state
    - Provide task queries
    - Coordinate task assignment
    """
    
    def __init__(self, workspace: Path, bus: MessageBus | None = None):
        """Initialize the task manager.
        
        Args:
            workspace: The workspace directory for task storage.
            bus: Optional message bus for notifications.
        """
        self.workspace = workspace
        self.bus = bus
        self.tasks_dir = ensure_dir(workspace / "tasks")
        self.tasks: dict[str, Task] = {}
        self._load_tasks()
    
    def _load_tasks(self) -> None:
        """Load existing tasks from disk."""
        if not self.tasks_dir.exists():
            return
        
        for path in self.tasks_dir.glob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                task = Task.from_dict(data)
                
                if task.status == TaskStatus.RUNNING:
                    logger.warning(
                        f"Task [{task.id}] was RUNNING at shutdown, resetting to PENDING. "
                        f"Previous subagent_id: {task.subagent_id}"
                    )
                    task.status = TaskStatus.PENDING
                    task.subagent_id = None
                    self._save_task(task)
                
                self.tasks[task.id] = task
            except Exception as e:
                logger.warning(f"Failed to load task from {path}: {e}")
        
        logger.debug(f"Loaded {len(self.tasks)} tasks (including historical)")
    
    def _save_task(self, task: Task) -> None:
        """Save a task to disk.
        
        Args:
            task: The task to save.
        """
        path = self.tasks_dir / f"{task.id}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save task {task.id}: {e}")
    
    def _delete_task_file(self, task_id: str) -> None:
        """Delete task file from disk.
        
        Args:
            task_id: The task ID.
        """
        path = self.tasks_dir / f"{task_id}.json"
        if path.exists():
            try:
                path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete task file {path}: {e}")
    
    def create_task(
        self,
        title: str,
        description: str,
        context: TaskContext | None = None,
        role: str | None = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        origin_channel: str = "cli",
        origin_chat_id: str = "direct",
    ) -> Task:
        """Create a new task.
        
        Args:
            title: Task title.
            description: Task description.
            context: Optional task context.
            role: Optional role assignment.
            priority: Task priority.
            origin_channel: Origin channel for responses.
            origin_chat_id: Origin chat ID for responses.
            
        Returns:
            The created task.
        """
        task_id = str(uuid.uuid4())[:8]
        
        task = Task(
            id=task_id,
            title=title,
            description=description,
            context=context,
            role=role,
            priority=priority,
            origin_channel=origin_channel,
            origin_chat_id=origin_chat_id,
        )
        
        self.tasks[task_id] = task
        self._save_task(task)
        
        logger.info(f"Created task [{task_id}]: {title}")
        return task
    
    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID.
        
        Args:
            task_id: The task ID.
            
        Returns:
            The task if found, None otherwise.
        """
        return self.tasks.get(task_id)
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID.
        
        Args:
            task_id: The task ID.
            
        Returns:
            True if deleted, False if not found.
        """
        task = self.tasks.pop(task_id, None)
        if task:
            task_file = self.tasks_dir / f"{task_id}.json"
            if task_file.exists():
                task_file.unlink()
            logger.info(f"Deleted task [{task_id}]: {task.title}")
            return True
        return False
    
    def restart_task(self, task_id: str) -> Task | None:
        """Restart a pending/failed/cancelled task by resetting its status.
        
        Args:
            task_id: The task ID.
            
        Returns:
            The restarted task if found, None otherwise.
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        if task.status not in (TaskStatus.PENDING, TaskStatus.FAILED, TaskStatus.CANCELLED):
            logger.warning(f"Cannot restart task [{task_id}]: invalid status {task.status}")
            return None
        
        task.status = TaskStatus.PENDING
        task.progress = 0
        task.progress_message = ""
        task.error = None
        task.started_at = None
        task.completed_at = None
        task.result = None
        
        self._save_task(task)
        logger.info(f"Restarted task [{task_id}]: {task.title}")
        return task
    
    def update_task(
        self,
        task_id: str,
        status: TaskStatus | None = None,
        progress: int | None = None,
        progress_message: str | None = None,
        result: str | None = None,
        error: str | None = None,
    ) -> Task | None:
        """Update a task.
        
        Args:
            task_id: The task ID.
            status: Optional new status.
            progress: Optional progress value.
            progress_message: Optional progress message.
            result: Optional result.
            error: Optional error message.
            
        Returns:
            The updated task if found, None otherwise.
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        if status is not None:
            task.status = status
            if status == TaskStatus.RUNNING and task.started_at is None:
                task.started_at = datetime.now()
            elif status.is_terminal():
                task.completed_at = datetime.now()
        
        if progress is not None:
            task.progress = progress
        
        if progress_message is not None:
            task.progress_message = progress_message
        
        if result is not None:
            task.result = result
        
        if error is not None:
            task.error = error
        
        self._save_task(task)
        return task
    
    def add_checkpoint(
        self,
        task_id: str,
        stage: str,
        progress: int,
        message: str,
        artifacts: list[str] | None = None,
    ) -> Task | None:
        """Add a checkpoint to a task.
        
        Args:
            task_id: The task ID.
            stage: The execution stage.
            progress: Progress percentage.
            message: Progress message.
            artifacts: Optional list of artifacts.
            
        Returns:
            The updated task if found, None otherwise.
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        task.add_checkpoint(stage, progress, message, artifacts)
        self._save_task(task)
        return task
    
    def assign_task(self, task_id: str, role: str, subagent_id: str) -> Task | None:
        """Assign a task to a subagent.
        
        Args:
            task_id: The task ID.
            role: The role to assign.
            subagent_id: The subagent ID.
            
        Returns:
            The updated task if found, None otherwise.
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        task.role = role
        task.subagent_id = subagent_id
        task.status = TaskStatus.ASSIGNED
        self._save_task(task)
        
        logger.info(f"Assigned task [{task_id}] to role '{role}' (subagent: {subagent_id})")
        return task
    
    def complete_task(self, task_id: str, result: str) -> Task | None:
        """Mark a task as completed.
        
        Args:
            task_id: The task ID.
            result: The task result.
            
        Returns:
            The updated task if found, None otherwise.
        """
        return self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            progress_message="任务完成",
            result=result,
        )
    
    def fail_task(self, task_id: str, error: str) -> Task | None:
        """Mark a task as failed.
        
        Args:
            task_id: The task ID.
            error: The error message.
            
        Returns:
            The updated task if found, None otherwise.
        """
        return self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            error=error,
        )
    
    def cancel_task(self, task_id: str) -> Task | None:
        """Cancel a task.
        
        Args:
            task_id: The task ID.
            
        Returns:
            The updated task if found, None otherwise.
        """
        return self.update_task(
            task_id,
            status=TaskStatus.CANCELLED,
            progress_message="任务已取消",
        )
    
    def pause_task(self, task_id: str) -> Task | None:
        """Pause a task.
        
        Args:
            task_id: The task ID.
            
        Returns:
            The updated task if found, None otherwise.
        """
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return None
        
        return self.update_task(
            task_id,
            status=TaskStatus.PAUSED,
            progress_message="任务已暂停",
        )
    
    def resume_task(self, task_id: str) -> Task | None:
        """Resume a paused task.
        
        Args:
            task_id: The task ID.
            
        Returns:
            The updated task if found, None otherwise.
        """
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            return None
        
        return self.update_task(
            task_id,
            status=TaskStatus.RUNNING,
            progress_message="任务已恢复",
        )
    
    def list_tasks(
        self,
        status: TaskStatus | None = None,
        role: str | None = None,
        limit: int = 50,
    ) -> list[Task]:
        """List tasks with optional filters.
        
        Args:
            status: Optional status filter.
            role: Optional role filter.
            limit: Maximum number of tasks to return.
            
        Returns:
            List of matching tasks.
        """
        tasks = list(self.tasks.values())
        
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        
        if role is not None:
            tasks = [t for t in tasks if t.role == role]
        
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]
    
    def get_active_tasks(self) -> list[Task]:
        """Get all active (non-terminal) tasks.
        
        Returns:
            List of active tasks.
        """
        return [t for t in self.tasks.values() if not t.status.is_terminal()]
    
    def get_tasks_by_origin(self, channel: str, chat_id: str) -> list[Task]:
        """Get tasks by origin channel and chat ID.
        
        Args:
            channel: The origin channel.
            chat_id: The origin chat ID.
            
        Returns:
            List of matching tasks.
        """
        return [
            t for t in self.tasks.values()
            if t.origin_channel == channel and t.origin_chat_id == chat_id
        ]
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed tasks.
        
        Args:
            max_age_hours: Maximum age in hours for completed tasks.
            
        Returns:
            Number of tasks cleaned up.
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        cleaned = 0
        
        for task_id, task in list(self.tasks.items()):
            if task.status.is_terminal() and task.completed_at:
                if task.completed_at < cutoff:
                    del self.tasks[task_id]
                    self._delete_task_file(task_id)
                    cleaned += 1
        
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} completed tasks")
        
        return cleaned
    
    def get_statistics(self) -> dict[str, Any]:
        """Get task statistics.
        
        Returns:
            Dictionary with task statistics.
        """
        tasks = list(self.tasks.values())
        
        return {
            "total": len(tasks),
            "pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
            "running": sum(1 for t in tasks if t.status == TaskStatus.RUNNING),
            "paused": sum(1 for t in tasks if t.status == TaskStatus.PAUSED),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            "cancelled": sum(1 for t in tasks if t.status == TaskStatus.CANCELLED),
        }
