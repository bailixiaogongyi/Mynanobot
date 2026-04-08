"""Utility functions for nanobot."""

from pathlib import Path
from datetime import datetime


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_data_path() -> Path:
    """Get the nanobot data directory (~/.nanobot)."""
    return ensure_dir(Path.home() / ".nanobot")


def get_workspace_path(workspace: str | None = None) -> Path:
    """
    Get the workspace path.
    
    Args:
        workspace: Optional workspace path. Defaults to ~/.nanobot/workspace.
    
    Returns:
        Expanded and ensured workspace path.
    """
    if workspace:
        path = Path(workspace).expanduser()
    else:
        path = Path.home() / ".nanobot" / "workspace"
    return ensure_dir(path)


def get_sessions_path() -> Path:
    """Get the sessions storage directory."""
    return ensure_dir(get_data_path() / "sessions")


def get_skills_path(workspace: Path | None = None) -> Path:
    """Get the skills directory within the workspace."""
    ws = workspace or get_workspace_path()
    return ensure_dir(ws / "skills")


def init_workspace_directories(workspace: Path | None = None) -> dict[str, Path]:
    """
    Initialize all required workspace directories for note management.
    
    Creates the following directories:
    - memory: Daily notes and memory files
    - daily: Archived daily notes (organized by year/month)
    - projects: Project notes
    - personal: Personal information
    - topics: Topic notes
    - pending: Temporary/pending notes
    - skills: Custom skills
    
    Args:
        workspace: Optional workspace path. Defaults to ~/.nanobot/workspace.
    
    Returns:
        Dict mapping directory names to their paths.
    """
    ws = workspace or get_workspace_path()
    
    directories = {
        "memory": ws / "memory",
        "daily": ws / "daily",
        "projects": ws / "projects",
        "personal": ws / "personal",
        "topics": ws / "topics",
        "pending": ws / "pending",
        "skills": ws / "skills",
    }
    
    for name, path in directories.items():
        ensure_dir(path)
    
    return directories


def timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()


def truncate_string(s: str, max_len: int = 100, suffix: str = "...") -> str:
    """Truncate a string to max length, adding suffix if truncated."""
    if len(s) <= max_len:
        return s
    return s[: max_len - len(suffix)] + suffix


def safe_filename(name: str) -> str:
    """Convert a string to a safe filename."""
    # Replace unsafe characters
    unsafe = '<>:"/\\|?*'
    for char in unsafe:
        name = name.replace(char, "_")
    return name.strip()


def parse_session_key(key: str) -> tuple[str, str]:
    """
    Parse a session key into channel and chat_id.
    
    Args:
        key: Session key in format "channel:chat_id"
    
    Returns:
        Tuple of (channel, chat_id)
    """
    parts = key.split(":", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid session key: {key}")
    return parts[0], parts[1]


def split_message(content: str, max_len: int = 2000) -> list[str]:
    """
    Split content into chunks within max_len, preferring line breaks.
    
    Args:
        content: The text content to split.
        max_len: Maximum length per chunk (default 2000 for Discord compatibility).
    
    Returns:
        List of message chunks, each within max_len.
    """
    if not content:
        return []
    if len(content) <= max_len:
        return [content]
    
    chunks: list[str] = []
    while content:
        if len(content) <= max_len:
            chunks.append(content)
            break
        
        cut = content[:max_len]
        last_newline = cut.rfind('\n')
        last_space = cut.rfind(' ')
        
        if last_newline > max_len // 2:
            split_pos = last_newline + 1
        elif last_space > max_len // 2:
            split_pos = last_space + 1
        else:
            split_pos = max_len
        
        chunk = content[:split_pos].strip()
        if chunk:
            chunks.append(chunk)
        content = content[split_pos:].strip()
    
    return chunks
