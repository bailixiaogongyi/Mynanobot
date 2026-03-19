"""Test script for SiliconFlow image generation."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nanobot.providers.image_provider import ImageGenerationProvider


async def main():
    api_key = "sk-stccqvsrwandldejoswurpafynyktnqyflyzbbhcilxgbkur"
    
    print("Testing SiliconFlow image generation...")
    print(f"API Key: {api_key[:10]}...{api_key[-5:]}")
    print()
    
    models = ["Kwai-Kolors/Kolors", "Qwen/Qwen-Image"]
    
    for model in models:
        print(f"{'='*50}")
        print(f"Testing model: {model}")
        print()
        
        provider = ImageGenerationProvider(
            api_key=api_key,
            model=model,
        )
        
        try:
            response = await provider.generate(
                prompt="A beautiful sunset over the ocean",
                size="1024x1024",
                n=1,
            )
            
            print(f"SUCCESS!")
            print(f"Images generated: {len(response.images)}")
            print(f"Image URLs: {len(response.image_urls)}")
            
            if response.image_urls:
                print(f"\nGenerated image URL:")
                print(response.image_urls[0])
            
            print()
            
        except Exception as e:
            print(f"ERROR: {e}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
