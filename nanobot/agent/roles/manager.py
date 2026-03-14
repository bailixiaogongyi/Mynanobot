"""Role manager for loading and managing role definitions."""

from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from nanobot.agent.roles.models import RoleDefinition, CapabilitySet, RoleModelConfig


class RoleManager:
    """Manages role definitions for the multi-agent system.
    
    Roles are defined in YAML configuration file (config/roles.yaml).
    This is the single source of truth for all role definitions.
    """
    
    def __init__(self, config_path: Path | None = None):
        """Initialize the role manager.
        
        Args:
            config_path: Optional path to roles.yaml configuration file.
        """
        self.roles: dict[str, RoleDefinition] = {}
        
        if config_path:
            self._load_from_yaml(config_path)
    
    def _load_from_yaml(self, config_path: Path) -> None:
        """Load roles from YAML configuration file.
        
        Args:
            config_path: Path to the YAML file.
        """
        if not config_path.exists():
            logger.debug(f"Roles config file not found: {config_path}")
            return
        
        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            roles_data = data.get("roles", {})
            for role_key, role_data in roles_data.items():
                if role_data.get("enabled", True):
                    self.roles[role_key] = RoleDefinition.from_dict(role_key, role_data)
                    logger.debug(f"Loaded role from config: {role_key}")
            
            logger.info(f"Loaded {len(roles_data)} roles from {config_path}")
            
        except Exception as e:
            logger.warning(f"Failed to load roles from {config_path}: {e}")
    
    def get_role(self, role_name: str) -> RoleDefinition | None:
        """Get a role definition by name.
        
        Args:
            role_name: The role identifier.
            
        Returns:
            RoleDefinition if found, None otherwise.
        """
        return self.roles.get(role_name)
    
    def list_roles(self) -> list[dict[str, Any]]:
        """List all available roles.
        
        Returns:
            List of role information dictionaries.
        """
        return [
            {
                "key": key,
                "name": role.name,
                "description": role.description,
                "icon": role.icon,
                "enabled": role.enabled,
                "has_custom_model": role.model_config is not None and role.model_config.model is not None,
            }
            for key, role in self.roles.items()
            if role.enabled
        ]
    
    def match_role_for_task(self, task_description: str) -> str:
        """Match the most suitable role for a given task.
        
        Uses keyword matching to find the best role based on task content.
        
        Args:
            task_description: Description of the task to match.
            
        Returns:
            The key of the most suitable role.
        """
        task_lower = task_description.lower()
        
        role_keywords = {
            "document_writer": [
                "文档", "document", "报告", "report", "方案", "proposal",
                "编写", "write", "写作", "markdown", "笔记", "note",
            ],
            "code_developer": [
                "代码", "code", "编程", "programming", "开发", "develop",
                "调试", "debug", "修复", "fix", "脚本", "script",
                "python", "javascript", "java", "函数", "function",
            ],
            "data_analyst": [
                "数据", "data", "分析", "analysis", "统计", "statistics",
                "图表", "chart", "可视化", "visualization", "excel", "csv",
            ],
            "researcher": [
                "研究", "research", "调研", "调查", "检索", "search",
                "资料", "information", "查找", "find", "收集", "collect",
            ],
        }
        
        best_role = "document_writer"
        best_score = 0
        
        for role_key, keywords in role_keywords.items():
            score = sum(1 for kw in keywords if kw in task_lower)
            if score > best_score:
                best_score = score
                best_role = role_key
        
        return best_role
    
    def get_all_tools_for_role(self, role_name: str) -> list[str]:
        """Get all allowed tools for a role.
        
        Args:
            role_name: The role identifier.
            
        Returns:
            List of allowed tool names.
        """
        role = self.get_role(role_name)
        if not role:
            return []
        return role.capabilities.allowed_tools
