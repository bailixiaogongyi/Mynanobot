"""Image generation provider for text-to-image models."""

import asyncio
import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp
from loguru import logger


@dataclass
class ImageGenerationResponse:
    """Response from image generation API."""
    images: list[str]  # List of base64 encoded images or URLs
    image_urls: list[str]  # List of image URLs (if available)
    revised_prompt: str | None = None  # Revised prompt (for models that refine it)


class ImageGenerationProvider:
    """Provider for text-to-image generation.
    
    Supports SiliconFlow API with the following models:
    - Kwai-Kolors/Kolors (快手可图)
    - Qwen/Qwen-Image (通义万相)
    """
    
    SUPPORTED_MODELS = [
        "Kwai-Kolors/Kolors",
        "Qwen/Qwen-Image",
    ]
    
    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        model: str = "Kwai-Kolors/Kolors",
    ):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
    
    def _validate_model(self) -> bool:
        """Check if the model is supported."""
        return self.model in self.SUPPORTED_MODELS
        
    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str | None = None,
        n: int = 1,
        **kwargs: Any,
    ) -> ImageGenerationResponse:
        """Generate images from text prompt.
        
        Args:
            prompt: Text description of the desired image.
            size: Size of the image (e.g., "1024x1024", "512x512").
            quality: Quality of the image ("standard", "hd").
            style: Style of the image (e.g., "vivid", "natural").
            n: Number of images to generate.
            
        Returns:
            ImageGenerationResponse with generated images.
        """
        if not self._validate_model():
            raise Exception(f"Unsupported model: {self.model}. Supported models: {self.SUPPORTED_MODELS}")
        
        return await self._generate_siliconflow(prompt, size, n, **kwargs)
    
    async def _generate_siliconflow(
        self,
        prompt: str,
        size: str,
        n: int,
        **kwargs: Any,
    ) -> ImageGenerationResponse:
        """Generate images using SiliconFlow API.
        
        API Reference: https://docs.siliconflow.cn/cn/api-reference/images/images-generations
        """
        api_base = self.api_base or "https://api.siliconflow.cn/v1"
        
        if not self.api_key:
            raise Exception("API key is required for SiliconFlow. Please configure it in settings.")
        
        size_map = {
            "1024x1024": "1024x1024",
            "512x512": "512x512",
            "768x512": "768x512",
            "512x768": "512x768",
            "1024x576": "1024x576",
            "576x1024": "576x1024",
        }
        
        actual_size = size_map.get(size, "1024x1024")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "image_size": actual_size,
            "n": n,
            "prompt_enhancement": kwargs.get("prompt_enhancement", True),
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{api_base}/images/generations",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=180),
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        if resp.status == 401:
                            raise Exception("Invalid API key. Please check your SiliconFlow API key.")
                        elif resp.status == 429:
                            raise Exception("Rate limit exceeded. Please try again later.")
                        raise Exception(f"SiliconFlow API error: {resp.status} - {error_text}")
                    
                    data = await resp.json()
                    
                    images = []
                    image_urls = []
                    
                    for item in data.get("data", []):
                        if "url" in item:
                            image_urls.append(item["url"])
                        if "b64_json" in item:
                            images.append(item["b64_json"])
                    
                    return ImageGenerationResponse(
                        images=images,
                        image_urls=image_urls,
                        revised_prompt=data.get("revised_prompt"),
                    )
        except aiohttp.ClientError as e:
            raise Exception(f"Network error connecting to SiliconFlow API: {str(e)}")
        except asyncio.TimeoutError:
            raise Exception("SiliconFlow API request timed out. Please try again.")


class ImageProviderRegistry:
    """Registry of image generation providers (SiliconFlow only)."""
    
    PROVIDERS = {
        "siliconflow": {
            "models": [
                "Kwai-Kolors/Kolors",
                "Qwen/Qwen-Image",
            ],
            "default_model": "Kwai-Kolors/Kolors",
            "api_base": "https://api.siliconflow.cn/v1",
            "env_key": "SILICONFLOW_API_KEY",
        },
    }
    
    @classmethod
    def get_default_model(cls, provider: str) -> str:
        """Get default model for a provider."""
        return cls.PROVIDERS.get(provider, {}).get("default_model", "Kwai-Kolors/Kolors")
    
    @classmethod
    def get_available_models(cls, provider: str) -> list[str]:
        """Get available models for a provider."""
        return cls.PROVIDERS.get(provider, {}).get("models", [])
