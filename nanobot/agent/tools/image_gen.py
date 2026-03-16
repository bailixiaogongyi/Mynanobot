"""Image generation tool for AI text-to-image."""

import base64
import os
import uuid
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.agent.tools.base import Tool


class ImageGenerationTool(Tool):
    """Tool to generate images from text descriptions using AI.
    
    Supports multiple image generation backends:
    - OpenAI DALL-E
    - 阿里云通义万相 (WanXiang)
    - 百度千帆 (ERNIE)
    - Custom endpoints
    """
    
    def __init__(
        self,
        workspace: Path | None = None,
        allowed_dir: Path | None = None,
        image_provider=None,
    ):
        self._workspace = workspace
        self._allowed_dir = allowed_dir
        self._image_provider = image_provider
    
    @property
    def name(self) -> str:
        return "generate_image"
    
    @property
    def description(self) -> str:
        return (
            "Generate images from text descriptions using AI. "
            "Provide a detailed prompt describing the image you want to create. "
            "The tool will return the generated image(s) as file path(s) that can be sent to users."
        )
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Text description of the desired image. Be as detailed as possible for better results."
                },
                "size": {
                    "type": "string",
                    "description": "Image size (e.g., '1024x1024', '512x512'). Default: 1024x1024",
                    "default": "1024x1024"
                },
                "quality": {
                    "type": "string",
                    "description": "Image quality - 'standard' or 'hd' (only for DALL-E 3)",
                    "default": "standard"
                },
                "n": {
                    "type": "integer",
                    "description": "Number of images to generate (1-10)",
                    "default": 1
                },
                "save_path": {
                    "type": "string",
                    "description": "Optional path to save the generated image(s). If not specified, saves to workspace with generated filename."
                }
            },
            "required": ["prompt"]
        }
    
    def _get_workspace(self) -> Path:
        """Get the workspace directory for saving images."""
        if self._workspace:
            workspace = self._workspace
        else:
            workspace = Path.home() / ".nanobot" / "generated_images"
        
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace
    
    async def execute(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
        save_path: str | None = None,
        **kwargs: Any
    ) -> str:
        """Execute image generation.
        
        Args:
            prompt: Text description of the desired image.
            size: Image size.
            quality: Image quality.
            n: Number of images.
            save_path: Optional custom save path.
            
        Returns:
            Result message with image paths.
        """
        if not self._image_provider:
            return "Error: Image generation provider not configured. Please configure image generation in settings."
        
        try:
            logger.info(f"Generating image with prompt: {prompt[:50]}...")
            
            response = await self._image_provider.generate(
                prompt=prompt,
                size=size,
                quality=quality,
                n=n,
            )
            
            workspace = self._get_workspace()
            saved_paths = []
            
            for i, image_data in enumerate(response.images):
                if image_data:
                    file_name = f"generated_{uuid.uuid4().hex[:8]}_{i}.png"
                    file_path = workspace / file_name
                    
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    image_bytes = base64.b64decode(image_data)
                    file_path.write_bytes(image_bytes)
                    saved_paths.append(str(file_path))
                    logger.info(f"Saved generated image to: {file_path}")
            
            for i, image_url in enumerate(response.image_urls):
                if image_url:
                    file_name = f"generated_{uuid.uuid4().hex[:8]}_{len(saved_paths)}.png"
                    file_path = workspace / file_name
                    
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_url) as resp:
                            if resp.status == 200:
                                file_path.write_bytes(await resp.read())
                                saved_paths.append(str(file_path))
                                logger.info(f"Downloaded and saved image to: {file_path}")
            
            if not saved_paths:
                return f"Error: No images were generated. Please try again with a different prompt."
            
            if len(saved_paths) == 1:
                return f"Image generated successfully!\n\nImage saved to: {saved_paths[0]}\n\nPrompt: {prompt}"
            else:
                paths_str = "\n".join([f"- {p}" for p in saved_paths])
                return f"Generated {len(saved_paths)} images successfully!\n\nImages saved to:\n{paths_str}\n\nPrompt: {prompt}"
                
        except Exception as e:
            logger.exception("Image generation failed")
            return f"Error generating image: {str(e)}"


class ImageUnderstandingTool(Tool):
    """Tool to understand images using multimodal AI models.
    
    This tool uses vision-capable models to analyze and describe images.
    """
    
    def __init__(
        self,
        llm_provider=None,
    ):
        self._llm_provider = llm_provider
    
    @property
    def name(self) -> str:
        return "understand_image"
    
    @property
    def description(self) -> str:
        return (
            "Analyze and describe images using AI vision capabilities. "
            "Provide an image path and a question about the image. "
            "The tool will analyze the image and provide a detailed description or answer your question."
        )
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the image file to analyze"
                },
                "question": {
                    "type": "string",
                    "description": "Question about the image (e.g., 'Describe this image', 'What text is in the image?')"
                }
            },
            "required": ["image_path", "question"]
        }
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve image path."""
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = Path.home() / ".nanobot" / p
        return p.resolve()
    
    async def execute(
        self,
        image_path: str,
        question: str = "Describe this image in detail.",
        **kwargs: Any
    ) -> str:
        """Execute image understanding.
        
        Args:
            image_path: Path to the image file.
            question: Question about the image.
            
        Returns:
            Analysis result.
        """
        if not self._llm_provider:
            return "Error: LLM provider not configured. Please configure a vision-capable model."
        
        try:
            file_path = self._resolve_path(image_path)
            
            if not file_path.exists():
                return f"Error: Image file not found: {image_path}"
            
            import mimetypes
            
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = "image/png"
            
            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            image_url = f"data:{mime_type};base64,{image_data}"
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
            
            response = await self._llm_provider.chat(
                messages=messages,
                max_tokens=2048,
            )
            
            if response.content:
                return response.content
            else:
                return "Error: No response from vision model."
                
        except Exception as e:
            logger.exception("Image understanding failed")
            return f"Error analyzing image: {str(e)}"
