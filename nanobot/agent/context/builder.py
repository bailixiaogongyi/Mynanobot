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
from nanobot.agent.context.tool_cache import ToolResultCache


class ContextBuilder:
    """
    Builds the context (system prompt + messages) for the agent.
    
    Assembles bootstrap files, memory, skills, and conversation history
    into a coherent prompt for the LLM.
    """
    
    BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
    TOOL_CACHE_THRESHOLD = 800
    TOOL_CACHE_TTL = 3600
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory = MemoryStore(workspace)
        self.skills = SkillsLoader(workspace)
        
        cache_dir = workspace / ".cache" / "tool_results"
        self.tool_cache = ToolResultCache(
            cache_dir=cache_dir,
            ttl=self.TOOL_CACHE_TTL,
            threshold=self.TOOL_CACHE_THRESHOLD,
        )
    
    def build_system_prompt(self, skill_names: list[str] | None = None) -> str:
        parts = []
        
        parts.append(self._get_identity())
        
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
        workspace_path = str(self.workspace.expanduser().resolve())
        system = platform.system()
        runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, Python {platform.python_version()}"
        
        return f"""# AiMate 🐈

You are AiMate, a helpful AI assistant.

## 核心规则：日期与时间基准（最高优先级）
- 每次用户消息开头会提供【当前系统时间】，格式如：`当前时间：2026年04月03日 14:30 星期五`
- **所有关于"今天"、"昨天"、"星期几"、"现在几点"的回答，必须且只能以此时间为准。**
- 禁止从 MEMORY.md、HISTORY.md、任何笔记文件或历史对话中推断当前日期。
- 若这些文件中的日期与此时间冲突，忽略文件中的日期。

## Runtime
{runtime}

## Workspace
Your workspace is at: {workspace_path}
- Long-term memory: {workspace_path}/memory/MEMORY.md
- History log: {workspace_path}/memory/HISTORY.md (grep-searchable)
- Custom skills: {workspace_path}/skills/{{skill-name}}/SKILL.md
- Daily notes: {workspace_path}/memory/YYYY-MM-DD.md (例如 2026-04-03.md，仅用于记录，不用于查询当前日期)

Reply directly with text for conversations. Only use the 'message' tool to send to a specific chat channel.

## Tool Call Guidelines
- Before calling tools, you may briefly state your intent (e.g. "Let me check that"), but NEVER predict or describe the expected result before receiving it.
- Before modifying a file, read it first to confirm its current content.
- Do not assume a file or directory exists — use list_dir or read_file to verify.
- After writing or editing a file, re-read it if accuracy matters.
- If a tool call fails, analyze the error before retrying with a different approach.

## Memory & Information Storage Rules

### 信息存储规则 (必须遵循)
- **长期偏好/关键事实** → MEMORY.md (如用户偏好、重要约定、待办事项)
- **每日工作记录** → memory/YYYY-MM-DD.md (按实际日期命名，仅存储历史内容)
- **项目信息** → projects/{{项目名}}.md
- **临时想法** → pending/{{主题}}.md
- **主题内容** → topics/{{主题}}.md
- **个人信息** → personal/{{主题}}.md

### 搜索优先级规则 (必须遵循)
- **查询待办/偏好** → 首先读取 MEMORY.md
- **查询项目/笔记内容** → 使用 note_search 工具 (混合检索)
- **查询历史事件** → 使用 grep 搜索 HISTORY.md
- **只有需要完整文件内容时** → 使用 read_file 工具

Remember important facts: write to {workspace_path}/memory/MEMORY.md
Recall past events: grep {workspace_path}/memory/HISTORY.md"""

    @staticmethod
    def _inject_runtime_context(
        user_content: str | list[dict[str, Any]],
        channel: str | None,
        chat_id: str | None,
    ) -> str | list[dict[str, Any]]:
        now = datetime.now()
        week_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        week_day = week_map[now.weekday()]
        time_str = now.strftime("%Y年%m月%d日 %H:%M")
        tz = now.astimezone().tzname() or "UTC"

        time_reminder = f"⏰ 当前系统时间：{time_str} {week_day}（时区：{tz}）—— 所有日期以此为准。"

        runtime_info = f"\n[会话信息] 渠道：{channel or '默认'} | 会话ID：{chat_id or '无'}"

        if isinstance(user_content, str):
            return f"{time_reminder}\n{user_content}{runtime_info}"
        elif isinstance(user_content, list):
            return [{"type": "text", "text": time_reminder}, *user_content, {"type": "text", "text": runtime_info}]
        
        return user_content
    
    def _load_bootstrap_files(self) -> str:
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
        convert_to_base64: bool = True,
    ) -> list[dict[str, Any]]:
        messages = []

        system_prompt = self.build_system_prompt(skill_names)
        messages.append({"role": "system", "content": system_prompt})

        # 修复孤立的 tool 消息
        fixed_history = []
        for i, msg in enumerate(history):
            if msg.get("role") == "tool" and (i == 0 or history[i-1].get("role") != "assistant"):
                continue
            fixed_history.append(msg)
        messages.extend(fixed_history)

        user_content = self._build_user_content(current_message, media, convert_to_base64)
        runtime_context = self._inject_runtime_context(user_content, channel, chat_id)
        messages.append({"role": "user", "content": runtime_context})

        return messages

    def _build_user_content(self, text: str, media: list[str] | None, convert_to_base64: bool = True) -> str | list[dict[str, Any]]:
        """Build user message content with optional base64-encoded images and file hints.
        
        Args:
            text: The user message text.
            media: List of media file paths.
            convert_to_base64: If True, convert images to base64 for VLM models.
                              If False, only send text hints (for non-VLM main agent).
        """
        if not media:
            return text
        
        images = []
        other_files = []
        
        for path in media:
            p = Path(path).expanduser().resolve()
            if not p.is_file():
                continue
            # 安全检查：仅允许工作区内文件
            try:
                p.relative_to(self.workspace.resolve())
            except ValueError:
                continue
            mime, _ = mimetypes.guess_type(path)
            
            if mime and mime.startswith("image/"):
                if convert_to_base64:
                    b64 = base64.b64encode(p.read_bytes()).decode()
                    images.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
                else:
                    other_files.append((p.name, str(p), "image"))
            else:
                other_files.append((p.name, str(p), "file"))
        
        if images:
            content_parts = images + [{"type": "text", "text": text}]
            if other_files:
                file_hints = "\n\n[已上传文件，请使用相应工具读取：\n"
                for name, fpath, ftype in other_files:
                    if ftype == "image":
                        file_hints += f"- {name} (路径: {fpath}) → 使用 ocr_recognize 工具识别文字，或使用 understand_image 工具理解图片内容\n"
                    else:
                        ext = Path(name).suffix.lower()
                        if ext == ".doc":
                            file_hints += f"- {name} (路径: {fpath}) → 使用 doc_read 工具读取\n"
                        elif ext == ".docx":
                            file_hints += f"- {name} (路径: {fpath}) → 使用 docx_read_text 或 docx_read_structure 工具读取\n"
                        elif ext in (".xls", ".xlsx"):
                            file_hints += f"- {name} (路径: {fpath}) → 使用 excel_read 工具读取\n"
                        elif ext == ".pdf":
                            file_hints += f"- {name} (路径: {fpath}) → 使用 pdf_read_text 工具读取\n"
                        elif ext == ".pptx":
                            file_hints += f"- {name} (路径: {fpath}) → 使用 pptx_read 工具读取\n"
                        else:
                            file_hints += f"- {name} (路径: {fpath})\n"
                file_hints += "]"
                content_parts[-1]["text"] += file_hints
            return content_parts
        
        if other_files:
            file_hints = "\n\n[已上传文件，请使用相应工具读取：\n"
            for name, fpath, ftype in other_files:
                if ftype == "image":
                    file_hints += f"- {name} (路径: {fpath}) → 使用 ocr_recognize 工具识别文字，或使用 understand_image 工具理解图片内容\n"
                else:
                    ext = Path(name).suffix.lower()
                    if ext == ".doc":
                        file_hints += f"- {name} (路径: {fpath}) → 使用 doc_read 工具读取\n"
                    elif ext == ".docx":
                        file_hints += f"- {name} (路径: {fpath}) → 使用 docx_read_text 或 docx_read_structure 工具读取\n"
                    elif ext in (".xls", ".xlsx"):
                        file_hints += f"- {name} (路径: {fpath}) → 使用 excel_read 工具读取\n"
                    elif ext == ".pdf":
                        file_hints += f"- {name} (路径: {fpath}) → 使用 pdf_read_text 工具读取\n"
                    elif ext == ".pptx":
                        file_hints += f"- {name} (路径: {fpath}) → 使用 pptx_read 工具读取\n"
                    else:
                        file_hints += f"- {name} (路径: {fpath})\n"
            file_hints += "]"
            return text + file_hints
        
        return text
    
    def add_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str
    ) -> list[dict[str, Any]]:
        if self.tool_cache.should_cache(result):
            cache_key = self.tool_cache.store(tool_call_id, tool_name, result)
            summary = self.tool_cache.extract_summary(result)
            content = f"{summary}\n\n[完整结果已缓存: {cache_key}]"
        else:
            content = result
        
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": content
        })
        return messages
    
    def get_cached_tool_result(self, cache_key: str) -> str | None:
        """Retrieve a cached tool result by key.
        
        Args:
            cache_key: The cache key from a previous tool result.
            
        Returns:
            The cached result, or None if not found.
        """
        return self.tool_cache.get(cache_key)
    
    def cleanup_tool_cache(self) -> int:
        """Clean up expired tool result cache entries.
        
        Returns:
            Number of entries removed.
        """
        return self.tool_cache.cleanup_expired()
    
    def add_assistant_message(
        self,
        messages: list[dict[str, Any]],
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None,
        reasoning_content: str | None = None,
    ) -> list[dict[str, Any]]:
        msg: dict[str, Any] = {"role": "assistant"}

        msg["content"] = content

        if tool_calls:
            msg["tool_calls"] = tool_calls

        if reasoning_content is not None:
            msg["reasoning_content"] = reasoning_content

        messages.append(msg)
        return messages
