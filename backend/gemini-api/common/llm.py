from __future__ import annotations

import asyncio
import random
import logging
from typing import Optional, Any

from settings import settings  # STEP_MAX_RETRIES 등
logger = logging.getLogger(__name__)

# 타입 힌트: 문자열/ContentRequest/메시지 리스트/SDK 유사 dict 등
# (서비스 계층에서 실제 SDK 타입으로 정규화합니다)
PromptLike = Any


# ──────────────────────────────────────────────────────────────
# 공통: 지수 백오프 + 지터
# ──────────────────────────────────────────────────────────────
def jittered_backoff(attempt: int, base: float = 0.5, cap: float = 8.0) -> float:
    """
    2^n * base에 [0.5,1.0) 지터를 곱하고 cap 으로 상한을 둡니다.
    """
    sleep = min(cap, base * (2 ** attempt))
    return sleep * (0.5 + random.random() * 0.5)


# ──────────────────────────────────────────────────────────────
# 응답 텍스트 추출 유틸
# ──────────────────────────────────────────────────────────────
def to_text(resp: Any) -> str:
    """
    Google GenAI 응답 객체에서 텍스트를 최대한 안전하게 뽑아냅니다.
    다양한 SDK 버전을 고려해 방어적으로 파싱합니다.
    """
    if resp is None:
        return ""

    # 1) 최상위에 text 속성이 직접 있는 경우
    txt = getattr(resp, "text", None)
    if isinstance(txt, str) and txt.strip():
        return txt.strip()

    # 2) candidates[0].content.parts[*].text 형태
    try:
        candidates = getattr(resp, "candidates", None)
        if candidates and len(candidates) > 0:
            content = getattr(candidates[0], "content", None)
            parts = getattr(content, "parts", None)
            if parts:
                texts = []
                for p in parts:
                    t = getattr(p, "text", None)
                    if isinstance(t, str) and t.strip():
                        texts.append(t.strip())
                if texts:
                    return "\n".join(texts).strip()
    except Exception:
        pass

    # 3) 다른 필드 구조 지원 여지 (필요 시 확장)
    return ""


# ──────────────────────────────────────────────────────────────
# 텍스트 생성 리트라이
# ──────────────────────────────────────────────────────────────
async def generate_text_with_retry(
    service,
    model: str | Any,       # 문자열 모델명 또는 ContentRequest 등
    prompt: PromptLike,     # 문자열/메시지 리스트/ContentRequest/SDK 유사 dict
    *,
    max_retries: int | None = None,
) -> str:
    """
    서비스 계층(ContentGenerateService.generate_content)이
    내부에서 prompt를 Google GenAI SDK 타입으로 정규화합니다.
    여기서는 재시도/백오프만 담당합니다.
    """
    retries = max_retries if max_retries is not None else settings.STEP_MAX_RETRIES
    last_err: Optional[Exception] = None

    for attempt in range(retries):
        try:
            # 서비스는 다음 형태를 모두 지원:
            # - generate_content(model, contents="...")          (문자열)
            # - generate_content(model, contents=[...])          (메시지/SDK 유사 dict)
            # - generate_content(ContentRequest(...))            (요청 객체)
            resp = await service.generate_content(model, prompt)
            text = to_text(resp)
            if not text:
                raise RuntimeError("empty text")
            return text

        except Exception as e:
            last_err = e
            sleep = jittered_backoff(attempt)
            logger.warning(f"[genai:text] attempt {attempt+1}/{retries} failed: {e} → sleep {sleep:.2f}s")
            await asyncio.sleep(sleep)

    raise last_err or RuntimeError("generate_text_with_retry failed")


# ──────────────────────────────────────────────────────────────
# 이미지 생성 리트라이
# ──────────────────────────────────────────────────────────────
async def generate_images_with_retry(
    service,
    image_model: str | Any,   # 문자열 모델명 또는 ContentRequest 등
    prompt: PromptLike,       # 문자열/메시지 리스트/ContentRequest/SDK 유사 dict
    *,
    max_retries: int | None = None,
) -> list[str]:
    """
    서비스 계층(ContentGenerateService.generate_image)이
    내부에서 prompt를 Google GenAI SDK 타입으로 정규화하고,
    생성된 이미지를 파일로 저장한 뒤 파일 경로 리스트를 반환합니다.
    """
    retries = max_retries if max_retries is not None else settings.STEP_MAX_RETRIES
    last_err: Optional[Exception] = None

    for attempt in range(retries):
        try:
            # 서비스는 다음 형태를 모두 지원:
            # - generate_image(image_model, contents="...")       (문자열)
            # - generate_image(ContentRequest(...))               (요청 객체)
            paths = await service.generate_image(image_model, prompt)
            if not paths:
                raise RuntimeError("no images returned")
            return paths

        except Exception as e:
            last_err = e
            sleep = jittered_backoff(attempt)
            logger.warning(f"[genai:image] attempt {attempt+1}/{retries} failed: {e} → sleep {sleep:.2f}s")
            await asyncio.sleep(sleep)

    raise last_err or RuntimeError("generate_images_with_retry failed")
