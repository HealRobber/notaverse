from __future__ import annotations

import httpx
import socket
import os
import uuid
import base64
import asyncio
import random
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional, Any, List

import log_config  # logger 설정 모듈
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as gatypes
from PIL import Image

# 내부 유틸 (SDK 타입 변환기)
from utils.genai_payload import to_ga_contents

try:
    from models.content_request import ContentRequest
except Exception:
    ContentRequest = None  # 타입 체크 회피용

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────────────────────
GENAI_MAX_CONCURRENCY = int(os.getenv("GENAI_MAX_CONCURRENCY", "3"))
GENAI_MAX_ATTEMPTS = int(os.getenv("GENAI_MAX_ATTEMPTS", "6"))
GENAI_MAX_BACKOFF = float(os.getenv("GENAI_MAX_BACKOFF", "20.0"))
IMG_OUT_DIR = os.getenv("IMG_OUT_DIR", "/app/images")

_genai_sem = asyncio.Semaphore(GENAI_MAX_CONCURRENCY)

ClientErr = getattr(genai_errors, "ClientError", Exception)
ServerErr = getattr(genai_errors, "ServerError", Exception)
APIErr = getattr(genai_errors, "APIError", Exception)


# ──────────────────────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────────────────────
def _jittered_backoff(attempt: int, max_backoff: float = GENAI_MAX_BACKOFF) -> float:
    """2^n + [0.1, 0.9] 무작위 지터"""
    return min(2 ** attempt, max_backoff) + random.uniform(0.1, 0.9)


def _ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _decode_inline_data(data: Any) -> Optional[bytes]:
    """Gemini inline_data.data → bytes로 안전 변환"""
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
    img.load()  # lazy-load 방지
    fpath = out_dir / f"{uuid.uuid4()}.{ext}"
    img.save(fpath)
    return str(fpath)


def _assert_non_empty_contents(contents: List[gatypes.Content]) -> None:
    """빈 입력 방지용 검증"""
    if not contents:
        raise RuntimeError("contents is empty")
    any_text = False
    for m in contents:
        for p in (m.parts or []):
            txt = getattr(p, "text", None)
            if isinstance(txt, str) and txt.strip():
                any_text = True
                break
        if any_text:
            break
    if not any_text:
        raise RuntimeError("contents has no non-empty text parts")


def _is_retryable_error(e: Exception) -> bool:
    """429, 5xx, 타임아웃 등 재시도 가능 에러"""
    status = getattr(e, "status", None) or getattr(e, "http_status", None)
    code = getattr(e, "code", None)

    if isinstance(status, int) and (status == 429 or 500 <= status < 600):
        return True
    if isinstance(code, int) and (code == 429 or 500 <= code < 600):
        return True

    txt = repr(e).lower()
    if any(k in txt for k in [
        "429", "rate limit", "resource exhausted", "too many requests",
        "unavailable", "temporarily", "retry", "server error",
        "deadline", "timeout"
    ]):
        return True

    if isinstance(e, (TimeoutError, socket.timeout, httpx.ReadTimeout, httpx.ConnectTimeout)):
        return True

    return False


# ──────────────────────────────────────────────────────────────
# 메인 클래스
# ──────────────────────────────────────────────────────────────
class ContentGenerateService:
    client = genai.Client()

    # ============== TEXT ==============
    async def generate_content(self, model_or_req: Any, contents: Optional[Any] = None):
        """
        지원 형태:
          - generate_content(model, contents="...")                 ← 문자열
          - generate_content(model, contents=[ContentMessage...])   ← 메시지 리스트
          - generate_content(ContentRequest(...))                   ← ContentRequest 전체
        """
        # --- 인자 정규화 ---
        if ContentRequest is not None and isinstance(model_or_req, ContentRequest):
            model = model_or_req.model
            raw_contents = model_or_req.content
        elif hasattr(model_or_req, "content") and hasattr(model_or_req, "model") and contents is None:
            model = getattr(model_or_req, "model", None)
            raw_contents = getattr(model_or_req, "content", None)
        else:
            model = model_or_req
            raw_contents = contents

        if not raw_contents:
            raise TypeError("generate_content() requires non-empty 'contents'")
        if not model:
            model = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")

        # --- SDK 타입으로 변환 ---
        ga_contents = to_ga_contents(raw_contents)
        _assert_non_empty_contents(ga_contents)

        last_exc: Optional[Exception] = None

        for attempt in range(GENAI_MAX_ATTEMPTS):
            try:
                async with _genai_sem:
                    def _call():
                        return self.client.models.generate_content(
                            model=model,
                            contents=ga_contents,  # List[gatypes.Content]
                        )

                    response = await asyncio.to_thread(_call)
                return response

            except (ServerErr, APIErr, ClientErr, httpx.HTTPError, TimeoutError, socket.timeout) as e:
                if _is_retryable_error(e):
                    last_exc = e
                    delay = _jittered_backoff(attempt)
                    logger.warning(
                        f"[genai:text] transient error (attempt {attempt + 1}/{GENAI_MAX_ATTEMPTS}): {e} → sleep {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                last_exc = e
                logger.exception(f"[genai:text] non-retryable error: {e}")
                raise
            except Exception as e:
                last_exc = e
                logger.exception(f"[genai:text] unexpected error: {e}")
                raise

        raise last_exc or RuntimeError("generate_content failed after retries")

    # ============== IMAGE ==============
    async def generate_image(self, image_model_or_req: Any, contents: Optional[str] = None):
        """
        지원 형태:
          - generate_image(image_model, contents="...")  ← 문자열
          - generate_image(ContentRequest(...))          ← ContentRequest 전체
        """
        # --- 인자 정규화 ---
        if ContentRequest is not None and isinstance(image_model_or_req, ContentRequest):
            image_model = image_model_or_req.image_model
            contents = image_model_or_req.content
        elif hasattr(image_model_or_req, "content") and hasattr(image_model_or_req, "image_model") and contents is None:
            image_model = getattr(image_model_or_req, "image_model", None)
            contents = getattr(image_model_or_req, "content", None)
        else:
            image_model = image_model_or_req

        if not contents:
            raise TypeError("generate_image() requires 'contents' text")
        if not image_model:
            image_model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-preview-image-generation")

        last_exc: Optional[Exception] = None
        out_dir = _ensure_dir(IMG_OUT_DIR)

        for attempt in range(GENAI_MAX_ATTEMPTS):
            try:
                async with _genai_sem:
                    def _call():
                        return self.client.models.generate_content(
                            model=image_model,
                            contents=contents,
                            config=gatypes.GenerateContentConfig(
                                response_modalities=['TEXT', 'IMAGE']
                            ),
                        )

                    response = await asyncio.to_thread(_call)

                saved_image_paths: list[str] = []
                try:
                    parts = response.candidates[0].content.parts
                except Exception:
                    parts = []

                for part in parts:
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

            except (ServerErr, APIErr, ClientErr, httpx.HTTPError, TimeoutError, socket.timeout) as e:
                if _is_retryable_error(e):
                    last_exc = e
                    delay = _jittered_backoff(attempt)
                    logger.warning(
                        f"[genai:image] transient error (attempt {attempt + 1}/{GENAI_MAX_ATTEMPTS}): {e} → sleep {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                last_exc = e
                logger.exception(f"[genai:image] non-retryable error: {e}")
                raise
            except Exception as e:
                last_exc = e
                logger.exception(f"[genai:image] unexpected error: {e}")
                raise

        raise last_exc or RuntimeError("generate_image failed after retries")
