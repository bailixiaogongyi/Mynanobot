import asyncio
import json
from pathlib import Path
from typing import Any
from datetime import datetime
from loguru import logger


class SharedContext:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self._contexts: dict[str, dict[str, Any]] = {}
        self._results: dict[str, Any] = {}
        self._events: list[dict] = []
        self._lock = asyncio.Lock()

    async def create_workspace(self, workspace_id: str) -> None:
        async with self._lock:
            self._contexts[workspace_id] = {
                "created_at": datetime.now().isoformat(),
                "agents": set(),
                "data": {},
                "status": "active"
            }

    async def join_workspace(self, workspace_id: str, agent_id: str) -> bool:
        async with self._lock:
            if workspace_id not in self._contexts:
                return False
            if "agents" not in self._contexts[workspace_id]:
                self._contexts[workspace_id]["agents"] = set()
            self._contexts[workspace_id]["agents"].add(agent_id)
            return True

    async def leave_workspace(self, workspace_id: str, agent_id: str) -> bool:
        async with self._lock:
            if workspace_id not in self._contexts:
                return False
            if agent_id in self._contexts[workspace_id].get("agents", set()):
                self._contexts[workspace_id]["agents"].discard(agent_id)
            return True

    async def put(self, workspace_id: str, key: str, value: Any) -> None:
        async with self._lock:
            if workspace_id not in self._contexts:
                await self.create_workspace(workspace_id)
            self._contexts[workspace_id]["data"][key] = value

            self._events.append({
                "type": "put",
                "workspace": workspace_id,
                "key": key,
                "timestamp": datetime.now().isoformat()
            })

    async def get(self, workspace_id: str, key: str) -> Any | None:
        async with self._lock:
            return self._contexts.get(workspace_id, {}).get("data", {}).get(key)

    async def get_all(self, workspace_id: str) -> dict:
        async with self._lock:
            return self._contexts.get(workspace_id, {}).get("data", {}).copy()

    async def put_result(self, task_id: str, result: Any) -> None:
        async with self._lock:
            self._results[task_id] = {
                "result": result,
                "timestamp": datetime.now().isoformat()
            }

    async def get_result(self, task_id: str) -> Any | None:
        async with self._lock:
            return self._results.get(task_id, {}).get("result")

    async def delete_result(self, task_id: str) -> None:
        async with self._lock:
            if task_id in self._results:
                del self._results[task_id]

    def get_events(
        self,
        workspace_id: str | None = None,
        limit: int = 100
    ) -> list[dict]:
        events = self._events
        if workspace_id:
            events = [e for e in events if e.get("workspace") == workspace_id]
        return events[-limit:]

    async def get_workspace_info(self, workspace_id: str) -> dict | None:
        async with self._lock:
            ctx = self._contexts.get(workspace_id)
            if not ctx:
                return None
            return {
                "id": workspace_id,
                "created_at": ctx.get("created_at"),
                "status": ctx.get("status"),
                "agents": list(ctx.get("agents", set())),
                "data_keys": list(ctx.get("data", {}).keys())
            }

    async def list_workspaces(self) -> list[str]:
        async with self._lock:
            return list(self._contexts.keys())

    async def close_workspace(self, workspace_id: str) -> None:
        async with self._lock:
            if workspace_id in self._contexts:
                del self._contexts[workspace_id]
