import asyncio, os, mimetypes
from pathlib import Path
from typing import Optional, List, Dict, Any
import httpx
from settings import settings                      # ← 여기만
from common.retry import jittered_backoff

async def robust_post_form(url: str, data: Dict[str, Any], *, max_retries: int | None = None) -> Dict[str, Any]:
    retries = max_retries if max_retries is not None else settings.STEP_MAX_RETRIES
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(settings.HTTP_TIMEOUT_SEC)) as client:
                r = await client.post(url, data=data)
                r.raise_for_status()
                return r.json()
        except Exception as e:
            last_err = e
            await asyncio.sleep(jittered_backoff(attempt, max_backoff=settings.STEP_MAX_BACKOFF))
    raise last_err or RuntimeError(f"POST failed: {url}")

async def robust_upload_images(image_paths: List[str], url: str, *, max_retries: int | None = None) -> List[Dict[str, Any]]:
    retries = max_retries if max_retries is not None else settings.STEP_MAX_RETRIES
    results: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(settings.HTTP_TIMEOUT_SEC)) as client:
        for p in image_paths:
            fn = Path(os.path.abspath(p)).as_posix()
            mime = mimetypes.guess_type(fn)[0] or "application/octet-stream"
            last_err: Optional[Exception] = None
            for attempt in range(retries):
                try:
                    with open(fn, "rb") as f:
                        r = await client.post(url, files={"image": (fn, f, mime)})
                        r.raise_for_status()
                        results.append(r.json())
                        break
                except Exception as e:
                    last_err = e
                    await asyncio.sleep(jittered_backoff(attempt, max_backoff=settings.STEP_MAX_BACKOFF))
            else:
                raise last_err or RuntimeError(f"upload failed: {fn}")
    return results
