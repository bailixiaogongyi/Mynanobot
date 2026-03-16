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
    
    Supports multiple backends:
    - OpenAI DALL-E
    - 阿里云通义万相 (WanXiang)
    - 百度千帆 (ERNIE iRAG)
    - Stability AI
    - Custom endpoints
    """
    
    PROVIDER_MODEL_MAP = {
        "dall-e-2": "openai",
        "dall-e-3": "openai",
        "wan21-turbo": "dashscope",
        "wan21": "dashscope",
        "ernie-iprag-t2i": "baidu",
    }
    
    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        model: str = "dall-e-3",
        provider: str | None = None,
    ):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self._provider = provider
    
    def _detect_provider(self) -> str:
        """Detect provider from model name or explicit setting."""
        if self._provider:
            return self._provider
        
        if self.model in self.PROVIDER_MODEL_MAP:
            return self.PROVIDER_MODEL_MAP[self.model]
        
        if self.model.startswith("wan") or "tongyi" in self.model.lower():
            return "dashscope"
        elif self.model.startswith("ernie") or self.model.startswith("yi"):
            return "baidu"
        elif self.model.startswith("dall-e"):
            return "openai"
        else:
            return "generic"
        
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
        provider = self._detect_provider()
        
        if provider == "dashscope":
            return await self._generate_wanxiang(prompt, size, n, **kwargs)
        elif provider == "baidu":
            return await self._generate_baidu(prompt, size, n, **kwargs)
        elif provider == "openai":
            return await self._generate_dalle(prompt, size, quality, style, n)
        else:
            return await self._generate_generic(prompt, size, n, **kwargs)
    
    async def _generate_dalle(
        self,
        prompt: str,
        size: str,
        quality: str,
        style: str | None,
        n: int,
    ) -> ImageGenerationResponse:
        """Generate images using OpenAI DALL-E API."""
        api_base = self.api_base or "https://api.openai.com/v1"
        
        if not self.api_key:
            raise Exception("API key is required for DALL-E. Please configure it in settings.")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": n,
        }
        
        if style:
            payload["style"] = style
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{api_base}/images/generations",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        if resp.status == 401:
                            raise Exception("Invalid API key. Please check your DALL-E API key.")
                        elif resp.status == 429:
                            raise Exception("Rate limit exceeded. Please try again later.")
                        raise Exception(f"DALL-E API error: {resp.status} - {error_text}")
                    
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
            raise Exception(f"Network error connecting to DALL-E API: {str(e)}")
        except asyncio.TimeoutError:
            raise Exception("DALL-E API request timed out. Please try again.")
    
    async def _generate_wanxiang(
        self,
        prompt: str,
        size: str,
        n: int,
        **kwargs: Any,
    ) -> ImageGenerationResponse:
        """Generate images using 阿里云通义万相 API."""
        api_base = self.api_base or "https://dashscope.aliyuncs.com/api/v1"
        
        size_map = {
            "1024x1024": "1024*1024",
            "512x512": "512*512",
            "768x768": "768*768",
            "720x1280": "720*1280",
            "1280x720": "1280*720",
        }
        
        actual_size = size_map.get(size, "1024*1024")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "disable",
        }
        
        payload = {
            "model": self.model,
            "input": {
                "prompt": prompt,
            },
            "parameters": {
                "size": actual_size,
                "n": n,
            }
        }
        
        if "style" in kwargs:
            payload["parameters"]["style"] = kwargs["style"]
            
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base}/services/aigc/text2image/image-synthesis",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=180),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"WanXiang API error: {resp.status} - {error_text}")
                
                data = await resp.json()
                
                if data.get("output", {}).get("task_status") == "SUCCEEDED":
                    images = []
                    image_urls = []
                    
                    for item in data.get("output", {}).get("results", []):
                        if "url" in item:
                            image_urls.append(item["url"])
                    
                    return ImageGenerationResponse(
                        images=images,
                        image_urls=image_urls,
                        revised_prompt=prompt,
                    )
                elif data.get("output", {}).get("task_status") == "PENDING":
                    task_id = data.get("output", {}).get("task_id")
                    if task_id:
                        return await self._poll_wanxiang_task(session, api_base, headers, task_id, prompt)
                    raise Exception(f"WanXiang async task started but no task_id returned")
                else:
                    raise Exception(f"WanXiang generation failed: {data}")
    
    async def _poll_wanxiang_task(
        self,
        session: aiohttp.ClientSession,
        api_base: str,
        headers: dict,
        task_id: str,
        original_prompt: str,
        max_wait: int = 180,
    ) -> ImageGenerationResponse:
        """Poll for async WanXiang task completion."""
        import asyncio
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait:
                raise Exception(f"WanXiang task timeout after {max_wait}s")
            
            await asyncio.sleep(3)
            
            async with session.get(
                f"{api_base}/tasks/{task_id}",
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    continue
                
                data = await resp.json()
                status = data.get("output", {}).get("task_status")
                
                if status == "SUCCEEDED":
                    images = []
                    image_urls = []
                    
                    for item in data.get("output", {}).get("results", []):
                        if "url" in item:
                            image_urls.append(item["url"])
                    
                    return ImageGenerationResponse(
                        images=images,
                        image_urls=image_urls,
                        revised_prompt=original_prompt,
                    )
                elif status == "FAILED":
                    raise Exception(f"WanXiang task failed: {data}")
                elif status in ("PENDING", "RUNNING"):
                    continue
                else:
                    raise Exception(f"WanXiang unknown status: {status}")
    
    async def _generate_baidu(
        self,
        prompt: str,
        size: str,
        n: int,
        **kwargs: Any,
    ) -> ImageGenerationResponse:
        """Generate images using 百度千帆 ERNIE API."""
        api_base = self.api_base or "https://qianfan.baidubce.com/v2"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        size_map = {
            "1024x1024": "1024x1024",
            "512x512": "512x512",
        }
        
        actual_size = size_map.get(size, "1024x1024")
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": actual_size,
            "n": n,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base}/text2image",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=180),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Baidu API error: {resp.status} - {error_text}")
                
                data = await resp.json()
                
                images = []
                image_urls = []
                
                if "data" in data:
                    for item in data["data"]:
                        if "b64_image" in item:
                            images.append(item["b64_image"])
                        if "image_url" in item:
                            image_urls.append(item["image_url"])
                
                return ImageGenerationResponse(
                    images=images,
                    image_urls=image_urls,
                    revised_prompt=prompt,
                )
    
    async def _generate_generic(
        self,
        prompt: str,
        size: str,
        n: int,
        **kwargs: Any,
    ) -> ImageGenerationResponse:
        """Generate images using generic API (custom endpoint)."""
        if not self.api_base:
            raise Exception("No API base URL configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "prompt": prompt,
            "size": size,
            "n": n,
            **kwargs,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/images/generations",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=180),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Image generation API error: {resp.status} - {error_text}")
                
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


class ImageProviderRegistry:
    """Registry of image generation providers."""
    
    PROVIDERS = {
        "openai": {
            "models": ["dall-e-2", "dall-e-3"],
            "default_model": "dall-e-3",
            "api_base": "https://api.openai.com/v1",
        },
        "dashscope": {
            "models": ["wan21-turbo", "wan21"],
            "default_model": "wan21-turbo",
            "api_base": "https://dashscope.aliyuncs.com/api/v1",
            "env_key": "DASHSCOPE_API_KEY",
        },
        "baidu": {
            "models": ["ernie-iprag-t2i", "ernie-vimg大模型-4"],
            "default_model": "ernie-iprag-t2i",
            "api_base": "https://qianfan.baidubce.com/v2",
            "env_key": "BAIDU_API_KEY",
        },
        "custom": {
            "models": [],
            "default_model": "custom",
            "api_base": None,
        },
    }
    
    @classmethod
    def get_default_model(cls, provider: str) -> str:
        """Get default model for a provider."""
        return cls.PROVIDERS.get(provider, {}).get("default_model", "dall-e-3")
    
    @classmethod
    def get_available_models(cls, provider: str) -> list[str]:
        """Get available models for a provider."""
        return cls.PROVIDERS.get(provider, {}).get("models", [])
