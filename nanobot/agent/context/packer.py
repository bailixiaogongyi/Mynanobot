"""Context packer for preparing task context for subagents."""

from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class ContextPackage:
    """Packaged context for a subagent task.
    
    Contains all the information a subagent needs to complete
    its task effectively, extracted from the main agent's context.
    """
    task_background: str = ""
    user_requirements: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    reference_materials: dict[str, str] = field(default_factory=dict)
    relevant_history: list[dict[str, Any]] = field(default_factory=list)
    workspace_info: dict[str, Any] = field(default_factory=dict)
    output_expectations: str = ""
    
    def to_prompt_section(self) -> str:
        """Convert to a prompt section for the subagent.
        
        Returns:
            Formatted prompt section.
        """
        parts = []
        
        if self.task_background:
            parts.append(f"## 任务背景\n\n{self.task_background}")
        
        if self.user_requirements:
            req_list = "\n".join(f"- {r}" for r in self.user_requirements)
            parts.append(f"## 用户需求\n\n{req_list}")
        
        if self.constraints:
            const_list = "\n".join(f"- {c}" for c in self.constraints)
            parts.append(f"## 约束条件\n\n{const_list}")
        
        if self.reference_materials:
            ref_parts = []
            for name, content in self.reference_materials.items():
                ref_parts.append(f"### {name}\n\n{content}")
            parts.append(f"## 参考材料\n\n" + "\n\n".join(ref_parts))
        
        if self.output_expectations:
            parts.append(f"## 输出期望\n\n{self.output_expectations}")
        
        return "\n\n---\n\n".join(parts)


class ContextPacker:
    """Packs context information for subagent tasks.
    
    This class extracts and packages relevant context from the main
    agent's session and memory to provide subagents with the information
    they need without overwhelming them with irrelevant data.
    """
    
    def __init__(
        self,
        session_history: list[dict[str, Any]] | None = None,
        memory_context: str | None = None,
        workspace_path: str | None = None,
    ):
        """Initialize the context packer.
        
        Args:
            session_history: Recent session history from main agent.
            memory_context: Long-term memory context.
            workspace_path: Path to the workspace.
        """
        self.session_history = session_history or []
        self.memory_context = memory_context or ""
        self.workspace_path = workspace_path or ""
    
    def pack_for_task(
        self,
        task_description: str,
        role_name: str | None = None,
        role_description: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> ContextPackage:
        """Pack context for a specific task.
        
        Args:
            task_description: Description of the task.
            role_name: Name of the role being assigned.
            role_description: Description of the role.
            additional_context: Additional context from the main agent.
            
        Returns:
            Packaged context.
        """
        background = self._build_background(task_description, role_name, role_description)
        requirements = self._extract_requirements(task_description)
        constraints = self._build_constraints(role_name, role_description)
        reference_materials = self._extract_reference_materials(task_description)
        relevant_history = self._filter_relevant_history(task_description)
        output_expectations = self._infer_expectations(task_description, role_name)
        
        if additional_context:
            if "background" in additional_context:
                background = f"{background}\n\n{additional_context['background']}"
            if "requirements" in additional_context:
                requirements.extend(additional_context["requirements"])
            if "constraints" in additional_context:
                constraints.extend(additional_context["constraints"])
        
        return ContextPackage(
            task_background=background,
            user_requirements=requirements,
            constraints=constraints,
            reference_materials=reference_materials,
            relevant_history=relevant_history,
            workspace_info={"path": self.workspace_path},
            output_expectations=output_expectations,
        )
    
    def _build_background(
        self,
        task_description: str,
        role_name: str | None,
        role_description: str | None,
    ) -> str:
        """Build task background description.
        
        Args:
            task_description: The task description.
            role_name: Name of the assigned role.
            role_description: Description of the role.
            
        Returns:
            Background text.
        """
        parts = [f"你需要完成以下任务：\n\n{task_description}"]
        
        if role_name and role_description:
            parts.append(f"\n你被分配的角色是：{role_name}")
            parts.append(f"角色职责：{role_description}")
        
        if self.memory_context:
            relevant_memory = self._extract_relevant_memory(task_description)
            if relevant_memory:
                parts.append(f"\n相关记忆：\n{relevant_memory}")
        
        return "\n".join(parts)
    
    def _extract_requirements(self, task_description: str) -> list[str]:
        """Extract requirements from task description.
        
        Args:
            task_description: The task description.
            
        Returns:
            List of extracted requirements.
        """
        requirements = []
        
        keywords = ["需要", "要求", "必须", "应该", "要", "need", "require", "must", "should"]
        
        lines = task_description.split("\n")
        for line in lines:
            line = line.strip()
            if any(kw in line.lower() for kw in keywords):
                requirements.append(line)
        
        if not requirements:
            requirements.append("完成分配的任务")
        
        return requirements
    
    def _build_constraints(
        self,
        role_name: str | None,
        role_description: str | None,
    ) -> list[str]:
        """Build constraint list.
        
        Args:
            role_name: Name of the role.
            role_description: Description of the role.
            
        Returns:
            List of constraints.
        """
        constraints = []
        
        constraints.append("你不能创建其他子Agent")
        constraints.append("你不能直接与用户通信")
        constraints.append("你不能使用spawn工具")
        constraints.append("你不能使用message工具")
        
        if role_name:
            constraints.append(f"你必须专注于{role_name}的职责范围")
        
        return constraints
    
    def _extract_reference_materials(self, task_description: str) -> dict[str, str]:
        """Extract reference materials from context.
        
        Args:
            task_description: The task description.
            
        Returns:
            Dictionary of reference materials.
        """
        materials = {}
        
        if self.memory_context:
            relevant = self._extract_relevant_memory(task_description)
            if relevant:
                materials["相关记忆"] = relevant
        
        return materials
    
    def _filter_relevant_history(self, task_description: str) -> list[dict[str, Any]]:
        """Filter relevant history from session.
        
        Args:
            task_description: The task description.
            
        Returns:
            List of relevant history entries.
        """
        if not self.session_history:
            return []
        
        relevant = []
        task_keywords = set(task_description.lower().split())
        
        for msg in self.session_history[-20:]:
            content = msg.get("content", "")
            if not content:
                continue
            
            msg_keywords = set(content.lower().split())
            overlap = len(task_keywords & msg_keywords)
            
            if overlap > 2 or msg.get("role") == "user":
                relevant.append({
                    "role": msg.get("role"),
                    "content": content[:500],
                })
        
        return relevant[-5:]
    
    def _extract_relevant_memory(self, task_description: str) -> str:
        """Extract relevant memory content.
        
        Args:
            task_description: The task description.
            
        Returns:
            Relevant memory content.
        """
        if not self.memory_context:
            return ""
        
        task_keywords = set(task_description.lower().split())
        
        lines = self.memory_context.split("\n")
        relevant_lines = []
        
        for line in lines:
            line_keywords = set(line.lower().split())
            overlap = len(task_keywords & line_keywords)
            
            if overlap > 1:
                relevant_lines.append(line)
        
        if relevant_lines:
            return "\n".join(relevant_lines[:10])
        
        return ""
    
    def _infer_expectations(self, task_description: str, role_name: str | None) -> str:
        """Infer output expectations from task.
        
        Args:
            task_description: The task description.
            role_name: Name of the role.
            
        Returns:
            Expected output description.
        """
        task_lower = task_description.lower()
        
        if "文档" in task_lower or "document" in task_lower or "报告" in task_lower:
            return "提供格式规范的文档，使用Markdown格式，结构清晰，内容完整。"
        
        if "代码" in task_lower or "code" in task_lower or "脚本" in task_lower:
            return "提供可运行的代码，包含必要的注释，遵循编码规范。"
        
        if "分析" in task_lower or "analysis" in task_lower or "数据" in task_lower:
            return "提供清晰的分析结果，包含关键发现和建议。"
        
        if "研究" in task_lower or "research" in task_lower or "调研" in task_lower:
            return "提供结构化的研究结果，包含信息来源和结论。"
        
        return "提供清晰、完整的结果反馈。"
