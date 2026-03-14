"""Session management for conversation history."""

import json
import os
import tempfile
import time
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger

from nanobot.utils.helpers import ensure_dir, get_data_path, safe_filename

MAX_CACHE_SIZE = 500
DEFAULT_CACHE_TTL_HOURS = 24


@dataclass
class Session:
    """
    A conversation session.

    Stores messages in JSONL format for easy reading and persistence.

    Important: Messages are append-only for LLM cache efficiency.
    The consolidation process writes summaries to MEMORY.md/HISTORY.md
    but does NOT modify the messages list or get_history() output.
    """

    key: str  # channel:chat_id
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    last_consolidated: int = 0  # Number of messages already consolidated to files
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0
    used_model: str = ""
    
    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """Add a message to the session."""
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        self.messages.append(msg)
        self.updated_at = datetime.now()
    
    def get_history(self, max_messages: int = 500) -> list[dict[str, Any]]:
        """Return unconsolidated messages for LLM input, aligned to a user turn."""
        unconsolidated = self.messages[self.last_consolidated:]
        sliced = unconsolidated[-max_messages:]

        # Drop leading non-user messages to avoid orphaned tool_result blocks
        for i, m in enumerate(sliced):
            if m.get("role") == "user":
                sliced = sliced[i:]
                break

        out: list[dict[str, Any]] = []
        for m in sliced:
            entry: dict[str, Any] = {"role": m["role"], "content": m.get("content", "")}
            for k in ("tool_calls", "tool_call_id", "name", "timestamp"):
                if k in m:
                    entry[k] = m[k]
            out.append(entry)
        return out
    
    def get_full_history(self, max_messages: int = 500) -> list[dict[str, Any]]:
        """Return messages with all fields including timestamp for display.
        
        Args:
            max_messages: Maximum number of messages to return.
        
        Returns:
            List of messages with all fields.
        """
        unconsolidated = self.messages[self.last_consolidated:]
        sliced = unconsolidated[-max_messages:]

        # Drop leading non-user messages
        for i, m in enumerate(sliced):
            if m.get("role") == "user":
                sliced = sliced[i:]
                break

        # Return all fields for display (including reasoning_content, tool_calls, etc.)
        return [dict(m) for m in sliced]
    
    def clear(self) -> None:
        """Clear all messages and reset session to initial state."""
        self.messages = []
        self.last_consolidated = 0
        self.updated_at = datetime.now()


class SessionManager:
    """
    Manages conversation sessions.

    Sessions are stored as JSONL files in the sessions directory.
    """

    def __init__(self, workspace: Path, max_cache_size: int = MAX_CACHE_SIZE, 
                 cache_ttl_hours: int = DEFAULT_CACHE_TTL_HOURS):
        self.workspace = workspace
        self.sessions_dir = ensure_dir(get_data_path() / "sessions")
        self._cache: dict[str, Session] = {}
        self._cache_order: list[str] = []
        self._cache_timestamps: dict[str, float] = {}
        self._max_cache_size = max_cache_size
        self._cache_ttl_seconds = cache_ttl_hours * 3600
    
    def _evict_if_needed(self) -> None:
        now = time.time()
        while len(self._cache) > self._max_cache_size and self._cache_order:
            oldest_key = self._cache_order.pop(0)
            self._cache_timestamps.pop(oldest_key, None)
            self._cache.pop(oldest_key, None)
    
    def _evict_expired(self) -> None:
        """Remove expired sessions from cache."""
        if self._cache_ttl_seconds <= 0:
            return
        now = time.time()
        expired_keys = [
            key for key, ts in self._cache_timestamps.items()
            if now - ts > self._cache_ttl_seconds
        ]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
            if key in self._cache_order:
                self._cache_order.remove(key)
    
    def _get_session_path(self, key: str) -> Path:
        """Get the file path for a session."""
        safe_key = safe_filename(key.replace(":", "_"))
        return self.sessions_dir / f"{safe_key}.jsonl"
    
    def get(self, key: str) -> Session | None:
        """
        Get an existing session without creating a new one.

        Args:
            key: Session key (usually channel:chat_id).

        Returns:
            The session if it exists, None otherwise.
        """
        self._evict_expired()
        if key in self._cache:
            self._cache_timestamps[key] = time.time()
            return self._cache[key]
        return self._load(key)

    def get_or_create(self, key: str) -> Session:
        """
        Get an existing session or create a new one.
        
        Args:
            key: Session key (usually channel:chat_id).
        
        Returns:
            The session.
        """
        self._evict_expired()
        
        if key in self._cache:
            if key in self._cache_order:
                self._cache_order.remove(key)
            self._cache_order.append(key)
            self._cache_timestamps[key] = time.time()
            return self._cache[key]
        
        session = self._load(key)
        if session is None:
            session = Session(key=key)
        
        self._cache[key] = session
        self._cache_order.append(key)
        self._cache_timestamps[key] = time.time()
        self._evict_if_needed()
        return session
    
    def _load(self, key: str) -> Session | None:
        """Load a session from disk."""
        path = self._get_session_path(key)
        if not path.exists():
            return None

        try:
            messages = []
            metadata = {}
            created_at = None
            last_consolidated = 0
            total_prompt_tokens = 0
            total_completion_tokens = 0
            total_tokens = 0
            request_count = 0
            used_model = ""

            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    data = json.loads(line)

                    if data.get("_type") == "metadata":
                        metadata = data.get("metadata", {})
                        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
                        last_consolidated = data.get("last_consolidated", 0)
                        total_prompt_tokens = data.get("total_prompt_tokens", 0)
                        total_completion_tokens = data.get("total_completion_tokens", 0)
                        total_tokens = data.get("total_tokens", 0)
                        request_count = data.get("request_count", 0)
                        used_model = data.get("used_model", "")
                    else:
                        messages.append(data)

            return Session(
                key=key,
                messages=messages,
                created_at=created_at or datetime.now(),
                metadata=metadata,
                last_consolidated=last_consolidated,
                total_prompt_tokens=total_prompt_tokens,
                total_completion_tokens=total_completion_tokens,
                total_tokens=total_tokens,
                request_count=request_count,
                used_model=used_model,
            )
        except Exception as e:
            logger.warning("Failed to load session {}: {}", key, e)
            return None
    
    def save(self, session: Session) -> None:
        """Save a session to disk atomically.
        
        Uses a temporary file and atomic rename to prevent data corruption
        if the process crashes during write.
        """
        path = self._get_session_path(session.key)
        
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp"
        )
        
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                metadata_line = {
                    "_type": "metadata",
                    "key": session.key,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "metadata": session.metadata,
                    "last_consolidated": session.last_consolidated,
                    "total_prompt_tokens": session.total_prompt_tokens,
                    "total_completion_tokens": session.total_completion_tokens,
                    "total_tokens": session.total_tokens,
                    "request_count": session.request_count,
                    "used_model": session.used_model,
                }
                f.write(json.dumps(metadata_line, ensure_ascii=False) + "\n")
                for msg in session.messages:
                    f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            
            os.replace(tmp_path, path)
            
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
        
        self._cache[session.key] = session
    
    def invalidate(self, key: str) -> None:
        """Remove a session from the in-memory cache."""
        self._cache.pop(key, None)

    def delete(self, key: str) -> bool:
        """
        Delete a session from disk and cache.

        Args:
            key: Session key to delete.

        Returns:
            True if session was deleted, False if not found.
        """
        self._cache.pop(key, None)
        path = self._get_session_path(key)
        if path.exists():
            try:
                path.unlink()
                return True
            except Exception as e:
                logger.warning("Failed to delete session {}: {}", key, e)
                return False
        return False

    def list_sessions(self) -> list[dict[str, Any]]:
        """
        List all sessions.
        
        Returns:
            List of session info dicts.
        """
        sessions = []
        
        for path in self.sessions_dir.glob("*.jsonl"):
            try:
                with open(path, encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line:
                        data = json.loads(first_line)
                        if data.get("_type") == "metadata":
                            key = data.get("key") or path.stem.replace("_", ":", 1)
                            sessions.append({
                                "key": key,
                                "created_at": data.get("created_at"),
                                "updated_at": data.get("updated_at"),
                                "path": str(path),
                                "total_prompt_tokens": data.get("total_prompt_tokens", 0),
                                "total_completion_tokens": data.get("total_completion_tokens", 0),
                                "total_tokens": data.get("total_tokens", 0),
                                "request_count": data.get("request_count", 0),
                                "used_model": data.get("used_model", ""),
                            })
            except Exception:
                continue
        
        return sorted(sessions, key=lambda x: x.get("updated_at", ""), reverse=True)

    def add_token_usage(self, key: str, prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0, model: str = "") -> None:
        """Add token usage to a session.

        Args:
            key: Session key.
            prompt_tokens: Number of prompt tokens used.
            completion_tokens: Number of completion tokens used.
            total_tokens: Total tokens used.
            model: Model name used for this request.
        """
        session = self.get_or_create(key)
        session.total_prompt_tokens += prompt_tokens
        session.total_completion_tokens += completion_tokens
        session.total_tokens += total_tokens
        session.request_count += 1
        if model:
            session.used_model = model
        self.save(session)
