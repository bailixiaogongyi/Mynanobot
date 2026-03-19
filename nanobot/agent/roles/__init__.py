"""Role definition system for multi-agent architecture."""

from nanobot.agent.roles.models import (
    RoleModelConfig,
    CapabilitySet,
    RoleDefinition,
)
from nanobot.agent.roles.manager import RoleManager

__all__ = [
    "RoleModelConfig",
    "CapabilitySet",
    "RoleDefinition",
    "RoleManager",
]
