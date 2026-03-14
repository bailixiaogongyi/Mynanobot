"""Incremental indexer for tracking file changes."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class IncrementalIndexer:
    """Manager for incremental indexing based on file hashes.

    This class tracks file content hashes to enable:
    - Detection of new/modified files
    - Detection of deleted files
    - Efficient re-indexing

    Attributes:
        persist_dir: Directory for storing hash data.
    """

    HASH_FILE = "file_hashes.json"

    def __init__(self, persist_dir: Path):
        self.persist_dir = Path(persist_dir)
        self.hash_file = self.persist_dir / self.HASH_FILE
        self.hashes: dict[str, str] = self._load_hashes()

    def _load_hashes(self) -> dict[str, str]:
        """Load stored file hashes from disk."""
        if self.hash_file.exists():
            try:
                content = self.hash_file.read_text(encoding="utf-8")
                return json.loads(content)
            except Exception as e:
                logger.warning(f"Failed to load file hashes: {e}")
        return {}

    def _save_hashes(self) -> None:
        """Save current file hashes to disk."""
        try:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self.hash_file.write_text(
                json.dumps(self.hashes, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save file hashes: {e}")

    def get_changed_files(
        self,
        files: list[Path]
    ) -> tuple[list[Path], list[Path]]:
        """Detect changed and deleted files.

        Args:
            files: Current list of files to check.

        Returns:
            Tuple of (changed_files, deleted_files).
        """
        changed: list[Path] = []
        current_files = {str(f) for f in files}

        for file_path in files:
            file_str = str(file_path)

            try:
                content = file_path.read_bytes()
                file_hash = hashlib.md5(content).hexdigest()
            except Exception as e:
                logger.warning(f"Failed to read file {file_path}: {e}")
                continue

            stored_hash = self.hashes.get(file_str)

            if stored_hash != file_hash:
                changed.append(file_path)
                self.hashes[file_str] = file_hash

        deleted: list[Path] = []
        for file_str in list(self.hashes.keys()):
            if file_str not in current_files:
                deleted.append(Path(file_str))
                del self.hashes[file_str]

        self._save_hashes()

        if changed:
            logger.info(f"Detected {len(changed)} changed files")
        if deleted:
            logger.info(f"Detected {len(deleted)} deleted files")

        return changed, deleted

    def get_file_hash(self, file_path: Path) -> str | None:
        """Get stored hash for a file.

        Args:
            file_path: Path to check.

        Returns:
            Stored hash or None if not tracked.
        """
        return self.hashes.get(str(file_path))

    def update_hash(self, file_path: Path, content_hash: str | None = None) -> None:
        """Update hash for a file.

        Args:
            file_path: Path to update.
            content_hash: Optional pre-computed hash. If None, reads file.
        """
        if content_hash is None:
            try:
                content = file_path.read_bytes()
                content_hash = hashlib.md5(content).hexdigest()
            except Exception as e:
                logger.warning(f"Failed to read file {file_path}: {e}")
                return

        self.hashes[str(file_path)] = content_hash
        self._save_hashes()

    def remove_hash(self, file_path: Path) -> None:
        """Remove hash for a file.

        Args:
            file_path: Path to remove.
        """
        file_str = str(file_path)
        if file_str in self.hashes:
            del self.hashes[file_str]
            self._save_hashes()

    def clear(self) -> None:
        """Clear all stored hashes."""
        self.hashes = {}
        if self.hash_file.exists():
            try:
                self.hash_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove hash file: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about tracked files.

        Returns:
            Dict with count and file info.
        """
        return {
            "tracked_files": len(self.hashes),
            "hash_file": str(self.hash_file),
            "exists": self.hash_file.exists()
        }

    def needs_reindex(self, file_path: Path) -> bool:
        """Check if a file needs re-indexing.

        Args:
            file_path: File path to check.

        Returns:
            True if the file needs re-indexing.
        """
        file_str = str(file_path)
        stored_hash = self.hashes.get(file_str)

        if stored_hash is None:
            return True

        try:
            content = file_path.read_bytes()
            current_hash = hashlib.md5(content).hexdigest()
            return current_hash != stored_hash
        except Exception:
            return True

    def mark_indexed(self, file_path: Path) -> None:
        """Mark a file as indexed.

        Args:
            file_path: Path to mark as indexed.
        """
        try:
            content = file_path.read_bytes()
            content_hash = hashlib.md5(content).hexdigest()
            self.hashes[str(file_path)] = content_hash
            self._save_hashes()
        except Exception as e:
            logger.warning(f"Failed to mark file as indexed: {e}")

    def get_indexed_files(self) -> list[str]:
        """Get list of indexed file paths.

        Returns:
            List of indexed file path strings.
        """
        return list(self.hashes.keys())
