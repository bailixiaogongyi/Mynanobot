"""Notes API routes for Web UI.

This module provides note management API endpoints for the Web UI.
Supports file tree browsing, content editing, and semantic search.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

if TYPE_CHECKING:
    from nanobot.knowledge.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)

router = APIRouter()

NOTE_DIRS = ["daily", "projects", "personal", "topics", "pending", "memory"]


class NoteInfo(BaseModel):
    """Note file information."""

    path: str
    name: str
    type: str
    size: int
    modified_at: str
    is_dir: bool = False


class NoteContent(BaseModel):
    """Note content for save operation."""

    path: str
    content: str


class SearchResult(BaseModel):
    """Search result item."""

    id: str
    content: str
    score: float
    source: str
    metadata: dict[str, Any] = {}


class SearchResponse(BaseModel):
    """Search response."""

    query: str
    results: list[SearchResult]
    total: int


class DirectoryListing(BaseModel):
    """Directory listing response."""

    path: str
    directories: list[NoteInfo]
    files: list[NoteInfo]


class IndexResponse(BaseModel):
    """Index operation response."""

    status: str
    indexed: int
    total_files: int
    message: str


def _get_workspace(request) -> Path:
    """Get workspace path from app state."""
    if not hasattr(request.app.state, "config") or request.app.state.config is None:
        logger.error("config not found in app.state")
        raise HTTPException(status_code=500, detail="Server configuration not initialized")
    return request.app.state.config.workspace_path


def _validate_path(workspace: Path, path: str) -> Path:
    """Validate and resolve a path within workspace.

    Prevents path traversal attacks by ensuring the resolved path
    stays within the workspace directory.

    Args:
        workspace: Workspace root path.
        path: Relative path to validate.

    Returns:
        Resolved absolute path.

    Raises:
        HTTPException: If path is invalid or escapes workspace.
    """
    if ".." in path or path.startswith("/") or path.startswith("\\"):
        raise HTTPException(status_code=400, detail="Invalid path: path traversal not allowed")

    workspace_resolved = workspace.resolve()
    resolved = (workspace / path).resolve()

    try:
        resolved.relative_to(workspace_resolved)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path: path escapes workspace")

    return resolved


def _get_retriever(request) -> "HybridRetriever | None":
    """Get hybrid retriever from app state."""
    return getattr(request.app.state, "retriever", None)


@router.get("/list", response_model=DirectoryListing)
async def list_notes(
    request: Request,
    directory: Optional[str] = Query(None, description="Directory to list"),
) -> DirectoryListing:
    """List notes in a directory.

    Args:
        directory: Directory path relative to workspace. If None, lists root directories.

    Returns:
        Directory listing with subdirectories and files.
    """
    workspace = _get_workspace(request)

    if directory:
        target_dir = workspace / directory
        if not target_dir.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {directory}")
        if not target_dir.is_dir():
            raise HTTPException(status_code=400, detail=f"Not a directory: {directory}")
    else:
        target_dir = workspace

    directories = []
    files = []

    try:
        for item in sorted(target_dir.iterdir()):
            if item.name.startswith("."):
                continue

            stat = item.stat()
            info = NoteInfo(
                path=str(item.relative_to(workspace)),
                name=item.name,
                type="directory" if item.is_dir() else "file",
                size=stat.st_size if item.is_file() else 0,
                modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                is_dir=item.is_dir(),
            )

            if item.is_dir():
                directories.append(info)
            elif item.suffix.lower() == ".md":
                files.append(info)

    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    rel_path = str(target_dir.relative_to(workspace)) if target_dir != workspace else ""

    return DirectoryListing(
        path=rel_path,
        directories=directories,
        files=files,
    )


@router.get("/dirs")
async def list_root_dirs(request: Request) -> list[str]:
    """List root note directories.

    Returns:
        List of root directory names.
    """
    workspace = _get_workspace(request)
    existing_dirs = []

    for dir_name in NOTE_DIRS:
        dir_path = workspace / dir_name
        if dir_path.exists() and dir_path.is_dir():
            existing_dirs.append(dir_name)

    return existing_dirs


@router.get("/read")
async def read_note(
    request: Request,
    path: str = Query(..., description="Note file path relative to workspace"),
) -> NoteContent:
    """Read note content.

    Args:
        path: Note file path relative to workspace.

    Returns:
        Note content.
    """
    workspace = _get_workspace(request)
    file_path = _validate_path(workspace, path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    if file_path.suffix.lower() != ".md":
        raise HTTPException(status_code=400, detail="Only markdown files are supported")

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")

    return NoteContent(path=path, content=content)


@router.post("/save")
async def save_note(note: NoteContent, request: Request) -> dict[str, Any]:
    """Save note content.

    Args:
        note: Note content with path and content.

    Returns:
        Save result.
    """
    workspace = _get_workspace(request)
    file_path = _validate_path(workspace, note.path)

    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.exists() and not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {note.path}")

    try:
        file_path.write_text(note.content, encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")

    return {
        "status": "saved",
        "path": note.path,
        "size": len(note.content),
    }


@router.post("/create")
async def create_note(
    request: Request,
    path: str = Query(..., description="Note file path relative to workspace"),
    content: str = Query("", description="Initial content"),
) -> NoteContent:
    """Create a new note file.

    Args:
        path: Note file path relative to workspace.
        content: Initial content.

    Returns:
        Created note information.
    """
    workspace = _get_workspace(request)
    workspace_resolved = workspace.resolve()
    file_path = _validate_path(workspace, path)

    if file_path.exists():
        raise HTTPException(status_code=409, detail=f"File already exists: {path}")

    if file_path.suffix.lower() != ".md":
        file_path = file_path.with_suffix(".md")

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating file: {e}")

    return NoteContent(path=str(file_path.relative_to(workspace_resolved)), content=content)


@router.delete("/delete")
async def delete_note(
    request: Request,
    path: str = Query(..., description="Note file path relative to workspace"),
) -> dict[str, Any]:
    """Delete a note file.

    Args:
        path: Note file path relative to workspace.

    Returns:
        Delete result.
    """
    workspace = _get_workspace(request)
    file_path = _validate_path(workspace, path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    try:
        file_path.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {e}")

    return {"status": "deleted", "path": path}


@router.get("/search", response_model=SearchResponse)
async def search_notes(
    request: Request,
    q: str = Query(..., description="Search query"),
    top_k: int = Query(5, description="Number of results to return"),
    search_type: str = Query("auto", description="Search type: keyword, semantic, auto"),
) -> SearchResponse:
    """Search notes using hybrid retrieval.

    Uses the HybridRetriever for semantic + keyword search.

    Args:
        q: Search query.
        top_k: Number of results to return.
        search_type: Search type (keyword, semantic, auto).

    Returns:
        Search results.
    """
    retriever = _get_retriever(request)

    if not retriever:
        raise HTTPException(
            status_code=503,
            detail="Knowledge retrieval not available. Please enable knowledge.index.enabled in config."
        )

    try:
        results = retriever.search(q, top_k=top_k, search_type=search_type)

        search_results = [
            SearchResult(
                id=r.get("id", ""),
                content=r.get("content", ""),
                score=r.get("score", 0.0),
                source=r.get("metadata", {}).get("source", ""),
                metadata=r.get("metadata", {}),
            )
            for r in results
        ]

        return SearchResponse(
            query=q,
            results=search_results,
            total=len(search_results),
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search error: {e}")


@router.post("/index", response_model=IndexResponse)
async def index_notes(
    request: Request,
    directory: str = Query(..., description="Directory to index relative to workspace"),
    force: bool = Query(False, description="Force reindex all files"),
) -> IndexResponse:
    """Index notes in a directory.

    Args:
        directory: Directory to index. If "notes" or not found, indexes all configured note directories.
        force: Force reindex all files.

    Returns:
        Index result.
    """
    from nanobot.knowledge.hybrid_retriever import HybridRetriever
    from nanobot.knowledge.note_processor import NoteProcessor
    from nanobot.knowledge.incremental_indexer import IncrementalIndexer

    workspace = _get_workspace(request)
    config = request.app.state.config

    knowledge_config = getattr(config.tools, 'knowledge', None)
    index_config = getattr(knowledge_config, 'index', None) if knowledge_config else None

    if not index_config:
        raise HTTPException(
            status_code=400,
            detail="Knowledge index is not configured. Please enable tools.knowledge.index in config."
        )

    if not getattr(index_config, 'enabled', False):
        raise HTTPException(
            status_code=400,
            detail="Knowledge index is disabled. Please set tools.knowledge.index.enabled = true in config."
        )

    target_dirs = []
    if directory == "notes" or not (workspace / directory).exists():
        notes_dirs = getattr(knowledge_config, 'notes_dirs', NOTE_DIRS) if knowledge_config else NOTE_DIRS
        for dir_name in notes_dirs:
            dir_path = workspace / dir_name
            if dir_path.exists() and dir_path.is_dir():
                target_dirs.append(dir_path)
        if not target_dirs:
            raise HTTPException(status_code=404, detail="No note directories found in workspace")
    else:
        target_dir = workspace / directory
        if not target_dir.is_dir():
            raise HTTPException(status_code=400, detail=f"Not a directory: {directory}")
        target_dirs = [target_dir]

    persist_dir = Path(index_config.persist_dir).expanduser()
    persist_dir.mkdir(parents=True, exist_ok=True)

    try:
        retriever = getattr(request.app.state, 'retriever', None)
        if retriever is None:
            retriever = HybridRetriever(
                persist_dir=persist_dir,
                model_name=index_config.embedding_model,
                use_bm25=index_config.use_bm25,
                use_vector=index_config.use_vector,
                use_graph=getattr(index_config, 'use_graph', False),
                use_ollama=getattr(index_config, 'use_ollama', False),
                ollama_base_url=getattr(index_config, 'ollama_base_url', 'http://localhost:11434'),
            )

        processor = NoteProcessor(
            chunk_size=index_config.chunk_size,
            overlap=index_config.chunk_overlap,
        )

        indexer = IncrementalIndexer(persist_dir)

        all_chunks = []
        total_files = 0

        for target_dir in target_dirs:
            md_files = list(target_dir.rglob("*.md"))
            for md_file in md_files:
                if force or indexer.needs_reindex(md_file):
                    chunks = processor.process_markdown(md_file)
                    all_chunks.extend(chunks)
                    indexer.mark_indexed(md_file)
                    total_files += 1

        if all_chunks:
            result = retriever.index_documents(all_chunks)
            indexed = result.get("indexed", 0)
        else:
            indexed = 0

        return IndexResponse(
            status="success",
            indexed=indexed,
            total_files=total_files,
            message=f"Indexed {indexed} chunks from {total_files} files",
        )

    except Exception as e:
        import traceback
        logger.error(f"Index error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Index failed: {type(e).__name__}: {str(e)}")


@router.get("/index/status")
async def index_status(request: Request) -> dict[str, Any]:
    """Get indexing status.

    Returns:
        Indexing status information.
    """
    from nanobot.knowledge.incremental_indexer import IncrementalIndexer

    workspace = _get_workspace(request)
    config = request.app.state.config

    persist_dir = Path(config.tools.knowledge.index.persist_dir).expanduser()
    indexer = IncrementalIndexer(persist_dir)

    indexed_files = indexer.get_indexed_files()

    total_md_files = 0
    for note_dir in NOTE_DIRS:
        dir_path = workspace / note_dir
        if dir_path.exists():
            total_md_files += len(list(dir_path.rglob("*.md")))

    return {
        "indexed_files": len(indexed_files),
        "total_files": total_md_files,
        "persist_dir": str(persist_dir),
        "enabled": config.tools.knowledge.index.enabled,
    }
