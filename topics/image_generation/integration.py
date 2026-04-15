"""Image Generation — ComfyUI / AUTOMATIC1111 / InvokeAI integrations."""
from __future__ import annotations
import os


class ImageGenerationTopic:
    name = "image_generation"
    tools = ["stable-diffusion", "comfyui", "automatic1111", "invokeai", "fooocus", "kandinsky", "flux"]

    async def txt2img(self, prompt: str, steps: int = 20) -> dict:
        base = os.getenv("A1111_URL", "http://localhost:7860")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post(f"{base}/sdapi/v1/txt2img",
                                  json={"prompt": prompt, "steps": steps})
                return {"images": r.json().get("images", [])}
        except Exception as e:
            return {"error": str(e)}
