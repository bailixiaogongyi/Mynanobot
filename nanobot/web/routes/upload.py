"""File upload API routes."""

import uuid
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from loguru import logger


router = APIRouter()


class UploadResponse(BaseModel):
    """Response for file upload."""
    file_id: str
    filename: str
    original_name: str
    file_type: str
    mime_type: str
    size: int
    path: str


class FileInfo(BaseModel):
    """Information about an uploaded file."""
    file_id: str
    filename: str
    original_name: str
    file_type: str
    mime_type: str
    size: int
    created_at: str
    path: str


def _get_allowed_types(request: Request) -> set[str]:
    """Get allowed file types from config."""
    config = request.app.state.config
    image_types = set(config.upload.allowed_image_types)
    doc_types = set(config.upload.allowed_doc_types)
    return image_types | doc_types


def _get_max_file_size(request: Request) -> int:
    """Get max file size from config."""
    config = request.app.state.config
    return config.upload.max_file_size


def _get_upload_dir(request: Request) -> Path:
    """Get upload directory path."""
    import tempfile
    
    config = request.app.state.config
    workspace = Path(config.agents.defaults.workspace).expanduser()
    upload_dir = workspace / "uploads"
    
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        temp_dir = Path(tempfile.gettempdir()) / "nanobot_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        logger.warning(f"No permission to create {upload_dir}, using temp dir: {temp_dir}")
        upload_dir = temp_dir
    
    return upload_dir


def _get_file_type(ext: str) -> str:
    """Determine file type from extension."""
    ext = ext.lower()
    image_types = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    if ext in image_types:
        return "image"
    return "document"


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    request: Request = None,
) -> UploadResponse:
    """Upload a file.
    
    Supports:
    - Images: jpg, jpeg, png, gif, webp, bmp
    - Documents: pdf, doc, docx, txt, md, csv, xlsx, xls
    
    Files are stored in workspace/uploads/
    """
    allowed_types = _get_allowed_types(request)
    max_size = _get_max_file_size(request)
    
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}。支持的类型: {', '.join(sorted(allowed_types))}"
        )
    
    content = await file.read()
    if len(content) > max_size:
        max_mb = max_size // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"文件过大，最大支持 {max_mb}MB"
        )
    
    file_id = str(uuid.uuid4())[:12]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in (file.filename or "file"))
    new_filename = f"{timestamp}_{file_id}_{safe_name}"
    
    upload_dir = _get_upload_dir(request)
    file_path = upload_dir / new_filename
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    mime_type, _ = mimetypes.guess_type(file.filename or "")
    if not mime_type:
        mime_type = "application/octet-stream"
    
    logger.info(f"Uploaded file: {new_filename} ({len(content)} bytes)")
    
    return UploadResponse(
        file_id=file_id,
        filename=new_filename,
        original_name=file.filename or "file",
        file_type=_get_file_type(ext),
        mime_type=mime_type,
        size=len(content),
        path=str(file_path),
    )


@router.post("/upload/batch", response_model=list[UploadResponse])
async def upload_files(
    files: list[UploadFile] = File(...),
    request: Request = None,
) -> list[UploadResponse]:
    """Upload multiple files."""
    results = []
    for file in files:
        result = await upload_file(file, request)
        results.append(result)
    return results


@router.get("/files", response_model=list[FileInfo])
async def list_files(
    request: Request,
    file_type: str | None = None,
    limit: int = 50,
) -> list[FileInfo]:
    """List uploaded files.
    
    Args:
        file_type: Filter by type ("image" or "document")
        limit: Maximum number of files to return
    """
    upload_dir = _get_upload_dir(request)
    files = []
    
    if not upload_dir.exists():
        return files
    
    for path in sorted(upload_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not path.is_file():
            continue
        
        ext = path.suffix.lower()
        ft = _get_file_type(ext)
        
        if file_type and ft != file_type:
            continue
        
        mime_type, _ = mimetypes.guess_type(path.name)
        
        file_id = path.stem.split("_")[-1] if "_" in path.stem else path.stem
        original_name = path.name.split("_", 2)[-1] if path.name.count("_") >= 2 else path.name
        
        files.append(FileInfo(
            file_id=file_id,
            filename=path.name,
            original_name=original_name,
            file_type=ft,
            mime_type=mime_type or "application/octet-stream",
            size=path.stat().st_size,
            created_at=datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            path=str(path),
        ))
        
        if len(files) >= limit:
            break
    
    return files


@router.get("/files/{filename}")
async def download_file(
    filename: str,
    request: Request,
) -> FileResponse:
    """Download or preview a file."""
    upload_dir = _get_upload_dir(request)
    file_path = upload_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        file_path.resolve().relative_to(upload_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="非法路径")
    
    return FileResponse(
        path=file_path,
        filename=filename,
    )


@router.delete("/files/{filename}")
async def delete_file(
    filename: str,
    request: Request,
) -> dict[str, Any]:
    """Delete an uploaded file."""
    upload_dir = _get_upload_dir(request)
    file_path = upload_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        file_path.resolve().relative_to(upload_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="非法路径")
    
    file_path.unlink()
    logger.info(f"Deleted file: {filename}")
    
    return {"status": "deleted", "filename": filename}
