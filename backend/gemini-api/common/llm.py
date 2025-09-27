from __future__ import annotations
import asyncio
from typing import Optional, List
from settings import settings
from common.retry import jittered_backoff
from common.text import to_text

async def generate_text_with_retry(service, model: str, prompt: str, *, max_retries: int | None = None) -> str:
    retries = max_retries if max_retries is not None else settings.STEP_MAX_RETRIES
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = await service.generate_content(model, prompt)
            text = to_text(resp)
            if not text:
                raise RuntimeError("empty text")
            return text
        except Exception as e:
            last_err = e
            await asyncio.sleep(jittered_backoff(attempt))
    raise last_err or RuntimeError("generate_text_with_retry failed")

async def generate_images_with_retry(service, image_model: Optional[str], prompt: str, *, max_retries: int | None = None) -> List[str]:
    retries = max_retries if max_retries is not None else settings.STEP_MAX_RETRIES
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            paths = await service.generate_image(image_model, prompt)
            if not paths:
                raise RuntimeError("empty image list")
            return paths
        except Exception as e:
            last_err = e
            await asyncio.sleep(jittered_backoff(attempt))
    raise last_err or RuntimeError("generate_images_with_retry failed")
