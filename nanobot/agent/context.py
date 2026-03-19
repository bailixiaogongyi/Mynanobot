"""Context builder for assembling agent prompts."""

import base64
import mimetypes
import platform
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from nanobot.agent.memory import MemoryStore
from nanobot.agent.skills import SkillsLoader


class ContextBuilder:
    """
    Builds the context (system prompt + messages) for the agent.
    
    Assembles bootstrap files, memory, skills, and conversation history
    into a coherent prompt for the LLM.
    """
    
    BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory = MemoryStore(workspace)
        self.skills = SkillsLoader(workspace)
    
    def build_system_prompt(self, skill_names: list[str] | None = None) -> str:
        """
        Build the system prompt from bootstrap files, memory, and skills.
        
        Args:
            skill_names: Optional list of skills to include.
        
        Returns:
            Complete system prompt.
        """
        parts = []
        
        # Core identity
        parts.append(self._get_identity())
        
        # Bootstrap files
        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)
        
        # Skills Summary first - define available capabilities (per Claude Code best practices)
        skills_summary = self.skills.build_skills_summary()
        if skills_summary:
            parts.append(f"""# Skills

The following skills extend your capabilities. To use a skill, read its SKILL.md file using the read_file tool.
Skills with available="false" need dependencies installed first - you can try installing them with apt/brew.

{skills_summary}""")
        
        # Always Skills - load detailed skill content (for skills marked as always=true)
        always_skills = self.skills.get_always_skills()
        if always_skills:
            always_content = self.skills.load_skills_for_context(always_skills)
            if always_content:
                parts.append(f"# Active Skills\n\n{always_content}")
        
        # Memory Context last - user preferences and context (most dynamic)
        memory = self.memory.get_memory_context()
        if memory:
            parts.append(f"# Memory\n\n{memory}")
        
        return "\n\n---\n\n".join(parts)
    
    def _get_identity(self) -> str:
        """Get the core identity section."""
        workspace_path = str(self.workspace.expanduser().resolve())
        system = platform.system()
        runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, Python {platform.python_version()}"
        
        return f"""# AiMate 🐈

You are AiMate, a helpful AI assistant. 

## Runtime
{runtime}

## Workspace
Your workspace is at: {workspace_path}
- Long-term memory: {workspace_path}/memory/MEMORY.md
- History log: {workspace_path}/memory/HISTORY.md (grep-searchable)
- Custom skills: {workspace_path}/skills/{{skill-name}}/SKILL.md

Reply directly with text for conversations. Only use the 'message' tool to send to a specific chat channel.

## Tool Call Guidelines
- Before calling tools, you may briefly state your intent (e.g. "Let me check that"), but NEVER predict or describe the expected result before receiving it.
- Before modifying a file, read it first to confirm its current content.
- Do not assume a file or directory exists — use list_dir or read_file to verify.
- After writing or editing a file, re-read it if accuracy matters.
- If a tool call fails, analyze the error before retrying with a different approach.

## Memory
- Remember important facts: write to {workspace_path}/memory/MEMORY.md
- Recall past events: grep {workspace_path}/memory/HISTORY.md"""

    @staticmethod
    def _inject_runtime_context(
        user_content: str | list[dict[str, Any]],
        channel: str | None,
        chat_id: str | None,
    ) -> str | list[dict[str, Any]]:
        """Append dynamic runtime context to the tail of the user message."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        tz = time.strftime("%Z") or "UTC"
        lines = [f"Current Time: {now} ({tz})"]
        if channel and chat_id:
            lines += [f"Channel: {channel}", f"Chat ID: {chat_id}"]
        block = "[Runtime Context]\n" + "\n".join(lines)
        if isinstance(user_content, str):
            return f"{user_content}\n\n{block}"
        return [*user_content, {"type": "text", "text": block}]
    
    def _load_bootstrap_files(self) -> str:
        """Load all bootstrap files from workspace."""
        parts = []
        
        for filename in self.BOOTSTRAP_FILES:
            file_path = self.workspace / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n\n{content}")
        
        return "\n\n".join(parts) if parts else ""
    
    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        skill_names: list[str] | None = None,
        media: list[str] | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Build the complete message list for an LLM call.

        Args:
            history: Previous conversation messages.
            current_message: The new user message.
            skill_names: Optional skills to include.
            media: Optional list of local file paths for images/media.
            channel: Current channel (telegram, feishu, etc.).
            chat_id: Current chat/user ID.

        Returns:
            List of messages including system prompt.
        """
        messages = []

        # System prompt
        system_prompt = self.build_system_prompt(skill_names)
        messages.append({"role": "system", "content": system_prompt})

        # History
        messages.extend(history)

        # Current message (with optional image attachments)
        user_content = self._build_user_content(current_message, media)
        # Note: Runtime Context is intentionally NOT injected into user message
        # to maintain System Prompt cache stability (per Claude Code best practices)
        # The time/channel info can be accessed via tool calls if needed
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_user_content(self, text: str, media: list[str] | None) -> str | list[dict[str, Any]]:
        """Build user message content. 
        
        Note: Images are NOT sent directly to the main agent to avoid issues with
        non-vision models. Instead, we provide hints about available image processing
        options (OCR tools or spawn a vision-capable subagent).
        """
        if not media:
            return text
        
        images = []
        other_files = []
        
        for path in media:
            p = Path(path).expanduser().resolve()
            mime, _ = mimetypes.guess_type(path)
            
            if not p.is_file():
                logger.warning(f"Media file not found: {path}")
                continue
            
            if mime and mime.startswith("image/"):
                images.append((p.name, str(p), mime))
            else:
                other_files.append((p.name, str(p), p.suffix.lower()))
        
        has_images = bool(images)
        
        if has_images:
            image_info = "\n".join([f"- `{name}` (路径: `{path}`)" for name, path, _ in images])
            
            content_text = text + f"""

## 📷 用户上传了图片

图片列表：
{image_info}

### 处理方式选择：

**方式一：OCR 文字识别（本地处理）**
如果只需要识别图片中的文字，使用 `ocr_recognize` 工具：
- 工具名: `ocr_recognize`
- 参数: `path` (图片的完整路径，使用上面列表中的路径), `detail` (可选，是否返回详细信息)

**方式二：调用图片识别子 Agent（推荐用于图片理解）**
如果需要理解图片内容、场景、物体等，使用 `spawn` 工具创建一个专门处理图片的子 Agent：
- 使用 vision-agent 角色（配置了支持视觉的模型）
- 将图片路径传递给子 Agent
- 子 Agent 会将图片转换为 base64 并分析

### 执行建议：
1. 如果用户要求"识别文字"、"OCR"，使用 `ocr_recognize`
2. 如果用户要求"分析图片"、"描述图片"、"看图"，使用 `spawn` 调用 `vision-agent` 子 Agent
3. 如果用户要求"生成图片"、"画图"、"创建图片"，使用 `spawn` 调用 `image-generator` 子 Agent
4. 优先使用子 Agent 方式，因为子 Agent 配置了专门的模型
"""
        
        else:
            content_text = text
        
        if other_files:
            file_hints = """

## 已上传文件处理指南

用户上传了以下非图片文件，请根据文件类型选择合适的工具处理：

"""
            for name, fpath, ext in other_files:
                file_type_guide = self._get_file_type_guide(ext)
                file_hints += f"- **文件**: `{name}`\n  - 路径: `{fpath}`\n  - 类型: {file_type_guide}\n"
            
            file_hints += """

### 处理流程建议：
1. 使用 `file_processing_guide` 工具获取文件处理指导
2. 根据指导选择合适的工具（如 pdf_read_text, excel_read, docx_read_text 等）
3. 处理完成后，向用户总结结果
4. 如需返回处理后的文件，使用 `return_file` 工具
"""
            content_text += file_hints
        
        return content_text
    
    def _get_file_type_guide(self, ext: str) -> str:
        """Get file type processing guide based on extension."""
        guides = {
            ".pdf": "PDF文档 - 可用工具: pdf_read_text, pdf_extract_tables, pdf_extract_images, ocr_pdf",
            ".docx": "Word文档 - 可用工具: docx_read_text, docx_read_tables, docx_read_structure",
            ".xlsx": "Excel表格 - 可用工具: excel_read, excel_write, excel_list_sheets",
            ".pptx": "PPT演示文稿 - 可用工具: pptx_read",
            ".txt": "文本文件 - 可用工具: read_file",
            ".md": "Markdown文件 - 可用工具: read_file",
            ".csv": "CSV数据文件 - 可用工具: excel_read",
            ".jpg": "JPEG图片 - 可用工具: ocr_recognize (文字识别), image_understand (图片理解)",
            ".jpeg": "JPEG图片 - 可用工具: ocr_recognize (文字识别), image_understand (图片理解)",
            ".png": "PNG图片 - 可用工具: ocr_recognize (文字识别), image_understand (图片理解)",
            ".gif": "GIF图片 - 可用工具: ocr_recognize (文字识别), image_understand (图片理解)",
            ".bmp": "BMP图片 - 可用工具: ocr_recognize (文字识别), image_understand (图片理解)",
            ".webp": "WebP图片 - 可用工具: ocr_recognize (文字识别), image_understand (图片理解)",
        }
        return guides.get(ext, "未知类型文件 - 建议先尝试 read_file 读取内容")
    
    def add_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str
    ) -> list[dict[str, Any]]:
        """
        Add a tool result to the message list.
        
        Args:
            messages: Current message list.
            tool_call_id: ID of the tool call.
            tool_name: Name of the tool.
            result: Tool execution result.
        
        Returns:
            Updated message list.
        """
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result
        })
        return messages
    
    def add_assistant_message(
        self,
        messages: list[dict[str, Any]],
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None,
        reasoning_content: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Add an assistant message to the message list.
        
        Args:
            messages: Current message list.
            content: Message content.
            tool_calls: Optional tool calls.
            reasoning_content: Thinking output (Kimi, DeepSeek-R1, etc.).
        
        Returns:
            Updated message list.
        """
        msg: dict[str, Any] = {"role": "assistant"}

        # Always include content — some providers (e.g. StepFun) reject
        # assistant messages that omit the key entirely.
        msg["content"] = content

        if tool_calls:
            msg["tool_calls"] = tool_calls

        # Include reasoning content when provided (required by some thinking models)
        if reasoning_content is not None:
            msg["reasoning_content"] = reasoning_content

        messages.append(msg)
        return messages
