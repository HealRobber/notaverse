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

import log_config  # logger 설정 모듈 (사용 중)
from google import genai
from google.genai import types, errors as genai_errors
from PIL import Image

# 맨 위 import 근처에 추가
from typing import Optional, Any

try:
    # 경로는 사용하시는 위치에 맞게 조정 (예: models.content_request 또는 app.models.content_request)
    from models.content_request import ContentRequest
except Exception:
    ContentRequest = None  # 타입 체크 회피용


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
    async def generate_content(self, model_or_req: Any, contents: Optional[str] = None):
        """
        지원 형태:
          - generate_content(model, contents="...")  ← 기존 방식
          - generate_content(ContentRequest(...))    ← 새 방식
        """
        # --- 인자 정규화 ---
        if ContentRequest is not None and isinstance(model_or_req, ContentRequest):
            model = model_or_req.model
            contents = model_or_req.content
        elif hasattr(model_or_req, "content") and hasattr(model_or_req, "model") and contents is None:
            # ContentRequest duck-typing (임포트 실패 대비)
            model = getattr(model_or_req, "model", None)
            contents = getattr(model_or_req, "content", None)
        else:
            model = model_or_req  # 기존 방식
            # contents 는 두 번째 인자에서 받음

        if not contents:
            raise TypeError("generate_content() requires 'contents' text")
        if not model:
            # ContentRequest validator가 기본값을 넣지만, 안전망
            model = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")

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
          - generate_image(image_model, contents="...")  ← 기존 방식
          - generate_image(ContentRequest(...))          ← 새 방식
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

ClientErr = getattr(genai_errors, "ClientError", Exception)
ServerErr = getattr(genai_errors, "ServerError", Exception)
APIErr    = getattr(genai_errors, "APIError", Exception)

def _is_retryable_error(e: Exception) -> bool:
    """429, 5xx, 타임아웃/일시적 네트워크 오류면 True"""
    status = getattr(e, "status", None) or getattr(e, "http_status", None)
    code   = getattr(e, "code", None)

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

    # 네트워크 계열
    if isinstance(e, (TimeoutError, socket.timeout, httpx.ReadTimeout, httpx.ConnectTimeout)):
        return True

    return False