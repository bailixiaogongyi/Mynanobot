"""Task models for multi-agent task management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    def is_terminal(self) -> bool:
        """Check if this is a terminal status."""
        return self in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)


class TaskPriority(Enum):
    """Priority level of a task."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    
    @classmethod
    def from_string(cls, value: str) -> "TaskPriority":
        """Create from string value."""
        mapping = {
            "low": cls.LOW,
            "medium": cls.MEDIUM,
            "high": cls.HIGH,
            "urgent": cls.URGENT,
        }
        return mapping.get(value.lower(), cls.MEDIUM)


@dataclass
class TaskContext:
    """Context information passed to a subagent.
    
    Contains all the background information needed for a subagent
    to complete its task effectively.
    """
    background: str = ""
    requirements: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    reference_files: list[str] = field(default_factory=list)
    parent_session_key: str = ""
    relevant_history: list[dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "background": self.background,
            "requirements": self.requirements,
            "constraints": self.constraints,
            "reference_files": self.reference_files,
            "parent_session_key": self.parent_session_key,
            "relevant_history": self.relevant_history,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TaskContext":
        """Create from dictionary."""
        if not data:
            return cls()
        return cls(
            background=data.get("background", ""),
            requirements=data.get("requirements", []),
            constraints=data.get("constraints", []),
            reference_files=data.get("reference_files", []),
            parent_session_key=data.get("parent_session_key", ""),
            relevant_history=data.get("relevant_history", []),
        )
    
    def to_prompt_section(self) -> str:
        """Convert to a prompt section for the subagent.
        
        Returns:
            Formatted prompt section.
        """
        parts = []
        
        if self.background:
            parts.append(f"## 任务背景\n\n{self.background}")
        
        if self.requirements:
            req_list = "\n".join(f"- {r}" for r in self.requirements)
            parts.append(f"## 用户需求\n\n{req_list}")
        
        if self.constraints:
            const_list = "\n".join(f"- {c}" for c in self.constraints)
            parts.append(f"## 约束条件\n\n{const_list}")
        
        if self.reference_files:
            files_list = "\n".join(f"- {f}" for f in self.reference_files)
            parts.append(f"## 参考文件\n\n{files_list}")
        
        return "\n\n---\n\n".join(parts) if parts else ""


@dataclass
class TaskCheckpoint:
    """A checkpoint in task execution progress."""
    stage: str
    progress: int
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    artifacts: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stage": self.stage,
            "progress": self.progress,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "artifacts": self.artifacts,
        }


@dataclass
class Task:
    """A task to be executed by a subagent.
    
    Represents a unit of work that can be assigned to a subagent
    with specific role and tracked through its lifecycle.
    """
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    role: str | None = None
    context: TaskContext | None = None
    progress: int = 0
    progress_message: str = ""
    result: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    subagent_id: str | None = None
    workspace_path: Path | None = None
    checkpoints: list[TaskCheckpoint] = field(default_factory=list)
    origin_channel: str = "cli"
    origin_chat_id: str = "direct"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "role": self.role,
            "context": self.context.to_dict() if self.context else None,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "subagent_id": self.subagent_id,
            "workspace_path": str(self.workspace_path) if self.workspace_path else None,
            "checkpoints": [cp.to_dict() for cp in self.checkpoints],
            "origin_channel": self.origin_channel,
            "origin_chat_id": self.origin_chat_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Create from dictionary."""
        context = TaskContext.from_dict(data.get("context"))
        
        checkpoints = []
        for cp_data in data.get("checkpoints", []):
            checkpoints.append(TaskCheckpoint(
                stage=cp_data.get("stage", ""),
                progress=cp_data.get("progress", 0),
                message=cp_data.get("message", ""),
                timestamp=datetime.fromisoformat(cp_data["timestamp"]) if cp_data.get("timestamp") else datetime.now(),
                artifacts=cp_data.get("artifacts", []),
            ))
        
        return cls(
            id=data["id"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", "pending")),
            priority=TaskPriority(data.get("priority", 2)),
            role=data.get("role"),
            context=context,
            progress=data.get("progress", 0),
            progress_message=data.get("progress_message", ""),
            result=data.get("result"),
            error=data.get("error"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            subagent_id=data.get("subagent_id"),
            workspace_path=Path(data["workspace_path"]) if data.get("workspace_path") else None,
            checkpoints=checkpoints,
            origin_channel=data.get("origin_channel", "cli"),
            origin_chat_id=data.get("origin_chat_id", "direct"),
        )
    
    def add_checkpoint(self, stage: str, progress: int, message: str, artifacts: list[str] | None = None) -> None:
        """Add a progress checkpoint."""
        checkpoint = TaskCheckpoint(
            stage=stage,
            progress=progress,
            message=message,
            artifacts=artifacts or [],
        )
        self.checkpoints.append(checkpoint)
        self.progress = progress
        self.progress_message = message
    
    def get_duration(self) -> float | None:
        """Get task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
