"""Enhanced subagent manager for multi-agent coordination.

This module provides the SubagentManager class which supports:
- Role-based task assignment
- Independent model configuration per role
- Progress tracking and reporting
- Pause/resume/cancel functionality
- Workspace isolation
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

from loguru import logger

from nanobot.agent.roles.models import RoleDefinition
from nanobot.agent.tasks.models import Task, TaskStatus
from nanobot.agent.progress.tracker import ProgressTracker, ProgressStage
from nanobot.agent.context.packer import ContextPacker, ContextPackage
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.filesystem import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.web import WebSearchTool, WebFetchTool
from nanobot.agent.tools.weather import WeatherTool, WeatherForecastTool
from nanobot.bus.events import InboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.utils.helpers import ensure_dir

if TYPE_CHECKING:
    from nanobot.config.schema import Config
    from nanobot.agent.roles.manager import RoleManager
    from nanobot.agent.tasks.manager import TaskManager
    from nanobot.agent.providers.factory import ProviderFactory

SubagentLogLevel = str
SubagentLogType = str


@dataclass
class SubagentLogEntry:
    """A log entry for subagent execution."""
    timestamp: datetime
    level: SubagentLogLevel
    type: SubagentLogType
    message: str
    data: dict[str, Any] | None = None


@dataclass
class SubagentConfig:
    """Configuration for a running subagent."""
    role: RoleDefinition
    task: Task
    context: ContextPackage
    workspace: Path
    tracker: ProgressTracker
    provider: LLMProvider
    model: str
    temperature: float
    max_tokens: int
    logs: list[SubagentLogEntry] = field(default_factory=list)


class SubagentManager:
    """Enhanced subagent manager with role-based task execution.
    
    This manager enables:
    1. Parallel execution of multiple subagents
    2. Role-specific model configuration
    3. Progress tracking and control
    4. Workspace isolation
    5. Context passing from main agent
    """
    
    def __init__(
        self,
        main_provider: LLMProvider,
        main_config: Config,
        workspace: Path,
        bus: MessageBus,
        role_manager: RoleManager,
        task_manager: TaskManager,
        provider_factory: ProviderFactory,
        main_model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        web_search_api_key: str | None = None,
        weather_api_key: str | None = None,
        exec_config: Any = None,
        restrict_to_workspace: bool = False,
    ):
        """Initialize the enhanced subagent manager.
        
        Args:
            main_provider: The main agent's LLM provider.
            main_config: The main configuration.
            workspace: The workspace directory.
            bus: The message bus for communication.
            role_manager: The role manager.
            task_manager: The task manager.
            provider_factory: The provider factory for creating subagent providers.
            main_model: The main agent's model name.
            temperature: Default temperature for subagents.
            max_tokens: Default max tokens for subagents.
            web_search_api_key: Optional web search API key.
            weather_api_key: Optional weather API key.
            exec_config: Execution tool configuration.
            restrict_to_workspace: Whether to restrict file operations to workspace.
        """
        self.main_provider = main_provider
        self.main_config = main_config
        self.main_model = main_model
        self.workspace = workspace
        self.bus = bus
        self.role_manager = role_manager
        self.task_manager = task_manager
        self.provider_factory = provider_factory
        self.default_temperature = temperature
        self.default_max_tokens = max_tokens
        self._web_search_api_key = web_search_api_key
        self._weather_api_key = weather_api_key
        self.exec_config = exec_config
        self.restrict_to_workspace = restrict_to_workspace

    @property
    def web_search_api_key(self) -> str:
        if self.main_config and hasattr(self.main_config, 'tools'):
            return getattr(self.main_config.tools.web.search, 'api_key', None) or self._web_search_api_key or ""
        return self._web_search_api_key or ""

    @property
    def weather_api_key(self) -> str:
        if self.main_config and hasattr(self.main_config, 'tools'):
            return getattr(self.main_config.tools.weather.weather, 'api_key', None) or self._weather_api_key or ""
        return self._weather_api_key or ""
        
        self._running_subagents: dict[str, asyncio.Task] = {}
        self._subagent_configs: dict[str, SubagentConfig] = {}
        self._pause_events: dict[str, asyncio.Event] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}
    
    async def spawn_with_role(
        self,
        task: Task,
        role_name: str,
        context: ContextPackage,
        origin_channel: str,
        origin_chat_id: str,
    ) -> str:
        """Spawn a subagent with a specific role.
        
        Args:
            task: The task to execute.
            role_name: The role to assign.
            context: The context package for the task.
            origin_channel: The origin channel for responses.
            origin_chat_id: The origin chat ID for responses.
            
        Returns:
            Status message.
        """
        role = self.role_manager.get_role(role_name)
        if not role:
            logger.error(f"Role not found: {role_name}")
            return f"错误：角色 '{role_name}' 不存在"
        
        subagent_workspace = self._create_workspace(task.id)
        
        tracker = ProgressTracker(task.id, self.bus, self.task_manager)
        
        provider, model = self._get_provider_for_role(role)
        
        temperature = role.model_config.temperature if role.model_config and role.model_config.temperature else self.default_temperature
        max_tokens = role.model_config.max_tokens if role.model_config and role.model_config.max_tokens else self.default_max_tokens
        
        config = SubagentConfig(
            role=role,
            task=task,
            context=context,
            workspace=subagent_workspace,
            tracker=tracker,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._subagent_configs[task.id] = config
        
        pause_event = asyncio.Event()
        pause_event.set()
        self._pause_events[task.id] = pause_event
        
        cancel_event = asyncio.Event()
        self._cancel_events[task.id] = cancel_event
        
        task.status = TaskStatus.RUNNING
        task.subagent_id = task.id
        task.workspace_path = subagent_workspace
        task.started_at = datetime.now()
        self.task_manager.tasks[task.id] = task
        
        bg_task = asyncio.create_task(
            self._run_subagent(task.id, origin_channel, origin_chat_id)
        )
        self._running_subagents[task.id] = bg_task
        bg_task.add_done_callback(lambda _: self._cleanup_subagent(task.id))
        
        logger.info(f"Spawned subagent [{task.id}] with role '{role_name}', model '{model}'")
        return f"子Agent [{role.get_display_name()}] 已启动 (ID: {task.id}, 模型: {model})"
    
    def _create_workspace(self, task_id: str) -> Path:
        """Create an isolated workspace for a subagent.
        
        Args:
            task_id: The task ID.
            
        Returns:
            Path to the created workspace.
        """
        workspace = self.workspace / "subagents" / task_id
        workspace = ensure_dir(workspace)
        
        (workspace / "input").mkdir(exist_ok=True)
        (workspace / "output").mkdir(exist_ok=True)
        (workspace / "temp").mkdir(exist_ok=True)
        
        logger.debug(f"Created workspace for subagent [{task_id}]: {workspace}")
        return workspace
    
    def _get_provider_for_role(self, role: RoleDefinition) -> tuple[LLMProvider, str]:
        """Get the provider and model for a role.
        
        Args:
            role: The role definition.
            
        Returns:
            Tuple of (provider, model_name).
        """
        return self.provider_factory.create_provider(role.model_config)
    
    def _build_tools_for_role(self, role: RoleDefinition, workspace: Path) -> ToolRegistry:
        """Build a tool registry for a role based on its capabilities.
        
        Args:
            role: The role definition.
            workspace: The subagent's workspace.
            
        Returns:
            Tool registry with allowed tools.
        """
        tools = ToolRegistry()
        allowed_dir = workspace if self.restrict_to_workspace else None
        
        capabilities = role.capabilities
        
        if capabilities.is_tool_allowed("read_file"):
            tools.register(ReadFileTool(workspace=workspace, allowed_dir=allowed_dir))
        
        if capabilities.is_tool_allowed("write_file"):
            tools.register(WriteFileTool(workspace=workspace, allowed_dir=allowed_dir))
        
        if capabilities.is_tool_allowed("edit_file"):
            tools.register(EditFileTool(workspace=workspace, allowed_dir=allowed_dir))
        
        if capabilities.is_tool_allowed("list_dir"):
            tools.register(ListDirTool(workspace=workspace, allowed_dir=allowed_dir))
        
        if capabilities.is_tool_allowed("exec"):
            tools.register(ExecTool(
                working_dir=str(workspace),
                timeout=self.exec_config.timeout if self.exec_config else 120,
                restrict_to_workspace=self.restrict_to_workspace,
            ))
        
        if capabilities.is_tool_allowed("web_search"):
            tools.register(WebSearchTool(api_key_getter=lambda: self.web_search_api_key))
        
        if capabilities.is_tool_allowed("web_fetch"):
            tools.register(WebFetchTool())
        
        if capabilities.is_tool_allowed("weather"):
            tools.register(WeatherTool(api_key_getter=lambda: self.weather_api_key))
        
        if capabilities.is_tool_allowed("weather_forecast"):
            tools.register(WeatherForecastTool(api_key_getter=lambda: self.weather_api_key))
        
        if capabilities.is_tool_allowed("understand_image"):
            from nanobot.agent.tools.image_gen import ImageUnderstandingTool
            tools.register(ImageUnderstandingTool(llm_provider=self.main_provider))
        
        if capabilities.is_tool_allowed("generate_image"):
            if self.main_config and hasattr(self.main_config, 'tools') and hasattr(self.main_config.tools, 'image_generation'):
                img_config = self.main_config.tools.image_generation
                if img_config and img_config.enabled:
                    from nanobot.agent.tools.image_gen import ImageGenerationTool
                    from nanobot.providers.image_provider import ImageGenerationProvider
                    img_provider = ImageGenerationProvider(
                        api_key=img_config.api_key or None,
                        api_base=img_config.api_base or None,
                        model=img_config.model or "wan21-turbo",
                    )
                    tools.register(ImageGenerationTool(
                        workspace=workspace,
                        allowed_dir=allowed_dir,
                        image_provider=img_provider,
                    ))
        
        logger.debug(f"Built tools for role '{role.name}': {tools.tool_names}")
        return tools
    
    def _build_system_prompt(self, config: SubagentConfig) -> str:
        """Build the system prompt for a subagent.
        
        Args:
            config: The subagent configuration.
            
        Returns:
            The system prompt.
        """
        role = config.role
        workspace = config.workspace
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        
        parts = [
            f"# {role.name}",
            "",
            f"## 当前时间",
            now,
            "",
            role.system_prompt,
            "",
            "## 工作空间",
            f"你的工作空间位于: {workspace}",
            "- 输入文件放在: input/",
            "- 输出文件放在: output/", 
            "- 临时文件放在: temp/",
            "",
            "## 能力边界",
            f"你可以使用以下工具: {', '.join(role.capabilities.allowed_tools) if role.capabilities.allowed_tools else '无限制'}",
        ]
        
        if role.capabilities.forbidden_tools:
            parts.append(f"你不能使用以下工具: {', '.join(role.capabilities.forbidden_tools)}")
        
        parts.extend([
            "",
            "## 重要规则",
            "1. 专注于完成分配给你的任务，不要做额外的事情",
            "2. 完成后提供清晰的结果摘要",
            "3. 如果遇到问题，说明原因并提出解决方案",
        ])
        
        return "\n".join(parts)
    
    def _build_task_prompt(self, config: SubagentConfig) -> str:
        """Build the task prompt for a subagent.
        
        Args:
            config: The subagent configuration.
            
        Returns:
            The task prompt.
        """
        context = config.context
        task = config.task
        
        parts = [
            f"# 任务",
            "",
            f"**标题**: {task.title}",
            "",
            f"**描述**: {task.description}",
            "",
            context.to_prompt_section(),
        ]
        
        return "\n".join(parts)
    
    async def _run_subagent(
        self,
        task_id: str,
        origin_channel: str,
        origin_chat_id: str,
    ) -> None:
        """Run a subagent task.
        
        Args:
            task_id: The task ID.
            origin_channel: The origin channel.
            origin_chat_id: The origin chat ID.
        """
        config = self._subagent_configs.get(task_id)
        if not config:
            logger.error(f"No config found for subagent [{task_id}]")
            return
        
        task = config.task
        tracker = config.tracker
        pause_event = self._pause_events.get(task_id)
        cancel_event = self._cancel_events.get(task_id)
        
        try:
            self.add_log(task_id, "info", "system", f"🚀 启动子Agent: {config.role.name}")
            
            await tracker.report(
                ProgressStage.INITIALIZING,
                5,
                "正在初始化工作环境..."
            )
            self.add_log(task_id, "info", "progress", "正在初始化工作环境...")
            
            tools = self._build_tools_for_role(config.role, config.workspace)
            self.add_log(task_id, "info", "system", f"已加载 {len(tools.tool_names)} 个工具: {', '.join(tools.tool_names)}")
            
            system_prompt = self._build_system_prompt(config)
            task_prompt = self._build_task_prompt(config)
            
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task_prompt},
            ]
            
            await tracker.report(
                ProgressStage.ANALYZING,
                10,
                "正在分析任务..."
            )
            self.add_log(task_id, "info", "progress", f"📝 任务: {task.title[:50]}...")
            
            result = await self._execute_with_progress(
                task_id=task_id,
                messages=messages,
                tools=tools,
                tracker=tracker,
                pause_event=pause_event,
                cancel_event=cancel_event,
                provider=config.provider,
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                max_iterations=config.role.max_iterations,
                timeout=config.role.timeout,
            )
            
            artifacts = self._collect_artifacts(config.workspace)
            
            await tracker.report_complete("任务完成", artifacts)
            self.add_log(task_id, "info", "system", f"✅ 任务完成! 产生了 {len(artifacts)} 个产物")
            
            self.task_manager.complete_task(task_id, result)
            
            await self._announce_completion(task, result, origin_channel, origin_chat_id)
            
        except asyncio.CancelledError:
            logger.info(f"Subagent [{task_id}] was cancelled")
            self.add_log(task_id, "warning", "system", "❌ 任务被取消")
            self.task_manager.cancel_task(task_id)
            await tracker.report_failure("任务被取消")
            
        except asyncio.TimeoutError:
            error_msg = f"任务超时 ({config.role.timeout}秒)"
            logger.error(f"Subagent [{task_id}] timed out")
            self.add_log(task_id, "error", "error", f"⏱️ {error_msg}")
            self.task_manager.fail_task(task_id, error_msg)
            await tracker.report_failure(error_msg)
            await self._announce_failure(task, error_msg, origin_channel, origin_chat_id)
            
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Subagent [{task_id}] failed")
            self.add_log(task_id, "error", "error", f"❌ 任务失败: {error_msg[:200]}")
            self.task_manager.fail_task(task_id, error_msg)
            await tracker.report_failure(error_msg)
            await self._announce_failure(task, error_msg, origin_channel, origin_chat_id)
    
    async def _execute_with_progress(
        self,
        task_id: str,
        messages: list[dict],
        tools: ToolRegistry,
        tracker: ProgressTracker,
        pause_event: asyncio.Event | None,
        cancel_event: asyncio.Event | None,
        provider: LLMProvider,
        model: str,
        temperature: float,
        max_tokens: int,
        max_iterations: int,
        timeout: int,
    ) -> str:
        """Execute the agent loop with progress reporting.
        
        Args:
            task_id: The task ID.
            messages: The message list.
            tools: The tool registry.
            tracker: The progress tracker.
            pause_event: Event for pause control.
            cancel_event: Event for cancel control.
            provider: The LLM provider.
            model: The model name.
            temperature: Temperature parameter.
            max_tokens: Max tokens parameter.
            max_iterations: Maximum iterations.
            timeout: Timeout in seconds.
            
        Returns:
            The final result.
        """
        async with asyncio.timeout(timeout):
            iteration = 0
            final_result = None
            
            while iteration < max_iterations:
                if cancel_event and cancel_event.is_set():
                    raise asyncio.CancelledError("Task was cancelled")
                
                if pause_event:
                    await pause_event.wait()
                
                iteration += 1
                self.add_log(task_id, "info", "progress", f"🔄 开始迭代 {iteration}/{max_iterations}")
                
                progress = min(90, 10 + (iteration / max_iterations) * 80)
                
                await tracker.report(
                    ProgressStage.EXECUTING,
                    int(progress),
                    f"正在执行 (迭代 {iteration}/{max_iterations})..."
                )
                
                response = await provider.chat(
                    messages=messages,
                    tools=tools.get_definitions(),
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                if response.has_tool_calls:
                    tool_call_dicts = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                            },
                        }
                        for tc in response.tool_calls
                    ]
                    messages.append({
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": tool_call_dicts,
                    })
                    
                    for tc in response.tool_calls:
                        args_str = json.dumps(tc.arguments, ensure_ascii=False)
                        logger.debug(f"Subagent [{task_id}] tool call: {tc.name}({args_str[:100]})")
                        self.add_log(task_id, "info", "tool", f"🔧 调用工具: {tc.name}", {"arguments": tc.arguments})
                        
                        result = await tools.execute(tc.name, tc.arguments)
                        self.add_log(task_id, "info", "tool", f"📤 工具返回: {tc.name}", {"result": result[:500] if len(result) > 500 else result})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": result,
                        })
                else:
                    final_result = response.content
                    break
            
            await tracker.report(
                ProgressStage.VERIFYING,
                92,
                "正在验证结果..."
            )
            
            await tracker.report(
                ProgressStage.FINALIZING,
                95,
                "正在整理输出..."
            )
            
            return final_result or "任务完成但无输出结果"
    
    def _collect_artifacts(self, workspace: Path) -> list[str]:
        """Collect artifacts from the workspace.
        
        Args:
            workspace: The workspace path.
            
        Returns:
            List of artifact paths.
        """
        artifacts = []
        output_dir = workspace / "output"
        
        if output_dir.exists():
            for path in output_dir.rglob("*"):
                if path.is_file():
                    artifacts.append(str(path))
        
        return artifacts
    
    async def _announce_completion(
        self,
        task: Task,
        result: str,
        origin_channel: str,
        origin_chat_id: str,
    ) -> None:
        """Announce task completion to the main agent.
        
        Args:
            task: The completed task.
            result: The task result.
            origin_channel: The origin channel.
            origin_chat_id: The origin chat ID.
        """
        role = self.role_manager.get_role(task.role)
        role_name = role.get_display_name() if role else task.role or "Agent"
        
        artifacts = self._collect_artifacts(task.workspace_path)
        
        content = f"""📋 **[{role_name}]** 任务已完成

**任务**: {task.title}

**结果**:
{result[:1500]}{"..." if len(result) > 1500 else ""}

{f"📁 产物: {len(artifacts)} 个文件" if artifacts else ""}"""
        
        msg = InboundMessage(
            channel="system",
            sender_id="agent",
            chat_id=f"{origin_channel}:{origin_chat_id}",
            content=content,
            metadata={
                "type": "subagent_result",
                "task_id": task.id,
                "status": "completed",
                "role": task.role,
            },
        )
        
        await self.bus.publish_inbound(msg)
        logger.debug(f"Announced completion for task [{task.id}]")
    
    async def _announce_failure(
        self,
        task: Task,
        error: str,
        origin_channel: str,
        origin_chat_id: str,
    ) -> None:
        """Announce task failure to the main agent.
        
        Args:
            task: The failed task.
            error: The error message.
            origin_channel: The origin channel.
            origin_chat_id: The origin chat ID.
        """
        role = self.role_manager.get_role(task.role)
        role_name = role.get_display_name() if role else task.role or "Agent"
        
        content = f"""📋 **[{role_name}]** 任务失败

**任务**: {task.title}

**错误**: {error}"""
        
        msg = InboundMessage(
            channel="system",
            sender_id="agent",
            chat_id=f"{origin_channel}:{origin_chat_id}",
            content=content,
            metadata={
                "type": "subagent_result",
                "task_id": task.id,
                "status": "failed",
                "role": task.role,
            },
        )
        
        await self.bus.publish_inbound(msg)
        logger.debug(f"Announced failure for task [{task.id}]")
    
    async def pause(self, task_id: str) -> bool:
        """Pause a running subagent.
        
        Args:
            task_id: The task ID.
            
        Returns:
            True if paused successfully.
        """
        if task_id not in self._subagent_configs:
            return False
        
        pause_event = self._pause_events.get(task_id)
        if pause_event:
            pause_event.clear()
        
        tracker = self._subagent_configs[task_id].tracker
        tracker.pause()
        
        self.task_manager.pause_task(task_id)
        
        logger.info(f"Paused subagent [{task_id}]")
        return True
    
    async def resume(self, task_id: str) -> bool:
        """Resume a paused subagent.
        
        Args:
            task_id: The task ID.
            
        Returns:
            True if resumed successfully.
        """
        if task_id not in self._subagent_configs:
            return False
        
        pause_event = self._pause_events.get(task_id)
        if pause_event:
            pause_event.set()
        
        tracker = self._subagent_configs[task_id].tracker
        tracker.resume()
        
        self.task_manager.resume_task(task_id)
        
        logger.info(f"Resumed subagent [{task_id}]")
        return True
    
    async def cancel(self, task_id: str) -> bool:
        """Cancel a running subagent.
        
        Args:
            task_id: The task ID.
            
        Returns:
            True if cancelled successfully.
        """
        if task_id not in self._running_subagents:
            return False
        
        cancel_event = self._cancel_events.get(task_id)
        if cancel_event:
            cancel_event.set()
        
        tracker = self._subagent_configs.get(task_id)
        if tracker:
            tracker.tracker.cancel()
        
        pause_event = self._pause_events.get(task_id)
        if pause_event:
            pause_event.set()
        
        bg_task = self._running_subagents.get(task_id)
        if bg_task:
            bg_task.cancel()
            try:
                await bg_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Cancelled subagent [{task_id}]")
        return True
    
    def get_status(self, task_id: str) -> dict | None:
        """Get the status of a subagent.
        
        Args:
            task_id: The task ID.
            
        Returns:
            Status dictionary or None.
        """
        config = self._subagent_configs.get(task_id)
        if not config:
            return None
        
        task = config.task
        tracker = config.tracker
        
        return {
            "task_id": task_id,
            "title": task.title,
            "role": config.role.name,
            "role_icon": config.role.icon,
            "status": task.status.value,
            "progress": task.progress,
            "progress_message": task.progress_message,
            "is_paused": tracker.is_paused(),
            "model": config.model,
            "workspace": str(config.workspace),
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "log_count": len(config.logs),
        }
    
    def add_log(
        self,
        task_id: str,
        level: SubagentLogLevel,
        type: SubagentLogType,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Add a log entry to a subagent.
        
        Args:
            task_id: The task ID.
            level: Log level (info, debug, warning, error).
            type: Log type (system, tool, llm, progress, error).
            message: Log message.
            data: Optional additional data.
        """
        config = self._subagent_configs.get(task_id)
        if not config:
            return
        
        entry = SubagentLogEntry(
            timestamp=datetime.now(),
            level=level,
            type=type,
            message=message,
            data=data,
        )
        config.logs.append(entry)
    
    def get_logs(self, task_id: str, since_index: int = 0) -> list[dict]:
        """Get log entries for a subagent.
        
        Args:
            task_id: The task ID.
            since_index: Return logs after this index.
            
        Returns:
            List of log entry dictionaries.
        """
        config = self._subagent_configs.get(task_id)
        if not config:
            return []
        
        logs = config.logs[since_index:]
        return [
            {
                "index": since_index + i,
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "type": log.type,
                "message": log.message,
                "data": log.data,
            }
            for i, log in enumerate(logs)
        ]
    
    def list_active(self) -> list[dict]:
        """List all active subagents.
        
        Returns:
            List of status dictionaries.
        """
        return [
            self.get_status(task_id)
            for task_id in self._running_subagents.keys()
            if self.get_status(task_id) is not None
        ]
    
    def _cleanup_subagent(self, task_id: str) -> None:
        """Clean up a completed subagent.
        
        Args:
            task_id: The task ID.
        """
        config = self._subagent_configs.get(task_id)
        if config:
            config.logs.clear()
            if hasattr(config.tracker, 'reset'):
                config.tracker.reset()
        
        self._running_subagents.pop(task_id, None)
        self._subagent_configs.pop(task_id, None)
        self._pause_events.pop(task_id, None)
        self._cancel_events.pop(task_id, None)
        
        logger.debug(f"Cleaned up subagent [{task_id}] resources")
