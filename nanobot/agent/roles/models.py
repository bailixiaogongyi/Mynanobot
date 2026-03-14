"""Role definition models for multi-agent system."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoleModelConfig:
    """Model configuration for a specific role.
    
    Allows each role to use a different model/provider for optimal
    performance and cost efficiency.
    """
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    api_key: str | None = None
    api_base: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_key": self.api_key,
            "api_base": self.api_base,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "RoleModelConfig | None":
        """Create from dictionary."""
        if not data:
            return None
        return cls(
            provider=data.get("provider"),
            model=data.get("model"),
            temperature=data.get("temperature"),
            max_tokens=data.get("max_tokens"),
            api_key=data.get("api_key"),
            api_base=data.get("api_base"),
        )


@dataclass
class CapabilitySet:
    """Defines what tools a role can and cannot use.
    
    This enforces capability boundaries to prevent subagents from
    performing actions outside their designated scope.
    """
    allowed_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    
    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed for this role.
        
        Args:
            tool_name: Name of the tool to check.
            
        Returns:
            True if the tool is allowed, False otherwise.
        """
        if tool_name in self.forbidden_tools:
            return False
        if not self.allowed_tools:
            return True
        return tool_name in self.allowed_tools
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allowed_tools": self.allowed_tools,
            "forbidden_tools": self.forbidden_tools,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CapabilitySet":
        """Create from dictionary."""
        if not data:
            return cls()
        return cls(
            allowed_tools=data.get("allowed_tools", []),
            forbidden_tools=data.get("forbidden_tools", []),
        )


@dataclass
class RoleDefinition:
    """Complete definition of a subagent role.
    
    A role defines:
    - Identity (name, description, icon)
    - Model configuration (which LLM to use)
    - Capabilities (what tools are available)
    - Behavior (system prompt, iteration limits)
    """
    name: str
    description: str
    icon: str = "🤖"
    model_config: RoleModelConfig | None = None
    capabilities: CapabilitySet = field(default_factory=CapabilitySet)
    system_prompt: str = ""
    max_iterations: int = 15
    timeout: int = 600
    enabled: bool = True
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "model_config": self.model_config.to_dict() if self.model_config else None,
            "capabilities": self.capabilities.to_dict(),
            "system_prompt": self.system_prompt,
            "max_iterations": self.max_iterations,
            "timeout": self.timeout,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, role_key: str, data: dict[str, Any]) -> "RoleDefinition":
        """Create from dictionary.
        
        Args:
            role_key: The key/identifier for this role.
            data: Dictionary containing role configuration.
            
        Returns:
            RoleDefinition instance.
        """
        model_config = RoleModelConfig.from_dict(data.get("model_config"))
        capabilities = CapabilitySet.from_dict(data.get("capabilities"))
        
        return cls(
            name=data.get("name", role_key),
            description=data.get("description", ""),
            icon=data.get("icon", "🤖"),
            model_config=model_config,
            capabilities=capabilities,
            system_prompt=data.get("system_prompt", ""),
            max_iterations=data.get("max_iterations", 15),
            timeout=data.get("timeout", 600),
            enabled=data.get("enabled", True),
        )
    
    def get_display_name(self) -> str:
        """Get display name with icon."""
        return f"{self.icon} {self.name}"
