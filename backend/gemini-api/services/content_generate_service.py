# content_generate_service.py
from __future__ import annotations
import os
import uuid
import base64
import asyncio
import random
import logging
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import log_config  # logger 설정 모듈 (사용 중)
from google import genai
from google.genai import types, errors as genai_errors
from PIL import Image

# ✅ 여기! name이 아니라 __name__ 을 사용해야 합니다.
logger = logging.getLogger(__name__)

# 동시성 제한(환경변수 조절 가능)
GENAI_MAX_CONCURRENCY = int(os.getenv("GENAI_MAX_CONCURRENCY", "3"))
_genai_sem = asyncio.Semaphore(GENAI_MAX_CONCURRENCY)

# 재시도/백오프(환경변수 조절 가능)
GENAI_MAX_ATTEMPTS = int(os.getenv("GENAI_MAX_ATTEMPTS", "6"))
GENAI_MAX_BACKOFF = float(os.getenv("GENAI_MAX_BACKOFF", "20.0"))

# 이미지 저장 경로(컨테이너에서 쓰기 가능한 디렉터리 권장)
IMG_OUT_DIR = os.getenv("IMG_OUT_DIR", "/app/images")


def _jittered_backoff(attempt: int, max_backoff: float = GENAI_MAX_BACKOFF) -> float:
    # 2^n + [0.1, 0.9] 무작위 지터
    return min(2 ** attempt, max_backoff) + random.uniform(0.1, 0.9)


def _ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _decode_inline_data(data: Any) -> Optional[bytes]:
    """
    Gemini inline_data.data 는 bytes 또는 base64 str 일 수 있음.
    둘 다 안전하게 bytes로 변환.
    """
    if data is None:
        return None
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, str):
        try:
            return base64.b64decode(data)
        except Exception:
            return None
    return None


def _save_image_bytes(bin_: bytes, out_dir: Path, ext: str = "png") -> str:
    img = Image.open(BytesIO(bin_))
    img.load()  # PIL lazy-load 방지
    fpath = out_dir / f"{uuid.uuid4()}.{ext}"
    img.save(fpath)
    return str(fpath)


class ContentGenerateService:
    client = genai.Client()

    # ============== TEXT ==============
    async def generate_content(self, model, contents):
        """
        - 동기 SDK 호출을 to_thread로 위임(이벤트 루프 블로킹 방지)
        - 503/RateLimit에 대해 지수 백오프+지터로 재시도
        - 기존과 동일하게 '원본 응답 객체'를 반환(호출부 호환성 유지)
        """
        last_exc: Optional[Exception] = None

        for attempt in range(GENAI_MAX_ATTEMPTS):
            try:
                async with _genai_sem:
                    def _call():
                        return self.client.models.generate_content(
                            model=model,
                            contents=contents
                        )
                    response = await asyncio.to_thread(_call)
                return response
            except (genai_errors.ServerError, genai_errors.RateLimitError) as e:
                last_exc = e
                delay = _jittered_backoff(attempt)
                logger.warning(
                    f"[genai:text] transient error (attempt {attempt+1}/{GENAI_MAX_ATTEMPTS}): {e} → sleep {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                continue
            except Exception as e:
                last_exc = e
                logger.exception(f"[genai:text] unexpected error: {e}")
                raise

        raise last_exc or RuntimeError("generate_content failed after retries")

    # ============== IMAGE ==============
    async def generate_image(self, image_model, contents):
        """
        - 동기 SDK 호출을 to_thread로 위임
        - 503/RateLimit 재시도(지수 백오프+지터)
        - inline_data.data(bytes/base64) 모두 처리
        - 저장 디렉터리 자동 생성 및 안전 경로(/tmp 등) 사용
        - 반환: 저장된 로컬 이미지 경로 리스트
        """
        last_exc: Optional[Exception] = None
        out_dir = _ensure_dir(IMG_OUT_DIR)

        for attempt in range(GENAI_MAX_ATTEMPTS):
            try:
                async with _genai_sem:
                    def _call():
                        return self.client.models.generate_content(
                            model=image_model,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                response_modalities=['TEXT', 'IMAGE']
                            )
                        )
                    response = await asyncio.to_thread(_call)

                saved_image_paths: list[str] = []

                try:
                    parts = response.candidates[0].content.parts
                except Exception:
                    parts = []

                for part in parts:
                    # 텍스트 파트는 로깅만
                    if getattr(part, "text", None):
                        logger.info(f"[genai:image] text part: {part.text[:200]}...")
                        continue

                    inline = getattr(part, "inline_data", None)
                    if inline is None:
                        continue

                    bin_ = _decode_inline_data(getattr(inline, "data", None))
                    if not bin_:
                        continue

                    mime = getattr(inline, "mime_type", None)
                    ext = "png"
                    if isinstance(mime, str):
                        if "jpeg" in mime or "jpg" in mime:
                            ext = "jpg"
                        elif "webp" in mime:
                            ext = "webp"
                        elif "gif" in mime:
                            ext = "gif"

                    try:
                        path = _save_image_bytes(bin_, out_dir, ext)
                        saved_image_paths.append(path)
                    except Exception as e:
                        logger.warning(f"[genai:image] save failed: {e}")

                if not saved_image_paths:
                    delay = _jittered_backoff(attempt)
                    logger.warning(
                        f"[genai:image] no images in response (attempt {attempt+1}/{GENAI_MAX_ATTEMPTS}) → sleep {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue

                return saved_image_paths

            except (genai_errors.ServerError, genai_errors.RateLimitError) as e:
                last_exc = e
                delay = _jittered_backoff(attempt)
                logger.warning(
                    f"[genai:image] transient error (attempt {attempt+1}/{GENAI_MAX_ATTEMPTS}): {e} → sleep {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                continue
            except Exception as e:
                last_exc = e
                logger.exception(f"[genai:image] unexpected error: {e}")
                raise

        raise last_exc or RuntimeError("generate_image failed after retries")
