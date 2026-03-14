"""Agent modules for multi-agent coordination."""

from nanobot.agent.roles import RoleManager, RoleDefinition, CapabilitySet, RoleModelConfig
from nanobot.agent.tasks import TaskManager, Task, TaskStatus, TaskPriority, TaskContext
from nanobot.agent.progress import ProgressTracker, ProgressStage
from nanobot.agent.providers.factory import ProviderFactory

__all__ = [
    "RoleManager",
    "RoleDefinition",
    "CapabilitySet",
    "RoleModelConfig",
    "TaskManager",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "TaskContext",
    "ProgressTracker",
    "ProgressStage",
    "ProviderFactory",
]
