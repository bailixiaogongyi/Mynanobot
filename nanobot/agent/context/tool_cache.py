"""Tool result cache for isolating large tool outputs."""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


class ToolResultCache:
    """Cache for storing large tool results.
    
    When tool results exceed a threshold, they are stored in a cache file
    and only a summary/reference is kept in the conversation context.
    This reduces token usage while preserving access to full data.
    
    Attributes:
        cache_dir: Directory for storing cached results.
        ttl: Time-to-live in seconds for cache entries.
        threshold: Minimum size (chars) to trigger caching.
        max_summary_length: Maximum length of summary in context.
    """
    
    DEFAULT_TTL = 3600
    DEFAULT_THRESHOLD = 800
    DEFAULT_MAX_SUMMARY = 200
    
    def __init__(
        self,
        cache_dir: Path,
        ttl: int = DEFAULT_TTL,
        threshold: int = DEFAULT_THRESHOLD,
        max_summary_length: int = DEFAULT_MAX_SUMMARY,
    ):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.threshold = threshold
        self.max_summary_length = max_summary_length
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self) -> None:
        """Create cache directory if not exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_key(self, tool_call_id: str, tool_name: str, result: str) -> str:
        """Generate a unique cache key."""
        content_hash = hashlib.md5(result.encode()).hexdigest()[:8]
        return f"{tool_name}_{tool_call_id}_{content_hash}"
    
    def should_cache(self, result: str) -> bool:
        """Check if result should be cached based on size."""
        return len(result) > self.threshold
    
    def store(self, tool_call_id: str, tool_name: str, result: str) -> str:
        """Store tool result in cache.
        
        Args:
            tool_call_id: Unique ID for the tool call.
            tool_name: Name of the tool.
            result: The tool result string.
            
        Returns:
            Cache key for retrieval.
        """
        cache_key = self._generate_key(tool_call_id, tool_name, result)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        cache_data = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "result": result,
            "timestamp": time.time(),
            "size": len(result),
        }
        
        cache_file.write_text(json.dumps(cache_data, ensure_ascii=False), encoding="utf-8")
        
        return cache_key
    
    def get(self, cache_key: str) -> str | None:
        """Retrieve cached tool result.
        
        Args:
            cache_key: The cache key returned by store().
            
        Returns:
            The cached result string, or None if not found/expired.
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
            
            if self.ttl > 0:
                age = time.time() - cache_data.get("timestamp", 0)
                if age > self.ttl:
                    cache_file.unlink(missing_ok=True)
                    return None
            
            return cache_data.get("result")
        except (json.JSONDecodeError, KeyError):
            return None
    
    def get_metadata(self, cache_key: str) -> dict[str, Any] | None:
        """Get metadata for cached result without full content.
        
        Args:
            cache_key: The cache key.
            
        Returns:
            Dict with metadata, or None if not found.
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
            return {
                "tool_call_id": cache_data.get("tool_call_id"),
                "tool_name": cache_data.get("tool_name"),
                "timestamp": cache_data.get("timestamp"),
                "size": cache_data.get("size"),
            }
        except (json.JSONDecodeError, KeyError):
            return None
    
    def extract_summary(self, result: str) -> str:
        """Extract a summary from a large result.
        
        Args:
            result: The full result string.
            
        Returns:
            A summary string.
        """
        if len(result) <= self.max_summary_length:
            return result
        
        result_stripped = result.strip()
        
        if result_stripped.startswith("{") or result_stripped.startswith("["):
            summary = self._extract_json_summary(result_stripped)
            if summary:
                return summary
        
        lines = result.split("\n")
        if len(lines) > 10:
            first_lines = "\n".join(lines[:5])
            last_lines = "\n".join(lines[-2:])
            return f"{first_lines}\n... ({len(lines) - 7} lines omitted) ...\n{last_lines}"
        
        return result[:self.max_summary_length] + "..."
    
    def _extract_json_summary(self, result: str) -> str | None:
        """Extract summary from JSON result."""
        try:
            data = json.loads(result)
            
            if isinstance(data, dict):
                keys = list(data.keys())[:10]
                key_str = ", ".join(keys)
                if len(data) > 10:
                    key_str += f", ... ({len(data) - 10} more keys)"
                
                size_info = f"keys: {len(data)}"
                if "data" in data and isinstance(data["data"], list):
                    size_info += f", items: {len(data['data'])}"
                
                return f"{{ {key_str} }} ({size_info})"
            
            elif isinstance(data, list):
                count = len(data)
                if count > 0:
                    first_type = type(data[0]).__name__
                    return f"[{count} items of type {first_type}]"
                return "[empty list]"
            
        except json.JSONDecodeError:
            pass
        
        return None
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries.
        
        Returns:
            Number of entries removed.
        """
        if self.ttl <= 0:
            return 0
        
        removed = 0
        current_time = time.time()
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
                age = current_time - cache_data.get("timestamp", 0)
                if age > self.ttl:
                    cache_file.unlink()
                    removed += 1
            except (json.JSONDecodeError, KeyError):
                cache_file.unlink(missing_ok=True)
                removed += 1
        
        return removed
    
    def clear(self) -> int:
        """Clear all cache entries.
        
        Returns:
            Number of entries removed.
        """
        removed = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink(missing_ok=True)
            removed += 1
        return removed
    
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_size = 0
        entry_count = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            entry_count += 1
            total_size += cache_file.stat().st_size
        
        return {
            "entry_count": entry_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir),
            "ttl_seconds": self.ttl,
            "threshold_chars": self.threshold,
        }
