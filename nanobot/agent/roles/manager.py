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
    Supports dynamic reload without service restart.
    """
    
    def __init__(self, config_path: Path | None = None):
        """Initialize the role manager.
        
        Args:
            config_path: Optional path to roles.yaml configuration file.
        """
        self.roles: dict[str, RoleDefinition] = {}
        self._config_path = config_path
        
        if config_path:
            self._load_from_yaml(config_path)
    
    def reload(self) -> dict[str, Any]:
        """Reload roles from YAML configuration file.
        
        Returns:
            Dictionary with reload status and message.
        """
        if not self._config_path or not self._config_path.exists():
            return {"success": False, "message": "Config file not found"}
        
        try:
            old_roles = set(self.roles.keys())
            self._load_from_yaml(self._config_path)
            new_roles = set(self.roles.keys())
            
            added = new_roles - old_roles
            removed = old_roles - new_roles
            updated = old_roles & new_roles
            
            return {
                "success": True,
                "message": f"Reloaded successfully",
                "roles_count": len(self.roles),
                "added": list(added) if added else [],
                "removed": list(removed) if removed else [],
                "updated": list(updated) if updated else [],
            }
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def update_role(self, role_key: str, role_data: dict[str, Any], persist: bool = True) -> dict[str, Any]:
        """Update a role dynamically (runtime modification).
        
        Args:
            role_key: The role identifier to update.
            role_data: Dictionary containing role configuration.
            persist: Whether to persist changes to YAML file.
            
        Returns:
            Dictionary with update status.
        """
        try:
            if role_key in self.roles:
                role = RoleDefinition.from_dict(role_key, role_data)
                self.roles[role_key] = role
                
                if persist:
                    persist_result = self._save_to_yaml()
                    if not persist_result["success"]:
                        return {"success": False, "message": f"Role updated but failed to persist: {persist_result['message']}"}
                
                return {"success": True, "message": f"Role '{role_key}' updated"}
            else:
                if role_data.get("enabled", True):
                    role = RoleDefinition.from_dict(role_key, role_data)
                    self.roles[role_key] = role
                    
                    if persist:
                        persist_result = self._save_to_yaml()
                        if not persist_result["success"]:
                            return {"success": False, "message": f"Role created but failed to persist: {persist_result['message']}"}
                    
                    return {"success": True, "message": f"Role '{role_key}' created"}
                return {"success": False, "message": f"Role '{role_key}' not found and cannot be created (enabled=false)"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def _save_to_yaml(self) -> dict[str, Any]:
        """Save all roles to YAML configuration file.
        
        Returns:
            Dictionary with save status.
        """
        if not self._config_path:
            return {"success": False, "message": "No config path set"}
        
        try:
            existing_data = {}
            if self._config_path.exists():
                with open(self._config_path, encoding="utf-8") as f:
                    existing_data = yaml.safe_load(f) or {}
            
            roles_data = existing_data.get("roles", {})
            
            for role_key, role in self.roles.items():
                roles_data[role_key] = role.to_dict()
            
            existing_data["roles"] = roles_data
            
            import tempfile
            import shutil
            
            temp_path = self._config_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                yaml.dump(existing_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            shutil.move(str(temp_path), str(self._config_path))
            
            logger.info(f"Saved roles to {self._config_path}")
            return {"success": True, "message": "Roles saved successfully"}
            
        except Exception as e:
            logger.error(f"Failed to save roles to {self._config_path}: {e}")
            return {"success": False, "message": str(e)}
    
    def get_role_config(self, role_key: str) -> dict[str, Any] | None:
        """Get full configuration for a role.
        
        Args:
            role_key: The role identifier.
            
        Returns:
            Dictionary with role configuration or None if not found.
        """
        role = self.roles.get(role_key)
        if not role:
            return None
        return role.to_dict()
    
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
        result = []
        for key, role in self.roles.items():
            if not role.enabled:
                continue
            role_info = {
                "key": key,
                "name": role.name,
                "description": role.description,
                "icon": role.icon,
                "enabled": role.enabled,
                "has_custom_model": role.model_config is not None and role.model_config.model is not None,
            }
            if role.model_config:
                role_info["model_config"] = {
                    "provider": role.model_config.provider,
                    "model": role.model_config.model,
                }
            result.append(role_info)
        return result
    
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
            "image_processor": [
                "图片", "图像", "image", "图片识别", "图片分析", "看图",
                "生成图片", "画图", "文生图", "视觉", "vision", "ocr",
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
