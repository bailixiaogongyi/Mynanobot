"""Note processor for parsing and chunking markdown documents."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class NoteProcessor:
    """Processor for parsing and chunking markdown notes.

    This class handles:
    - Markdown file parsing with header-based sectioning
    - Intelligent chunking with sentence boundary detection
    - Directory scanning for batch processing
    - Unique ID generation for chunks

    Attributes:
        chunk_size: Maximum characters per chunk.
        overlap: Character overlap between chunks.
    """

    DEFAULT_CHUNK_SIZE = 512
    DEFAULT_OVERLAP = 50
    DEFAULT_EXTENSIONS = [".md", ".txt", ".markdown"]

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP
    ):
        if chunk_size < 100:
            raise ValueError("chunk_size must be at least 100 characters")
        if overlap < 0:
            raise ValueError("overlap cannot be negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def process_markdown(self, file_path: Path) -> list[dict[str, Any]]:
        """Process a single markdown file into chunks.

        Args:
            file_path: Path to the markdown file.

        Returns:
            List of chunk dicts with keys:
                - id: Unique chunk identifier
                - content: Chunk text content
                - metadata: Dict with source, title, level, type
                - timestamp: File modification time
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return []

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning(f"Failed to decode file: {file_path}")
            return []
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []

        if not content.strip():
            return []

        sections = self._split_by_headers(content)

        chunks = []
        timestamp = file_path.stat().st_mtime
        section_index = 0

        for section in sections:
            section_content = section["content"]

            if len(section_content) <= self.chunk_size:
                chunks.append({
                    "id": self._generate_id(file_path, section_content, section_index),
                    "content": section_content,
                    "metadata": {
                        "source": str(file_path),
                        "title": section.get("title", ""),
                        "level": section.get("level", 0),
                        "type": "note"
                    },
                    "timestamp": timestamp
                })
                section_index += 1
            else:
                sub_chunks = self._split_by_size(section, file_path, timestamp, section_index)
                chunks.extend(sub_chunks)
                section_index += len(sub_chunks)

        logger.debug(f"Processed {file_path}: {len(chunks)} chunks")
        return chunks

    def process_directory(
        self,
        dir_path: Path,
        extensions: list[str] | None = None,
        recursive: bool = True
    ) -> list[dict[str, Any]]:
        """Process all notes in a directory.

        Args:
            dir_path: Path to the directory.
            extensions: File extensions to process (default: .md, .txt, .markdown).
            recursive: Whether to process subdirectories.

        Returns:
            List of all chunks from all processed files.
        """
        dir_path = Path(dir_path)

        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return []

        if extensions is None:
            extensions = self.DEFAULT_EXTENSIONS

        all_chunks = []
        file_count = 0

        for ext in extensions:
            if recursive:
                files = dir_path.rglob(f"*{ext}")
            else:
                files = dir_path.glob(f"*{ext}")

            for file_path in files:
                if file_path.is_file():
                    chunks = self.process_markdown(file_path)
                    all_chunks.extend(chunks)
                    file_count += 1

        logger.info(f"Processed {file_count} files in {dir_path}: {len(all_chunks)} chunks")
        return all_chunks

    def process_files(
        self,
        file_paths: list[Path]
    ) -> list[dict[str, Any]]:
        """Process multiple files.

        Args:
            file_paths: List of file paths to process.

        Returns:
            List of all chunks from all files.
        """
        all_chunks = []

        for file_path in file_paths:
            chunks = self.process_markdown(file_path)
            all_chunks.extend(chunks)

        return all_chunks

    def _split_by_headers(self, content: str) -> list[dict[str, Any]]:
        """Split content by markdown headers.

        Args:
            content: Markdown content.

        Returns:
            List of section dicts with content, title, and level.
        """
        pattern = r'^(#{1,6})\s+(.+)$'
        lines = content.split('\n')

        sections = []
        current = {"content": "", "title": "", "level": 0}

        for line in lines:
            match = re.match(pattern, line)
            if match:
                if current["content"].strip():
                    sections.append(current)
                current = {
                    "content": line + "\n",
                    "title": match.group(2).strip(),
                    "level": len(match.group(1))
                }
            else:
                current["content"] += line + "\n"

        if current["content"].strip():
            sections.append(current)

        return sections

    def _split_by_size(
        self,
        section: dict[str, Any],
        file_path: Path,
        timestamp: float,
        start_index: int = 0
    ) -> list[dict[str, Any]]:
        """Split a large section into smaller chunks.

        Args:
            section: Section dict with content, title, level.
            file_path: Source file path.
            timestamp: File modification time.
            start_index: Starting index for chunk IDs.

        Returns:
            List of chunk dicts.
        """
        content = section["content"]
        chunks = []

        start = 0
        chunk_index = start_index

        while start < len(content):
            end = start + self.chunk_size
            chunk_content = content[start:end]

            if end < len(content):
                last_period = chunk_content.rfind('。')
                last_newline = chunk_content.rfind('\n')
                last_sentence_end = chunk_content.rfind('. ')

                boundary = max(last_period, last_newline, last_sentence_end)

                if boundary > self.chunk_size // 2:
                    end = start + boundary + 1
                    chunk_content = content[start:end]

            chunk_content = chunk_content.strip()
            if chunk_content:
                chunks.append({
                    "id": self._generate_id(file_path, chunk_content, chunk_index),
                    "content": chunk_content,
                    "metadata": {
                        "source": str(file_path),
                        "title": section.get("title", ""),
                        "level": section.get("level", 0),
                        "type": "note_chunk",
                        "chunk_index": chunk_index - start_index
                    },
                    "timestamp": timestamp
                })
                chunk_index += 1

            if end >= len(content):
                break

            start = end - self.overlap if self.overlap > 0 else end

        return chunks

    def _generate_id(
        self,
        file_path: Path,
        content: str,
        index: int | None = None
    ) -> str:
        """Generate a unique ID for a chunk.

        Args:
            file_path: Source file path.
            content: Chunk content.
            index: Optional chunk index.

        Returns:
            Unique identifier string.
        """
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        base_id = f"{file_path.stem}_{content_hash}"

        if index is not None:
            return f"{base_id}_{index}"

        return base_id

    def get_file_hash(self, file_path: Path) -> str:
        """Get MD5 hash of a file's content.

        Args:
            file_path: Path to the file.

        Returns:
            MD5 hash string.
        """
        content = file_path.read_bytes()
        return hashlib.md5(content).hexdigest()
