"""OCR operations tools using RapidOCR."""

import json
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


def _resolve_path(path: str, workspace: Path | None = None, allowed_dir: Path | None = None) -> Path:
    """Resolve path against workspace and enforce directory restriction."""
    p = Path(path).expanduser()
    if not p.is_absolute() and workspace:
        p = workspace / p
    resolved = p.resolve()
    if allowed_dir:
        try:
            resolved.relative_to(allowed_dir.resolve())
        except ValueError:
            raise PermissionError(f"Path {path} is outside allowed directory {allowed_dir}")
    return resolved


class OcrImageTool(Tool):
    """Tool to recognize text from images using OCR."""

    def __init__(self, workspace: Path | None = None, allowed_dir: Path | None = None):
        self._workspace = workspace
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "ocr_recognize"

    @property
    def description(self) -> str:
        return "Recognize text from an image file using OCR (Optical Character Recognition). Supports PNG, JPG, JPEG, BMP, GIF formats."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute path to the image file"
                },
                "detail": {
                    "type": "boolean",
                    "description": "Include detailed result with bounding boxes and confidence. Default: false"
                }
            },
            "required": ["path"]
        }

    async def execute(self, path: str, detail: bool = False, **kwargs: Any) -> str:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            return "Error: RapidOCR is required. Install with: pip install rapidocr-onnxruntime"

        try:
            file_path = _resolve_path(path, self._workspace, self._allowed_dir)
            if not file_path.exists():
                return f"Error: File not found: {path}"

            supported_formats = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"]
            if file_path.suffix.lower() not in supported_formats:
                return f"Error: Unsupported image format. Supported: {', '.join(supported_formats)}"

            result, elapse = RapidOCR()(str(file_path))

            if not result:
                return "No text recognized from the image."

            if detail:
                detailed_results = []
                for line in result:
                    bbox, text, confidence = line
                    detailed_results.append({
                        "text": text,
                        "confidence": round(confidence, 2),
                        "bbox": bbox
                    })
                return json.dumps({
                    "text": " ".join([r["text"] for r in detailed_results]),
                    "details": detailed_results,
                    "elapse_ms": round(elapse * 1000, 2)
                }, ensure_ascii=False, indent=2)
            else:
                text_lines = [line[1] for line in result]
                return "\n".join(text_lines)

        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error during OCR: {str(e)}"


class OcrBatchTool(Tool):
    """Tool to perform batch OCR on multiple images."""

    def __init__(self, workspace: Path | None = None, allowed_dir: Path | None = None):
        self._workspace = workspace
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "ocr_batch"

    @property
    def description(self) -> str:
        return "Perform OCR on multiple images in a directory."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": "Directory containing images to process"
                },
                "output_path": {
                    "type": "string",
                    "description": "Output JSON file to save results"
                }
            },
            "required": ["dir_path"]
        }

    async def execute(self, dir_path: str, output_path: str | None = None, **kwargs: Any) -> str:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            return "Error: RapidOCR is required. Install with: pip install rapidocr-onnxruntime"

        try:
            dir_file_path = _resolve_path(dir_path, self._workspace, self._allowed_dir)
            if not dir_file_path.exists() or not dir_file_path.is_dir():
                return f"Error: Directory not found: {dir_path}"

            supported_formats = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"]
            image_files = [
                f for f in dir_file_path.iterdir()
                if f.is_file() and f.suffix.lower() in supported_formats
            ]

            if not image_files:
                return f"No image files found in {dir_path}"

            ocr_engine = RapidOCR()
            results = {}

            for img_file in image_files:
                result, elapse = ocr_engine(str(img_file))
                if result:
                    text = " ".join([line[1] for line in result])
                else:
                    text = ""
                results[img_file.name] = {
                    "text": text,
                    "recognized": bool(result),
                    "elapse_ms": round(elapse * 1000, 2) if elapse else 0
                }

            if output_path:
                out_file_path = _resolve_path(output_path, self._workspace, self._allowed_dir)
                out_file_path.parent.mkdir(parents=True, exist_ok=True)
                out_file_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
                return f"Processed {len(image_files)} images. Results saved to: {out_file_path}"

            return json.dumps(results, ensure_ascii=False, indent=2)

        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error during batch OCR: {str(e)}"


class OcrPdfTool(Tool):
    """Tool to perform OCR on PDF pages (requires converting PDF to images first)."""

    def __init__(self, workspace: Path | None = None, allowed_dir: Path | None = None):
        self._workspace = workspace
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "ocr_pdf"

    @property
    def description(self) -> str:
        return "Perform OCR on PDF document pages. Converts each page to image first, then recognizes text."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute path to the PDF file"
                },
                "pages": {
                    "type": "string",
                    "description": "Page range to process, e.g., '1-5' or '1,3,5'. Default: all pages"
                },
                "output_path": {
                    "type": "string",
                    "description": "Output JSON file to save results"
                }
            },
            "required": ["path"]
        }

    async def execute(self, path: str, pages: str | None = None, output_path: str | None = None, **kwargs: Any) -> str:
        try:
            from rapidocr_onnxruntime import RapidOCR
            import fitz
        except ImportError:
            return "Error: RapidOCR and PyMuPDF are required. Install with: pip install rapidocr-onnxruntime pymupdf"

        try:
            file_path = _resolve_path(path, self._workspace, self._allowed_dir)
            if not file_path.exists():
                return f"Error: File not found: {path}"
            if not file_path.suffix.lower() == ".pdf":
                return f"Error: Not a PDF file: {path}"

            doc = fitz.open(str(file_path))
            total_pages = len(doc)

            page_indices = []
            if pages:
                for part in pages.split(","):
                    part = part.strip()
                    if "-" in part:
                        start, end = part.split("-")
                        page_indices.extend(range(int(start) - 1, int(end)))
                    else:
                        page_indices.append(int(part) - 1)
            else:
                page_indices = list(range(total_pages))

            ocr_engine = RapidOCR()
            results = {}

            for idx in page_indices:
                if 0 <= idx < total_pages:
                    page = doc[idx]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_bytes = pix.tobytes("png")

                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp.write(img_bytes)
                        tmp_path = tmp.name

                    result, elapse = ocr_engine(tmp_path)
                    if result:
                        text = " ".join([line[1] for line in result])
                    else:
                        text = ""

                    results[f"page_{idx + 1}"] = {
                        "text": text,
                        "recognized": bool(result),
                        "elapse_ms": round(elapse * 1000, 2) if elapse else 0
                    }

                    import os
                    os.unlink(tmp_path)

            doc.close()

            if output_path:
                out_file_path = _resolve_path(output_path, self._workspace, self._allowed_dir)
                out_file_path.parent.mkdir(parents=True, exist_ok=True)
                out_file_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
                return f"Processed {len(results)} pages. Results saved to: {out_file_path}"

            return json.dumps(results, ensure_ascii=False, indent=2)

        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error during OCR: {str(e)}"
