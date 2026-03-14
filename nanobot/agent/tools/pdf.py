"""PDF document operations tools using PyMuPDF."""

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


class PdfReadTextTool(Tool):
    """Tool to read text content from PDF document."""

    def __init__(self, workspace: Path | None = None, allowed_dir: Path | None = None):
        self._workspace = workspace
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "pdf_read_text"

    @property
    def description(self) -> str:
        return "Read text content from a PDF document. Returns plain text."

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
                    "description": "Page range to extract, e.g., '1-5' or '1,3,5'. Default: all pages"
                }
            },
            "required": ["path"]
        }

    async def execute(self, path: str, pages: str | None = None, **kwargs: Any) -> str:
        try:
            import fitz
        except ImportError:
            return "Error: PyMuPDF is required. Install with: pip install pymupdf"

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

            text_parts = []
            for idx in page_indices:
                if 0 <= idx < total_pages:
                    page = doc[idx]
                    text = page.get_text()
                    if text.strip():
                        text_parts.append(f"[Page {idx + 1}]\n{text}")

            doc.close()

            if not text_parts:
                return "No text content found in the specified pages."

            return "\n\n".join(text_parts)

        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error reading PDF: {str(e)}"


class PdfReadStructureTool(Tool):
    """Tool to read PDF document structure."""

    def __init__(self, workspace: Path | None = None, allowed_dir: Path | None = None):
        self._workspace = workspace
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "pdf_read_structure"

    @property
    def description(self) -> str:
        return "Read the structure of a PDF document, including page count, metadata, and basic info."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute path to the PDF file"
                }
            },
            "required": ["path"]
        }

    async def execute(self, path: str, **kwargs: Any) -> str:
        try:
            import fitz
        except ImportError:
            return "Error: PyMuPDF is required. Install with: pip install pymupdf"

        try:
            file_path = _resolve_path(path, self._workspace, self._allowed_dir)
            if not file_path.exists():
                return f"Error: File not found: {path}"
            if not file_path.suffix.lower() == ".pdf":
                return f"Error: Not a PDF file: {path}"

            doc = fitz.open(str(file_path))

            result = {
                "page_count": len(doc),
                "metadata": {
                    "title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                    "subject": doc.metadata.get("subject", ""),
                    "creator": doc.metadata.get("creator", ""),
                    "producer": doc.metadata.get("producer", ""),
                },
                "pages": []
            }

            for i, page in enumerate(doc):
                result["pages"].append({
                    "page_number": i + 1,
                    "width": round(page.rect.width, 2),
                    "height": round(page.rect.height, 2),
                    "text_length": len(page.get_text())
                })

            doc.close()
            return json.dumps(result, ensure_ascii=False, indent=2)

        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error reading PDF structure: {str(e)}"


class PdfExtractImagesTool(Tool):
    """Tool to extract images from PDF document."""

    def __init__(self, workspace: Path | None = None, allowed_dir: Path | None = None):
        self._workspace = workspace
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "pdf_extract_images"

    @property
    def description(self) -> str:
        return "Extract all images from a PDF document and save to output directory."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute path to the PDF file"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Output directory to save extracted images"
                }
            },
            "required": ["path", "output_dir"]
        }

    async def execute(self, path: str, output_dir: str, **kwargs: Any) -> str:
        try:
            import fitz
        except ImportError:
            return "Error: PyMuPDF is required. Install with: pip install pymupdf"

        try:
            file_path = _resolve_path(path, self._workspace, self._allowed_dir)
            if not file_path.exists():
                return f"Error: File not found: {path}"
            if not file_path.suffix.lower() == ".pdf":
                return f"Error: Not a PDF file: {path}"

            output_path = _resolve_path(output_dir, self._workspace, self._allowed_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            doc = fitz.open(str(file_path))
            image_count = 0

            for page_num, page in enumerate(doc):
                images = page.get_images()
                for img_index, img in enumerate(images):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    image_name = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                    image_path = output_path / image_name

                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    image_count += 1

            doc.close()

            return f"Successfully extracted {image_count} images to {output_path}"

        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error extracting images: {str(e)}"


class PdfExtractTablesTool(Tool):
    """Tool to extract tables from PDF document."""

    def __init__(self, workspace: Path | None = None, allowed_dir: Path | None = None):
        self._workspace = workspace
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "pdf_extract_tables"

    @property
    def description(self) -> str:
        return "Extract tables from a PDF document. Returns JSON format."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute path to the PDF file"
                },
                "page": {
                    "type": "integer",
                    "description": "Page number (1-based). Default: all pages"
                }
            },
            "required": ["path"]
        }

    async def execute(self, path: str, page: int | None = None, **kwargs: Any) -> str:
        try:
            import fitz
        except ImportError:
            return "Error: PyMuPDF is required. Install with: pip install pymupdf"

        try:
            file_path = _resolve_path(path, self._workspace, self._allowed_dir)
            if not file_path.exists():
                return f"Error: File not found: {path}"
            if not file_path.suffix.lower() == ".pdf":
                return f"Error: Not a PDF file: {path}"

            doc = fitz.open(str(file_path))

            tables_found = []

            if page:
                if 1 <= page <= len(doc):
                    pages_to_check = [doc[page - 1]]
                else:
                    return f"Error: Page {page} out of range (1-{len(doc)})"
            else:
                pages_to_check = doc

            for page_num, page in enumerate(pages_to_check):
                text = page.get_text()
                tables = page.find_tables()

                if tables:
                    for table in tables:
                        table_data = []
                        for row in table.extract():
                            table_data.append([cell.strip() if cell else "" for cell in row])
                        tables_found.append({
                            "page": page_num + 1,
                            "rows": len(table_data),
                            "cols": len(table_data[0]) if table_data else 0,
                            "data": table_data
                        })

            doc.close()

            if not tables_found:
                return "No tables found in the specified page(s)."

            return json.dumps({"tables": tables_found}, ensure_ascii=False, indent=2)

        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error extracting tables: {str(e)}"


class PdfToMarkdownTool(Tool):
    """Tool to convert PDF to Markdown format."""

    def __init__(self, workspace: Path | None = None, allowed_dir: Path | None = None):
        self._workspace = workspace
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "pdf_to_markdown"

    @property
    def description(self) -> str:
        return "Convert PDF document to Markdown format, preserving basic structure."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute path to the PDF file"
                },
                "output_path": {
                    "type": "string",
                    "description": "Output markdown file path. If not provided, returns markdown text"
                }
            },
            "required": ["path"]
        }

    async def execute(self, path: str, output_path: str | None = None, **kwargs: Any) -> str:
        try:
            import fitz
        except ImportError:
            return "Error: PyMuPDF is required. Install with: pip install pymupdf"

        try:
            file_path = _resolve_path(path, self._workspace, self._allowed_dir)
            if not file_path.exists():
                return f"Error: File not found: {path}"
            if not file_path.suffix.lower() == ".pdf":
                return f"Error: Not a PDF file: {path}"

            doc = fitz.open(str(file_path))
            markdown_parts = []

            for page_num, page in enumerate(doc):
                text = page.get_text("markdown")
                markdown_parts.append(f"## Page {page_num + 1}\n\n{text}")

            doc.close()
            markdown_content = "\n\n".join(markdown_parts)

            if output_path:
                out_path = _resolve_path(output_path, self._workspace, self._allowed_dir)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(markdown_content, encoding="utf-8")
                return f"Successfully converted to Markdown: {out_path}"

            return markdown_content

        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error converting to Markdown: {str(e)}"
