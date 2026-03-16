"""Agent loop: the core processing engine."""

from __future__ import annotations

import asyncio
import json
import re
from collections import defaultdict
from contextlib import AsyncExitStack
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from loguru import logger

from nanobot.agent.context import ContextBuilder
from nanobot.agent.memory import MemoryStore
from nanobot.agent.subagent_manager import SubagentManager
from nanobot.agent.tools.cron import CronTool
from nanobot.agent.tools.filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.spawn import SpawnTool
from nanobot.agent.tools.web import WebFetchTool, WebSearchTool
from nanobot.agent.tools.weather import WeatherTool, WeatherForecastTool
from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.session.manager import Session, SessionManager

if TYPE_CHECKING:
    from nanobot.config.schema import ChannelsConfig, ExecToolConfig
    from nanobot.cron.service import CronService


class AgentLoop:
    """
    The agent loop is the core processing engine.

    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """

    _USER_FRIENDLY_ERRORS = {
        "PermissionError": "I don't have permission to access that resource.",
        "FileNotFoundError": "The file or directory was not found.",
        "TimeoutError": "The operation took too long and was cancelled.",
        "ConnectionError": "There was a problem connecting to a service.",
        "ValueError": "There was a problem with the input provided.",
        "KeyError": "A required configuration or data was not found.",
        "default": "An unexpected error occurred. Please try again later."
    }

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 40,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        memory_window: int = 100,
        web_search_api_key: str | None = None,
        weather_api_key: str | None = None,
        exec_config: ExecToolConfig | None = None,
        cron_service: CronService | None = None,
        restrict_to_workspace: bool = False,
        session_manager: SessionManager | None = None,
        mcp_servers: dict | None = None,
        channels_config: ChannelsConfig | None = None,
        config: Any | None = None,
        upload_dir: Path | None = None,
        image_generation_config: Any | None = None,
    ):
        from nanobot.config.schema import ExecToolConfig
        self.bus = bus
        self.channels_config = channels_config
        self.provider = provider
        self.workspace = workspace
        self._model = model or provider.get_default_model()
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.memory_window = memory_window
        self.web_search_api_key = web_search_api_key
        self.weather_api_key = weather_api_key
        self.exec_config = exec_config or ExecToolConfig()
        self.cron_service = cron_service
        self.restrict_to_workspace = restrict_to_workspace
        self.config = config
        self.upload_dir = upload_dir
        self.image_generation_config = image_generation_config

        self.context = ContextBuilder(workspace)
        self.sessions = session_manager or SessionManager(workspace)
        self.tools = ToolRegistry()
        
        self._init_subagent_system(
            provider=provider,
            workspace=workspace,
            bus=bus,
            config=config,
        )

        self._running = False
        self._mcp_servers = mcp_servers or {}
        self._mcp_stack: AsyncExitStack | None = None
        self._mcp_connected = False
        self._mcp_connecting = False
        self._consolidating: set[str] = set()
        self._consolidation_tasks: set[asyncio.Task] = set()
        self._consolidation_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._register_default_tools()

    @property
    def model(self) -> str:
        """Get the current model."""
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        """Set the model directly."""
        self._model = value

    @property
    def task_manager(self):
        """Get the task manager from subagents."""
        return self.subagents.task_manager if hasattr(self, 'subagents') else None

    @property
    def role_manager(self):
        """Get the role manager from subagents."""
        return self.subagents.role_manager if hasattr(self, 'subagents') else None

    def _init_subagent_system(
        self,
        provider: LLMProvider,
        workspace: Path,
        bus: MessageBus,
        config: Any | None,
    ) -> None:
        """Initialize the subagent system."""
        from nanobot.agent.roles.manager import RoleManager
        from nanobot.agent.tasks.manager import TaskManager
        from nanobot.agent.providers.factory import ProviderFactory
        from nanobot import config as nanobot_config
        
        role_manager = RoleManager()
        
        default_roles_path = Path(nanobot_config.__file__).parent / "roles.yaml"
        if default_roles_path.exists():
            role_manager._load_from_yaml(default_roles_path)
            logger.debug(f"Loaded default roles from {default_roles_path}")
        
        user_roles_path = workspace / "config" / "roles.yaml"
        if user_roles_path.exists():
            role_manager._load_from_yaml(user_roles_path)
            logger.debug(f"Loaded user roles from {user_roles_path}")
        
        task_manager = TaskManager(workspace, bus)
        provider_factory = ProviderFactory(config) if config else None
        
        self.subagents = SubagentManager(
            main_provider=provider,
            main_config=config,
            workspace=workspace,
            bus=bus,
            role_manager=role_manager,
            task_manager=task_manager,
            provider_factory=provider_factory,
            main_model=self._model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            web_search_api_key=self.web_search_api_key,
            weather_api_key=self.weather_api_key,
            exec_config=self.exec_config,
            restrict_to_workspace=self.restrict_to_workspace,
        )

    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        from nanobot.agent.context.packer import ContextPacker
        from nanobot.agent.tools.docx import (
            DocxReadStructureTool, DocxReadTextTool, DocxReadTablesTool,
            DocxSetFontTool, DocxSetParagraphFormatTool, DocxSetHeadingStyleTool,
            DocxSetTableStyleTool, DocxFromTemplateTool
        )
        from nanobot.agent.tools.legacy_docs import DocReadTool, DocToDocxTool
        from nanobot.agent.tools.excel import ExcelReadTool, ExcelWriteTool
        from nanobot.agent.tools.pdf import PdfReadTextTool, PdfExtractImagesTool
        from nanobot.agent.tools.ocr import OcrImageTool
        from nanobot.agent.tools.pptx import PptxReadTool, PptxCreateTool
        from nanobot.agent.tools.note_search import NoteSearchTool, NoteIndexTool
        from nanobot.agent.tools.return_file import ReturnFileTool
        
        allowed_dir = self.workspace if self.restrict_to_workspace else None
        for cls in (ReadFileTool, WriteFileTool, EditFileTool, ListDirTool):
            self.tools.register(cls(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(ExecTool(
            working_dir=str(self.workspace),
            timeout=self.exec_config.timeout,
            restrict_to_workspace=self.restrict_to_workspace,
        ))
        self.tools.register(WebSearchTool(api_key=self.web_search_api_key))
        self.tools.register(WebFetchTool())
        self.tools.register(WeatherTool(api_key=self.weather_api_key))
        self.tools.register(WeatherForecastTool(api_key=self.weather_api_key))
        self.tools.register(MessageTool(send_callback=self.bus.publish_outbound))
        
        context_packer = ContextPacker(self.workspace)
        self.tools.register(SpawnTool(
            manager=self.subagents,
            task_manager=self.subagents.task_manager,
            context_packer=context_packer,
        ))
        
        if self.cron_service:
            self.tools.register(CronTool(self.cron_service))
        
        for cls in (DocxReadStructureTool, DocxReadTextTool, DocxReadTablesTool,
                    DocxSetFontTool, DocxSetParagraphFormatTool, DocxSetHeadingStyleTool,
                    DocxSetTableStyleTool, DocxFromTemplateTool):
            self.tools.register(cls(workspace=self.workspace, allowed_dir=allowed_dir))
        
        self.tools.register(DocReadTool(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(DocToDocxTool(workspace=self.workspace, allowed_dir=allowed_dir))
        
        self.tools.register(ExcelReadTool(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(ExcelWriteTool(workspace=self.workspace, allowed_dir=allowed_dir))
        
        self.tools.register(PdfReadTextTool(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(PdfExtractImagesTool(workspace=self.workspace, allowed_dir=allowed_dir))
        
        self.tools.register(OcrImageTool(workspace=self.workspace, allowed_dir=allowed_dir))
        
        self.tools.register(PptxReadTool(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(PptxCreateTool(workspace=self.workspace, allowed_dir=allowed_dir))
        
        self.tools.register(ReturnFileTool(upload_dir=self.upload_dir))
        
        from nanobot.agent.tools.cached_result import GetCachedResultTool
        self.tools.register(GetCachedResultTool(context_builder=self.context))
        
        if self.image_generation_config and self.image_generation_config.enabled:
            from nanobot.agent.tools.image_gen import ImageGenerationTool
            from nanobot.providers.image_provider import ImageGenerationProvider
            
            img_provider = ImageGenerationProvider(
                api_key=self.image_generation_config.api_key or None,
                api_base=self.image_generation_config.api_base or None,
                model=self.image_generation_config.model or "wan21-turbo",
            )
            self.tools.register(ImageGenerationTool(
                workspace=self.workspace,
                allowed_dir=allowed_dir,
                image_provider=img_provider,
            ))
            logger.info(f"Registered image generation tool with provider: {self.image_generation_config.provider}")

    async def _connect_mcp(self) -> None:
        """Connect to configured MCP servers (one-time, lazy)."""
        if self._mcp_connected or self._mcp_connecting or not self._mcp_servers:
            return
        self._mcp_connecting = True
        from nanobot.agent.tools.mcp import connect_mcp_servers
        try:
            self._mcp_stack = AsyncExitStack()
            await self._mcp_stack.__aenter__()
            await connect_mcp_servers(self._mcp_servers, self.tools, self._mcp_stack)
            self._mcp_connected = True
        except Exception as e:
            logger.error("Failed to connect MCP servers (will retry next message): {}", e)
            if self._mcp_stack:
                try:
                    await self._mcp_stack.aclose()
                except Exception:
                    pass
                self._mcp_stack = None
        finally:
            self._mcp_connecting = False

    def _set_tool_context(self, channel: str, chat_id: str, message_id: str | None = None) -> None:
        """Update context for all tools that need routing info."""
        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool):
                message_tool.set_context(channel, chat_id, message_id)

        if spawn_tool := self.tools.get("spawn"):
            if isinstance(spawn_tool, SpawnTool):
                spawn_tool.set_context(channel, chat_id)

        if cron_tool := self.tools.get("cron"):
            if isinstance(cron_tool, CronTool):
                cron_tool.set_context(channel, chat_id)

    @staticmethod
    def _strip_think(text: str | None) -> str | None:
        """Remove <think>…</think> blocks that some models embed in content."""
        if not text:
            return None
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip() or None

    @staticmethod
    def _tool_hint(tool_calls: list) -> str:
        """Format tool calls as concise hint, e.g. 'web_search("query")'."""
        def _fmt(tc):
            val = next(iter(tc.arguments.values()), None) if tc.arguments else None
            if not isinstance(val, str):
                return tc.name
            return f'{tc.name}("{val[:40]}…")' if len(val) > 40 else f'{tc.name}("{val}")'
        return ", ".join(_fmt(tc) for tc in tool_calls)

    def _format_tool_result(self, tool_name: str, result: Any) -> str:
        """Format tool result for progress display."""
        if isinstance(result, str):
            if result.startswith("FILE_RETURNED:"):
                return result
            preview = result[:100] + "..." if len(result) > 100 else result
            return f"{tool_name}: {preview}"
        return f"{tool_name}: completed"

    async def _run_agent_loop(
        self,
        initial_messages: list[dict],
        on_progress: Callable[..., Awaitable[None]] | None = None,
    ) -> tuple[str | None, list[str], list[dict]]:
        """Run the agent iteration loop. Returns (final_content, tools_used, messages)."""
        messages = initial_messages
        iteration = 0
        final_content = None
        tools_used: list[str] = []

        while iteration < self.max_iterations:
            iteration += 1

            response = await self.provider.chat(
                messages=messages,
                tools=self.tools.get_definitions(),
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            if response.has_tool_calls:
                if on_progress:
                    clean = self._strip_think(response.content)
                    if clean:
                        await on_progress(clean)
                    await on_progress(self._tool_hint(response.tool_calls), tool_hint=True)

                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False)
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts,
                    reasoning_content=response.reasoning_content,
                )

                for tool_call in response.tool_calls:
                    tools_used.append(tool_call.name)
                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                    logger.info("Tool call: {}({})", tool_call.name, args_str[:200])
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    
                    if on_progress:
                        result_preview = self._format_tool_result(tool_call.name, result)
                        await on_progress(result_preview, tool_hint=True)
                    
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
            else:
                final_content = self._strip_think(response.content)
                messages = self.context.add_assistant_message(
                    messages, response.content,
                    reasoning_content=response.reasoning_content,
                )
                break

        if final_content is None and iteration >= self.max_iterations:
            logger.warning("Max iterations ({}) reached", self.max_iterations)
            final_content = (
                f"I reached the maximum number of tool call iterations ({self.max_iterations}) "
                "without completing the task. You can try breaking the task into smaller steps."
            )

        return final_content, tools_used, messages

    async def run(self) -> None:
        """Run the agent loop, processing messages from the bus."""
        self._running = True
        await self._connect_mcp()
        logger.info("Agent loop started")

        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_inbound(),
                    timeout=1.0
                )
                try:
                    response = await self._process_message(msg)
                    if response is not None:
                        await self.bus.publish_outbound(response)
                    elif msg.channel == "cli":
                        await self.bus.publish_outbound(OutboundMessage(
                            channel=msg.channel, chat_id=msg.chat_id, content="", metadata=msg.metadata or {},
                        ))
                except Exception as e:
                    logger.exception("Error processing message from {}:{}", msg.channel, msg.chat_id)
                    error_type = type(e).__name__
                    user_message = self._USER_FRIENDLY_ERRORS.get(
                        error_type, 
                        self._USER_FRIENDLY_ERRORS["default"]
                    )
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content=user_message
                    ))
            except asyncio.TimeoutError:
                continue

    async def close_mcp(self) -> None:
        """Close MCP connections."""
        if self._mcp_stack:
            try:
                await self._mcp_stack.aclose()
            except (RuntimeError, BaseExceptionGroup):
                pass  # MCP SDK cancel scope cleanup is noisy but harmless
            self._mcp_stack = None

    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        logger.info("Agent loop stopping")

    def _get_consolidation_lock(self, session_key: str) -> asyncio.Lock:
        return self._consolidation_locks[session_key]

    def _prune_consolidation_lock(self, session_key: str, lock: asyncio.Lock) -> None:
        """Drop lock entry if no longer in use."""
        if not lock.locked():
            self._consolidation_locks.pop(session_key, None)

    async def _process_message(
        self,
        msg: InboundMessage,
        session_key: str | None = None,
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> OutboundMessage | None:
        """Process a single inbound message and return the response."""
        # System messages: parse origin from chat_id ("channel:chat_id")
        if msg.channel == "system":
            channel, chat_id = (msg.chat_id.split(":", 1) if ":" in msg.chat_id
                                else ("cli", msg.chat_id))
            logger.info("Processing system message from {}", msg.sender_id)
            key = f"{channel}:{chat_id}"
            session = self.sessions.get_or_create(key)
            self._set_tool_context(channel, chat_id, msg.metadata.get("message_id"))
            history = session.get_history(max_messages=self.memory_window)
            messages = self.context.build_messages(
                history=history,
                current_message=msg.content, channel=channel, chat_id=chat_id,
            )
            final_content, _, all_msgs = await self._run_agent_loop(messages)
            self._save_turn(session, all_msgs, 1 + len(history))
            self.sessions.save(session)
            return OutboundMessage(channel=channel, chat_id=chat_id,
                                  content=final_content or "Background task completed.")

        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info("Processing message from {}:{}: {}", msg.channel, msg.sender_id, preview)

        key = session_key or msg.session_key
        session = self.sessions.get_or_create(key)

        # Slash commands
        cmd = msg.content.strip().lower()
        if cmd == "/new":
            lock = self._get_consolidation_lock(session.key)
            self._consolidating.add(session.key)
            try:
                async with lock:
                    snapshot = session.messages[session.last_consolidated:]
                    if snapshot:
                        temp = Session(key=session.key)
                        temp.messages = list(snapshot)
                        if not await self._consolidate_memory(temp, archive_all=True):
                            return OutboundMessage(
                                channel=msg.channel, chat_id=msg.chat_id,
                                content="Memory archival failed, session not cleared. Please try again.",
                            )
            except Exception:
                logger.exception("/new archival failed for {}", session.key)
                return OutboundMessage(
                    channel=msg.channel, chat_id=msg.chat_id,
                    content="Memory archival failed, session not cleared. Please try again.",
                )
            finally:
                self._consolidating.discard(session.key)
                self._prune_consolidation_lock(session.key, lock)

            session.clear()
            self.sessions.save(session)
            self.sessions.invalidate(session.key)
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="New session started.")
        if cmd == "/help":
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="🐈 AiMate commands:\n/new — Start a new conversation\n/help — Show available commands")

        unconsolidated = len(session.messages) - session.last_consolidated
        if (unconsolidated >= self.memory_window and session.key not in self._consolidating):
            self._consolidating.add(session.key)
            lock = self._get_consolidation_lock(session.key)

            async def _consolidate_and_unlock():
                try:
                    async with lock:
                        await self._consolidate_memory(session)
                finally:
                    self._consolidating.discard(session.key)
                    self._prune_consolidation_lock(session.key, lock)
                    _task = asyncio.current_task()
                    if _task is not None:
                        self._consolidation_tasks.discard(_task)

            _task = asyncio.create_task(_consolidate_and_unlock())
            self._consolidation_tasks.add(_task)

        self._set_tool_context(msg.channel, msg.chat_id, msg.metadata.get("message_id"))
        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool):
                message_tool.start_turn()

        history = session.get_history(max_messages=self.memory_window)
        initial_messages = self.context.build_messages(
            history=history,
            current_message=msg.content,
            media=msg.media if msg.media else None,
            channel=msg.channel, chat_id=msg.chat_id,
        )

        async def _bus_progress(content: str, *, tool_hint: bool = False) -> None:
            meta = dict(msg.metadata or {})
            meta["_progress"] = True
            meta["_tool_hint"] = tool_hint
            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel, chat_id=msg.chat_id, content=content, metadata=meta,
            ))

        final_content, _, all_msgs = await self._run_agent_loop(
            initial_messages, on_progress=on_progress or _bus_progress,
        )

        if final_content is None:
            final_content = "I've completed processing but have no response to give."

        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content
        logger.info("Response to {}:{}: {}", msg.channel, msg.sender_id, preview)

        self._save_turn(session, all_msgs, 1 + len(history))
        self.sessions.save(session)
        
        self.context.cleanup_tool_cache()

        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool) and message_tool._sent_in_turn:
                return None

        return OutboundMessage(
            channel=msg.channel, chat_id=msg.chat_id, content=final_content,
            metadata=msg.metadata or {},
        )

    _TOOL_RESULT_MAX_CHARS = 2000

    def _save_turn(self, session: Session, messages: list[dict], skip: int) -> None:
        """Save new-turn messages into session, truncating large tool results."""
        from datetime import datetime
        for m in messages[skip:]:
            entry = {k: v for k, v in m.items() if k != "reasoning_content"}
            if entry.get("role") == "tool" and isinstance(entry.get("content"), str):
                content = entry["content"]
                if content.startswith("FILE_RETURNED:"):
                    pass
                elif len(content) > self._TOOL_RESULT_MAX_CHARS:
                    entry["content"] = content[:self._TOOL_RESULT_MAX_CHARS] + "\n... (truncated)"
            entry.setdefault("timestamp", datetime.now().isoformat())
            session.messages.append(entry)
        session.updated_at = datetime.now()

    async def _consolidate_memory(self, session, archive_all: bool = False) -> bool:
        """Delegate to MemoryStore.consolidate(). Returns True on success."""
        return await MemoryStore(self.workspace).consolidate(
            session, self.provider, self.model,
            archive_all=archive_all, memory_window=self.memory_window,
        )

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """Process a message directly (for CLI or cron usage)."""
        await self._connect_mcp()
        msg = InboundMessage(channel=channel, sender_id="user", chat_id=chat_id, content=content)
        response = await self._process_message(msg, session_key=session_key, on_progress=on_progress)
        return response.content if response else ""

    async def process_stream(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
        on_chunk: Callable[[Any], Awaitable[None]] | None = None,
        media: list[str] | None = None,
    ) -> str:
        """Process a message with streaming response.
        
        This method streams LLM output in real-time for WebSocket chat.
        Supports cancellation via asyncio.CancelledError.
        
        Args:
            content: The user message content.
            session_key: Session identifier.
            channel: Channel name (web, telegram, etc.).
            chat_id: Chat/user ID.
            on_chunk: Callback for streaming chunks.
            media: Optional list of media file paths (images, etc.).
        """
        from nanobot.providers.base import StreamChunk
        
        await self._connect_mcp()
        
        preview = content[:80] + "..." if len(content) > 80 else content
        logger.info("Processing stream message from {}:{}: {}", channel, chat_id, preview)
        
        session = self.sessions.get_or_create(session_key)
        
        cmd = content.strip().lower()
        if cmd == "/new":
            session.clear()
            self.sessions.save(session)
            self.sessions.invalidate(session.key)
            if on_chunk:
                await on_chunk(StreamChunk(type="done", content="New session started."))
            return "New session started."
        if cmd == "/help":
            if on_chunk:
                await on_chunk(StreamChunk(type="done", content="🐈 AiMate commands:\n/new — Start a new conversation\n/help — Show available commands"))
            return "🐈 AiMate commands:\n/new — Start a new conversation\n/help — Show available commands"
        
        self._set_tool_context(channel, chat_id)
        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool):
                message_tool.start_turn()
        
        history = session.get_history(max_messages=self.memory_window)
        initial_messages = self.context.build_messages(
            history=history,
            current_message=content,
            channel=channel,
            chat_id=chat_id,
            media=media,
        )
        
        final_content = None
        tools_used: list[str] = []
        messages = initial_messages
        iteration = 0
        accumulated_content = ""
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        used_model = self.model
        
        try:
            while iteration < self.max_iterations:
                iteration += 1
                
                if on_chunk:
                    await on_chunk(StreamChunk(type="status", content="thinking"))
                
                tool_calls: list = []
                iteration_content = ""
                
                try:
                    async for chunk in self.provider.chat_stream(
                        messages=messages,
                        tools=self.tools.get_definitions(),
                        model=self.model,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    ):
                        if chunk.type == "text_delta":
                            iteration_content += chunk.content or ""
                            accumulated_content += chunk.content or ""
                            if on_chunk:
                                await on_chunk(chunk)
                        
                        elif chunk.type == "reasoning_delta":
                            if on_chunk:
                                await on_chunk(chunk)
                        
                        elif chunk.type == "tool_call":
                            tool_calls.append(chunk.tool_call)
                        
                        elif chunk.type == "error":
                            if on_chunk:
                                await on_chunk(chunk)
                                await on_chunk(StreamChunk(type="done", content=accumulated_content or ""))
                            return accumulated_content or ""
                        
                        elif chunk.type == "done":
                            if chunk.usage:
                                total_prompt_tokens += chunk.usage.get("prompt_tokens", 0)
                                total_completion_tokens += chunk.usage.get("completion_tokens", 0)
                                total_tokens += chunk.usage.get("total_tokens", 0)
                            if chunk.metadata and chunk.metadata.get("model"):
                                used_model = chunk.metadata["model"]
                
                except asyncio.CancelledError:
                    logger.info("[Stream] Cancelled by user")
                    raise
                
                if tool_calls:
                    for tc in tool_calls:
                        hint = self._tool_hint([tc])
                        if on_chunk:
                            await on_chunk(StreamChunk(
                                type="tool_start",
                                content=hint,
                                metadata={"tool_name": tc.name, "tool_args": tc.arguments}
                            ))
                    
                    tool_call_dicts = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments, ensure_ascii=False)
                            }
                        }
                        for tc in tool_calls
                    ]
                    messages = self.context.add_assistant_message(
                        messages, iteration_content, tool_call_dicts,
                    )
                    
                    for tool_call in tool_calls:
                        tools_used.append(tool_call.name)
                        
                        try:
                            result = await self.tools.execute(tool_call.name, tool_call.arguments)
                        except asyncio.CancelledError:
                            logger.info("[Stream] Cancelled during tool execution")
                            raise
                        except Exception as e:
                            logger.exception("Tool execution error: {}", tool_call.name)
                            result = f"Error: {str(e)}"
                        
                        if on_chunk:
                            result_preview = self._format_tool_result(tool_call.name, result)
                            await on_chunk(StreamChunk(
                                type="tool_result",
                                content=result_preview,
                                metadata={"tool_name": tool_call.name}
                            ))
                        
                        messages = self.context.add_tool_result(
                            messages, tool_call.id, tool_call.name, result
                        )
                    
                    accumulated_content = ""
                else:
                    final_content = self._strip_think(iteration_content) or iteration_content
                    messages = self.context.add_assistant_message(messages, final_content)
                    break
            
            if final_content is None and iteration >= self.max_iterations:
                final_content = (
                    f"I reached the maximum number of tool call iterations ({self.max_iterations}) "
                    "without completing the task."
                )
                if on_chunk:
                    await on_chunk(StreamChunk(type="text_delta", content=final_content))
            
            self._save_turn(session, messages, 1 + len(history))
            logger.info(f"[Stream] Token stats: prompt={total_prompt_tokens}, completion={total_completion_tokens}, total={total_tokens}, model={used_model}")
            if total_tokens > 0:
                session.total_prompt_tokens += total_prompt_tokens
                session.total_completion_tokens += total_completion_tokens
                session.total_tokens += total_tokens
                session.request_count += 1
                session.used_model = used_model
            else:
                session.request_count += 1
                if used_model:
                    session.used_model = used_model
            self.sessions.save(session)
            
            if on_chunk:
                await on_chunk(StreamChunk(type="done", content=final_content or ""))
            
            return final_content or ""
        
        except asyncio.CancelledError:
            if accumulated_content:
                self._save_turn(session, messages, 1 + len(history))
                self.sessions.save(session)
            raise
