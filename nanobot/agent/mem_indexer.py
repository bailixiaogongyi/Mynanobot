import asyncio
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from loguru import logger


class IndexState:
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self._state: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load index state: {e}")

    def _save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False)

    def get_file_hash(self, file_path: str) -> str:
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash {file_path}: {e}")
            return ""

    def needs_reindex(self, file_path: str) -> bool:
        if file_path not in self._state:
            return True
        current_hash = self.get_file_hash(file_path)
        return current_hash != self._state[file_path].get("hash")

    def update_state(self, file_path: str, chunk_count: int) -> None:
        self._state[file_path] = {
            "hash": self.get_file_hash(file_path),
            "chunk_count": chunk_count,
            "indexed_at": 0
        }
        self._save()

    def get_all_files(self) -> list[str]:
        return list(self._state.keys())

    def remove_file(self, file_path: str) -> None:
        if file_path in self._state:
            del self._state[file_path]
            self._save()


class BackgroundIndexer:
    def __init__(self, retriever, index_state: IndexState):
        self.retriever = retriever
        self.index_state = index_state
        self._running = False
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Background indexer started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background indexer stopped")

    async def add_file(self, file_path: str) -> None:
        await self._queue.put(file_path)

    async def add_files_batch(self, file_paths: list[str]) -> None:
        for fp in file_paths:
            await self._queue.put(fp)

    async def _run(self) -> None:
        while self._running:
            try:
                file_path = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )

                if self.index_state.needs_reindex(file_path):
                    await self._index_file(file_path)
                else:
                    logger.debug(f"Skipping unchanged file: {file_path}")

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background index error: {e}")

    async def _index_file(self, file_path: str) -> None:
        try:
            from nanobot.knowledge.note_processor import NoteProcessor

            processor = NoteProcessor()
            chunks = processor.process_file(Path(file_path))

            if chunks:
                self.retriever.index_documents(chunks)
                self.index_state.update_state(file_path, len(chunks))
                logger.info(f"Indexed {file_path}: {len(chunks)} chunks")
            else:
                logger.debug(f"No chunks extracted from {file_path}")

        except Exception as e:
            logger.error(f"Failed to index {file_path}: {e}")

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "pending": self._queue.qsize(),
        }
