"""Enhanced spawn tool with role-based task assignment."""

from typing import Any, TYPE_CHECKING

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.agent.subagent_manager import SubagentManager
    from nanobot.agent.tasks.manager import TaskManager
    from nanobot.agent.context.packer import ContextPacker
    from nanobot.session.manager import Session


class SpawnTool(Tool):
    """Enhanced spawn tool for creating subagents with role assignment.
    
    Features:
    - Role-based task assignment
    - Context passing from main agent
    - Automatic role matching
    - Progress tracking integration
    """
    
    def __init__(
        self,
        manager: "SubagentManager",
        task_manager: "TaskManager",
        context_packer: "ContextPacker",
    ):
        """Initialize the spawn tool.
        
        Args:
            manager: The subagent manager.
            task_manager: The task manager.
            context_packer: The context packer.
        """
        self._manager = manager
        self._task_manager = task_manager
        self._context_packer = context_packer
        self._origin_channel = "cli"
        self._origin_chat_id = "direct"
        self._session: Session | None = None
        self._memory_context: str | None = None
    
    def set_context(
        self,
        channel: str,
        chat_id: str,
        session: "Session | None" = None,
        memory_context: str | None = None,
    ) -> None:
        """Set the context for spawn operations.
        
        Args:
            channel: The origin channel.
            chat_id: The origin chat ID.
            session: Optional session for context extraction.
            memory_context: Optional memory context.
        """
        self._origin_channel = channel
        self._origin_chat_id = chat_id
        self._session = session
        self._memory_context = memory_context
    
    @property
    def name(self) -> str:
        return "spawn"
    
    @property
    def description(self) -> str:
        return """创建一个子Agent来执行特定任务。

使用场景：
- 需要并行处理多个独立任务
- 任务需要特定专业技能（文档编写、数据分析、代码开发等）
- 任务耗时较长，适合后台执行

可用角色：
- document_writer: 文档编写专家 📝
- code_developer: 代码开发专家 💻  
- data_analyst: 数据分析专家 📊
- researcher: 研究分析专家 🔍
- image_processor: 图像处理专家 🖼️

如果不指定角色，系统会根据任务内容自动匹配最合适的角色。

注意：子Agent会在后台运行，完成后会自动汇报结果。你可以同时创建多个子Agent并行执行任务。"""
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "任务描述，清晰说明需要完成的工作",
                },
                "role": {
                    "type": "string",
                    "description": "角色名称，可选值: document_writer, code_developer, data_analyst, researcher, image_processor",
                    "enum": ["document_writer", "code_developer", "data_analyst", "researcher", "image_processor"],
                },
                "title": {
                    "type": "string",
                    "description": "任务标题（可选，用于显示）",
                },
                "priority": {
                    "type": "string",
                    "description": "优先级",
                    "enum": ["low", "medium", "high", "urgent"],
                    "default": "medium",
                },
                "context_hint": {
                    "type": "string",
                    "description": "额外的上下文提示，帮助子Agent理解任务背景（可选）",
                },
            },
            "required": ["task"],
        }
    
    async def execute(
        self,
        task: str,
        role: str | None = None,
        title: str | None = None,
        priority: str = "medium",
        context_hint: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Execute the spawn operation.
        
        Args:
            task: Task description.
            role: Optional role name.
            title: Optional task title.
            priority: Task priority.
            context_hint: Optional context hint.
            
        Returns:
            Status message.
        """
        from nanobot.agent.tasks.models import TaskPriority, TaskContext
        from nanobot.agent.context.packer import ContextPacker
        
        role_manager = self._manager.role_manager
        
        if not role:
            role = role_manager.match_role_for_task(task)
        
        role_def = role_manager.get_role(role)
        if not role_def:
            return f"错误：未找到角色 '{role}'"
        
        task_title = title or task[:50] + ("..." if len(task) > 50 else "")
        
        task_priority = TaskPriority.from_string(priority)
        
        history = []
        if self._session:
            history = self._session.get_history(max_messages=20)
        
        packer = ContextPacker(
            session_history=history,
            memory_context=self._memory_context,
            workspace_path=str(self._manager.workspace),
        )
        
        additional_context = {}
        if context_hint:
            additional_context["background"] = context_hint
        
        context_package = packer.pack_for_task(
            task_description=task,
            role_name=role,
            role_description=role_def.description,
            additional_context=additional_context,
        )
        
        task_context = TaskContext(
            background=context_package.task_background,
            requirements=context_package.user_requirements,
            constraints=context_package.constraints,
            reference_files=[],
            parent_session_key=f"{self._origin_channel}:{self._origin_chat_id}",
            relevant_history=context_package.relevant_history,
        )
        
        task_obj = self._task_manager.create_task(
            title=task_title,
            description=task,
            context=task_context,
            role=role,
            priority=task_priority,
            origin_channel=self._origin_channel,
            origin_chat_id=self._origin_chat_id,
        )
        
        result = await self._manager.spawn_with_role(
            task=task_obj,
            role_name=role,
            context=task_context,
            origin_channel=self._origin_channel,
            origin_chat_id=self._origin_chat_id,
        )
        
        return result
