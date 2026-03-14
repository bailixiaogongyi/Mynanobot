"""File return tool for generating downloadable files."""

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


class ReturnFileTool(Tool):
    """Tool to return a generated file to the user for download."""

    def __init__(self, upload_dir: Path):
        self._upload_dir = upload_dir
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "return_file"
    
    @property
    def description(self) -> str:
        return (
            "Return a generated file to the user for download. "
            "Use this tool when you need to provide a file for the user to download. "
            "The file will be accessible via a download link in the chat."
        )
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_path": {
                    "type": "string",
                    "description": "The path to the file you want to return to the user"
                },
                "display_name": {
                    "type": "string", 
                    "description": "Optional: The name to display to the user (default: original filename)"
                }
            },
            "required": ["source_path"]
        }
    
    async def execute(self, source_path: str, display_name: str | None = None, **kwargs: Any) -> str:
        try:
            source = Path(source_path).expanduser().resolve()
            
            if not source.exists():
                return f"Error: File not found: {source_path}"
            
            if not source.is_file():
                return f"Error: Not a file: {source_path}"
            
            file_id = str(uuid.uuid4())[:12]
            original_name = source.name
            display = display_name or original_name
            ext = source.suffix.lower()
            timestamp = int(source.stat().st_mtime)
            
            safe_display = "".join(c if c.isalnum() or c in "._-" else "_" for c in display)
            dest_name = f"{timestamp}_{file_id}_{safe_display}"
            dest_path = self._upload_dir / dest_name
            
            shutil.copy2(source, dest_path)
            
            file_info = {
                "file_id": file_id,
                "filename": dest_name,
                "original_name": display,
                "file_type": self._get_file_type(ext),
            }
            return f"FILE_RETURNED:{json.dumps(file_info, ensure_ascii=False)}"
        except PermissionError as e:
            return f"Error: Permission denied: {e}"
        except Exception as e:
            return f"Error returning file: {str(e)}"
    
    def _get_file_type(self, ext: str) -> str:
        """Determine file type from extension."""
        image_types = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
        if ext in image_types:
            return "image"
        return "document"
