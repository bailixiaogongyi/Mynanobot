"""Tool for retrieving cached tool results."""

from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


class GetCachedResultTool(Tool):
    """Tool to retrieve cached tool results.
    
    When large tool results are cached, this tool allows the LLM
    to retrieve the full result when needed.
    """
    
    def __init__(self, context_builder, allowed_dir: Path | None = None):
        self.context_builder = context_builder
    
    @property
    def name(self) -> str:
        return "get_cached_result"
    
    @property
    def description(self) -> str:
        return """Retrieve a cached tool result by its cache key.
        
Use this when you need the full content of a previously cached tool result.
Cached results are indicated by '[完整结果已缓存: cache_key]' in tool outputs.
"""
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "cache_key": {
                    "type": "string",
                    "description": "The cache key from a cached tool result (e.g., 'toolname_callid_hash')."
                }
            },
            "required": ["cache_key"]
        }
    
    def execute(self, cache_key: str) -> str:
        result = self.context_builder.get_cached_tool_result(cache_key)
        
        if result is None:
            return f"Error: Cache key '{cache_key}' not found or expired. Cached results expire after 1 hour."
        
        return result
