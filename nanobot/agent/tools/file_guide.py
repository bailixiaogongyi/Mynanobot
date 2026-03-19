"""File processing helper tool - provides guidance on how to handle various file types."""

from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


class FileProcessingGuideTool(Tool):
    """
    Tool to provide guidance on processing different file types.
    
    When user uploads a file, use this tool to determine the best approach:
    - Images: OCR (ocr_recognize) vs Vision understanding (image_understand)
    - PDFs: Text extraction, table extraction, image extraction
    - Word/Excel: Read content, analyze data, modify formatting
    - Other files: Determine appropriate handling
    """

    def __init__(self, workspace: Path | None = None, allowed_dir: Path | None = None):
        self._workspace = workspace
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "file_processing_guide"
    
    @property
    def description(self) -> str:
        return (
            "Get guidance on how to process a file. Use this tool when user uploads a file "
            "and you need to determine the best processing approach. "
            "This tool analyzes the file and recommends appropriate tools."
        )
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file that needs processing"
                },
                "user_request": {
                    "type": "string",
                    "description": "What the user wants to do with the file (e.g., 'extract text', 'analyze data', 'recognize text')"
                }
            },
            "required": ["file_path", "user_request"]
        }
    
    async def execute(self, file_path: str, user_request: str = "", **kwargs: Any) -> str:
        """Analyze file and provide processing guidance."""
        import mimetypes
        
        file_path_obj = Path(file_path).expanduser()
        
        if not file_path_obj.exists():
            return f"Error: File not found: {file_path}"
        
        ext = file_path_obj.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(file_path_obj))
        
        guidance = {
            ".pdf": {
                "type": "PDF Document",
                "tools": {
                    "extract_text": "pdf_read_text - Read plain text from PDF pages",
                    "extract_tables": "pdf_extract_tables - Extract tables in JSON format",
                    "extract_images": "pdf_extract_images - Extract embedded images",
                    "get_structure": "pdf_read_structure - Get page count and metadata",
                    "convert_markdown": "pdf_to_markdown - Convert to Markdown format",
                    "ocr": "ocr_pdf - Use OCR for scanned PDFs"
                },
                "recommendation": self._recommend_pdf_processing(user_request)
            },
            ".docx": {
                "type": "Word Document",
                "tools": {
                    "read_text": "docx_read_text - Extract text content",
                    "read_tables": "docx_read_tables - Extract table data",
                    "read_structure": "docx_read_structure - Get document structure",
                    "set_font": "docx_set_font - Modify font properties",
                    "set_format": "docx_set_paragraph_format - Adjust paragraph formatting",
                    "from_template": "docx_from_template - Generate from template"
                },
                "recommendation": self._recommend_docx_processing(user_request)
            },
            ".xlsx": {
                "type": "Excel Spreadsheet",
                "tools": {
                    "read_data": "excel_read - Read cell data as JSON",
                    "list_sheets": "excel_list_sheets - List all sheets",
                    "create_sheet": "excel_create_sheet - Add new sheet",
                    "write_data": "excel_write - Write data to Excel",
                    "set_cell": "excel_set_cell - Modify specific cell"
                },
                "recommendation": self._recommend_excel_processing(user_request)
            },
            ".pptx": {
                "type": "PowerPoint Presentation",
                "tools": {
                    "read_content": "pptx_read - Extract slide content",
                    "create_slides": "pptx_create - Create new presentation"
                },
                "recommendation": self._recommend_pptx_processing(user_request)
            },
            ".jpg": {
                "type": "Image (JPEG)",
                "tools": {
                    "ocr": "ocr_recognize - Extract text from image",
                    "vision": "image_understand - Describe image content using AI"
                },
                "recommendation": self._recommend_image_processing(user_request, "jpeg")
            },
            ".jpeg": {
                "type": "Image (JPEG)",
                "tools": {
                    "ocr": "ocr_recognize - Extract text from image",
                    "vision": "image_understand - Describe image content using AI"
                },
                "recommendation": self._recommend_image_processing(user_request, "jpeg")
            },
            ".png": {
                "type": "Image (PNG)",
                "tools": {
                    "ocr": "ocr_recognize - Extract text from image",
                    "vision": "image_understand - Describe image content using AI"
                },
                "recommendation": self._recommend_image_processing(user_request, "png")
            },
            ".gif": {
                "type": "Image (GIF)",
                "tools": {
                    "ocr": "ocr_recognize - Extract text from image",
                    "vision": "image_understand - Describe image content using AI"
                },
                "recommendation": self._recommend_image_processing(user_request, "gif")
            },
            ".bmp": {
                "type": "Image (BMP)",
                "tools": {
                    "ocr": "ocr_recognize - Extract text from image",
                    "vision": "image_understand - Describe image content using AI"
                },
                "recommendation": self._recommend_image_processing(user_request, "bmp")
            },
            ".webp": {
                "type": "Image (WebP)",
                "tools": {
                    "ocr": "ocr_recognize - Extract text from image",
                    "vision": "image_understand - Describe image content using AI"
                },
                "recommendation": self._recommend_image_processing(user_request, "webp")
            },
            ".txt": {
                "type": "Text File",
                "tools": {
                    "read": "read_file - Read plain text content"
                },
                "recommendation": "Simply use read_file tool to read the text content."
            },
            ".md": {
                "type": "Markdown File",
                "tools": {
                    "read": "read_file - Read markdown content"
                },
                "recommendation": "Use read_file to read the markdown. The content can be displayed directly in chat."
            },
            ".csv": {
                "type": "CSV Data File",
                "tools": {
                    "read": "read_file - Read raw CSV data",
                    "excel": "excel_read - Read as structured data"
                },
                "recommendation": "Use excel_read tool to parse as structured data for analysis."
            },
        }
        
        if ext in guidance:
            info = guidance[ext]
            result = f"""# File Processing Guide

## File Type: {info['type']}
## File Path: {file_path}

### Available Tools:"""
            
            for tool_name, tool_desc in info['tools'].items():
                result += f"\n- **{tool_name}**: {tool_desc}"
            
            result += f"\n\n### Recommendation for your request: \"{user_request}\"\n"
            result += f"{info['recommendation']}"
            
            result += "\n\n### Next Steps:\n"
            result += "1. Use the recommended tool to process the file\n"
            result += "2. After processing, summarize the results to the user\n"
            result += "3. If user wants to save/return the processed file, use return_file tool"
            
            return result
        else:
            return f"""# Unknown File Type

## File: {file_path}
## Extension: {ext}
## MIME Type: {mime_type or 'unknown'}

This file type may not be directly supported. Suggestions:
- Try reading the file with read_file tool
- If it's a special format, check if it can be converted
- For compressed files, suggest user extract first
"""

    def _recommend_pdf_processing(self, user_request: str) -> str:
        """Recommend PDF processing approach."""
        request = user_request.lower()
        
        if any(kw in request for kw in ["文字", "文本", "内容", "read", "extract", "text"]):
            return "Use pdf_read_text to extract the text content. If the PDF is scanned (no selectable text), use ocr_pdf instead."
        elif any(kw in request for kw in ["表格", "table", "数据"]):
            return "Use pdf_extract_tables to extract table data in JSON format."
        elif any(kw in request for kw in ["图片", "image", "提取"]):
            return "Use pdf_extract_images to extract embedded images."
        elif any(kw in request for kw in ["结构", "structure", "页数", "metadata"]):
            return "Use pdf_read_structure to get document structure and metadata."
        elif any(kw in request for kw in ["markdown", "转换"]):
            return "Use pdf_to_markdown to convert PDF to Markdown format."
        else:
            return "Use pdf_read_text to extract text content first, then analyze based on the results."

    def _recommend_docx_processing(self, user_request: str) -> str:
        """Recommend Word document processing approach."""
        request = user_request.lower()
        
        if any(kw in request for kw in ["文字", "文本", "内容", "read", "text"]):
            return "Use docx_read_text to extract text content."
        elif any(kw in request for kw in ["表格", "table", "数据"]):
            return "Use docx_read_tables to extract table data in JSON format."
        elif any(kw in request for kw in ["结构", "structure", "标题"]):
            return "Use docx_read_structure to get document structure including headings."
        elif any(kw in request for kw in ["字体", "font", "样式", "style"]):
            return "Use docx_set_font or docx_set_paragraph_format to modify styles."
        elif any(kw in request for kw in ["模板", "template"]):
            return "Use docx_from_template to generate document from a template."
        else:
            return "Use docx_read_text to read the document content first."

    def _recommend_excel_processing(self, user_request: str) -> str:
        """Recommend Excel processing approach."""
        request = user_request.lower()
        
        if any(kw in request for kw in ["读", "read", "数据", "data", "分析"]):
            return "Use excel_read to read data as JSON. You can specify sheet_name and header_row parameters."
        elif any(kw in request for kw in ["表", "sheets", "工作表"]):
            return "Use excel_list_sheets to see all available sheets."
        elif any(kw in request for kw in ["写", "write", "创建", "create", "新增"]):
            return "Use excel_write to write data to a new file or append to existing."
        elif any(kw in request for kw in ["修改", "修改", "单元格", "cell"]):
            return "Use excel_set_cell to modify specific cell values."
        else:
            return "Use excel_read to read the spreadsheet data."

    def _recommend_pptx_processing(self, user_request: str) -> str:
        """Recommend PowerPoint processing approach."""
        request = user_request.lower()
        
        if any(kw in request for kw in ["读", "read", "内容", "提取"]):
            return "Use pptx_read to extract slide content including text and images."
        elif any(kw in request for kw in ["创建", "create", "新建"]):
            return "Use pptx_create to create a new presentation."
        else:
            return "Use pptx_read to extract the presentation content."

    def _recommend_image_processing(self, user_request: str, img_type: str) -> str:
        """Recommend image processing approach."""
        request = user_request.lower()
        
        if any(kw in request for kw in ["文字", "ocr", "识别", "recognize", "提取"]):
            return "Use ocr_recognize tool to extract text from the image. This uses OCR technology."
        elif any(kw in request for kw in ["描述", "内容", "图片", "describe", "understand", "分析", "看"]):
            return "Use image_understand tool to get AI-powered image analysis and description. This uses vision AI."
        elif any(kw in request for kw in ["翻译", "translate"]):
            return "First use ocr_recognize to extract text, then translate the text using your language capabilities."
        else:
            return """Based on your request, choose:
- **For text extraction (OCR)**: Use ocr_recognize
- **For image understanding**: Use image_understand

If you're not sure, you can do both: use ocr_recognize first for text, then image_understand for visual analysis."""
