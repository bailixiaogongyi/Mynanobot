import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass
class MemoryLayerConfig:
    working_mem_size: int = 100
    session_mem_ttl: int = 3600
    enable_cache: bool = True


class MemoryLayer:
    def __init__(self, workspace, config: MemoryLayerConfig | None = None):
        self.config = config or MemoryLayerConfig()
        self.workspace = workspace
        self._working_cache: OrderedDict[str, Any] = OrderedDict()
        self._session_store: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        if key in self._working_cache:
            self._working_cache.move_to_end(key)
            return self._working_cache[key]

        if key in self._session_store:
            entry = self._session_store[key]
            if self._is_valid(entry):
                value = entry["value"]
                self._add_to_working(key, value)
                return value
            else:
                del self._session_store[key]

        return None

    def set(self, key: str, value: Any, layer: str = "working") -> None:
        if layer == "working":
            self._add_to_working(key, value)
        elif layer == "session":
            self._session_store[key] = {
                "value": value,
                "timestamp": time.time()
            }

    def delete(self, key: str) -> None:
        self._working_cache.pop(key, None)
        self._session_store.pop(key, None)

    def _is_valid(self, entry: dict) -> bool:
        if self.config.session_mem_ttl <= 0:
            return True
        return time.time() - entry.get("timestamp", 0) < self.config.session_mem_ttl

    def _add_to_working(self, key: str, value: Any) -> None:
        if key in self._working_cache:
            if self._working_cache[key] == value:
                self._working_cache.move_to_end(key)
                return
            else:
                del self._working_cache[key]

        if len(self._working_cache) >= self.config.working_mem_size:
            oldest_key, oldest_value = self._working_cache.popitem(last=False)
            self._session_store[oldest_key] = {
                "value": oldest_value,
                "timestamp": time.time()
            }

        self._working_cache[key] = value

    def clear_working(self) -> None:
        self._working_cache.clear()

    def clear_session(self) -> None:
        self._session_store.clear()

    def get_stats(self) -> dict:
        return {
            "working_size": len(self._working_cache),
            "working_capacity": self.config.working_mem_size,
            "session_size": len(self._session_store),
            "session_ttl": self.config.session_mem_ttl,
        }
