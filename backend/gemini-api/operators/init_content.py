# operators/init_content.py
from __future__ import annotations
import asyncio
import logging
import json
import os
import mimetypes
from pathlib import Path
from typing import Any, Optional, List
import httpx
import log_config  # noqa: F401
from sqlalchemy.orm import Session
from services.create_article_service import CreateArticleService
from services.db_service import get_db
from services.content_generate_service import ContentGenerateService
from models.content_request import ContentRequest
from utils.html_parser import HtmlParser
from utils.validators import safe_parse_and_validate

logger = logging.getLogger(__name__)

# ---- 환경설정 (필요 시 환경변수로 조절) ----
WORDPRESS_API_BASE = os.getenv("WORDPRESS_API_BASE", "http://wordpressapi:32552")
STEP_MAX_RETRIES = int(os.getenv("STEP_MAX_RETRIES", "3"))
STEP_MAX_BACKOFF = int(os.getenv("STEP_MAX_BACKOFF", "20"))  # 초 단위 최대 백오프

# ---------------- 공통 유틸 ----------------
def _jittered_backoff(attempt: int, max_backoff: int = STEP_MAX_BACKOFF) -> float:
    import random
    return min(2 ** attempt, max_backoff) + random.uniform(0.1, 0.9)

def to_text(raw: Any) -> str:
    """google.genai 응답 객체를 문자열로 안전 변환"""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    # 공식 클라이언트 호환
    if hasattr(raw, "text") and isinstance(getattr(raw, "text"), str):
        return raw.text
    # candidates → content.parts[*].text
    try:
        cands = getattr(raw, "candidates", None)
        if cands:
            chunks = []
            for c in cands:
                content = getattr(c, "content", None)
                if content:
                    parts = getattr(content, "parts", None)
                    if parts:
                        for p in parts:
                            t = getattr(p, "text", None)
                            if isinstance(t, str):
                                chunks.append(t)
            if chunks:
                return "\n\n".join(chunks)
    except Exception:
        pass
    # 최후의 수단
    return str(raw)

def strip_code_fence_to_json(text: str) -> str:
    """
    ```json ... ``` / ``` ... ``` 케이스 제거 후 순수 JSON 텍스트 반환
    """
    t = text.strip()
    if not t:
        return t
    if t.startswith("```"):
        # 앞쪽 ```json 또는 ``` 제거
        t = t[3:].lstrip()  # 백틱 제거 후 공백
        if t.lower().startswith("json"):
            t = t[4:].lstrip()
        # 뒤쪽 ``` 제거
        if t.endswith("```"):
            t = t[:-3]
        t = t.strip()
    return t

async def robust_post_form(url: str, data: dict, *, max_retries: int = STEP_MAX_RETRIES) -> dict:
    """
    application/x-www-form-urlencoded POST를 재시도와 함께 수행
    """
    last_err: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0)) as client:
                r = await client.post(url, data=data)
                if r.status_code == 200:
                    return r.json()
                logger.warning(f"[POST] {url} non-200 {r.status_code}: {r.text[:300]}")
        except Exception as e:
            last_err = e
            logger.warning(f"[POST] {url} failed attempt {attempt+1}/{max_retries}: {e}")
        await asyncio.sleep(_jittered_backoff(attempt))
    raise last_err or RuntimeError(f"POST failed for {url}")

async def robust_upload_images(image_paths: List[str], url: str, *, max_retries: int = STEP_MAX_RETRIES) -> List[dict]:
    """
    파일 업로드(멀티파트) 재시도
    """
    results: List[dict] = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0)) as client:
        for p in image_paths:
            full_path = os.path.abspath(p)
            # 멀티파트 filename에 디렉터리 구분자가 들어가면 서버/프록시가 싫어할 수 있어 POSIX 형태 권장
            filename_for_multipart = Path(full_path).as_posix()

            mime = mimetypes.guess_type(p)[0] or "application/octet-stream"
            logger.info(f"[POST] {filename_for_multipart} mime type: {mime}")
            last_err: Optional[Exception] = None
            for attempt in range(max_retries):
                try:
                    with open(filename_for_multipart, "rb") as f:
                        files = {"image": (filename_for_multipart, f, mime)}
                        r = await client.post(url, files=files)
                        r.raise_for_status()
                        results.append(r.json())
                        break
                except Exception as e:
                    last_err = e
                    logger.warning(f"[upload] {filename_for_multipart} failed attempt {attempt+1}/{max_retries}: {e}")
                    await asyncio.sleep(_jittered_backoff(attempt))
            else:
                raise last_err or RuntimeError(f"upload failed: {filename_for_multipart}")
    return results

# --------------- 스텝 래퍼 ---------------
async def step_generate_text(service: ContentGenerateService, model: str, prompt: str) -> str:
    """
    텍스트 생성(서비스는 응답 객체를 반환하므로 문자열로 표준화)
    """
    last_err: Optional[Exception] = None
    for attempt in range(STEP_MAX_RETRIES):
        try:
            resp = await service.generate_content(model, prompt)
            text = to_text(resp)
            if not text:
                raise RuntimeError("empty text")
            return text
        except Exception as e:
            last_err = e
            logger.warning(f"[step_generate_text] attempt {attempt+1}/{STEP_MAX_RETRIES} failed: {e}")
            await asyncio.sleep(_jittered_backoff(attempt))
    raise last_err or RuntimeError("step_generate_text failed")

async def step_generate_images(service: ContentGenerateService, image_model: Optional[str], prompt: str) -> List[str]:
    """
    이미지 생성 → (서비스가 로컬 경로 리스트 반환)
    """
    last_err: Optional[Exception] = None
    for attempt in range(STEP_MAX_RETRIES):
        try:
            paths = await service.generate_image(image_model, prompt)
            if not paths:
                raise RuntimeError("empty image list")
            # 파일 존재/크기 로그
            for p in paths:
                try:
                    sz = os.path.getsize(p)
                    logger.info(f"[image] saved: {p} ({sz} bytes)")
                except Exception as e:
                    logger.warning(f"[image] cannot stat {p}: {e}")
            return paths
        except Exception as e:
            last_err = e
            logger.warning(f"[step_generate_images] attempt {attempt+1}/{STEP_MAX_RETRIES} failed: {e}")
            await asyncio.sleep(_jittered_backoff(attempt))
    raise last_err or RuntimeError("step_generate_images failed")

# --------------- 메인 파이프라인 ---------------
async def main():
    pipeline_id = 1  # 조회할 pipeline ID
    topic = "포항시 천원주택에 관한 소개와 기대효과에 대한 전망 분석"

    wordpress_api_base = WORDPRESS_API_BASE.rstrip("/")
    create_article_service = CreateArticleService()
    content_generate_service = ContentGenerateService()

    # DB 세션 획득
    db_gen = get_db()
    db: Session = next(db_gen)

    try:
        pipeline = create_article_service.fetch_pipeline(db, pipeline_id)
        # 공백 제거해 분기 누락 방지
        prompt_ids = [p.strip() for p in pipeline.prompt_array.split(",")]

        generated_content: Optional[str] = None
        fact_checked_text: Optional[str] = None
        uploaded_results: List[dict] = []
        tags: List[str] = []
        categories: List[str] = []

        for pid in prompt_ids:
            prompt_obj = create_article_service.fetch_prompt(db, int(pid))
            logger.debug(prompt_obj)
            tmpl = prompt_obj.prompt

            if pid == "1":
                req = ContentRequest(content=tmpl.format(topic=topic))
                generated_content = await step_generate_text(content_generate_service, req.model, req.content)
                logger.info("[1] generated_content len=%s", len(generated_content))

            elif pid == "2":
                if not generated_content:
                    raise RuntimeError("[2] generated_content is empty")
                req = ContentRequest(content=tmpl.format(generated_content=generated_content))
                fact_checked_text = await step_generate_text(content_generate_service, req.model, req.content)
                logger.info("[2] fact_checked_text =%s", fact_checked_text)
                logger.info("[2] fact_checked_text len=%s", len(fact_checked_text))

            elif pid == "3":
                if not fact_checked_text:
                    raise RuntimeError("[3] fact_checked_text is empty")
                # n 값은 프롬프트 내부 지시로 반영
                req = ContentRequest(content=tmpl.format(n=1, fact_checked_text=fact_checked_text))
                saved_image_paths = await step_generate_images(content_generate_service, req.image_model, req.content)
                logger.info("[3] saved_image_paths=%s", saved_image_paths)

                upload_url = f"{wordpress_api_base}/posts/upload-image/"
                logger.info("[3] upload_url=%s", upload_url)
                uploaded_results = await robust_upload_images(saved_image_paths, upload_url)
                logger.info("[3] uploaded_results=%s", uploaded_results)

            elif pid == "4":
                if not fact_checked_text:
                    raise RuntimeError("[4] fact_checked_text is empty")
                req = ContentRequest(content=tmpl.format(fact_checked_text=fact_checked_text))
                raw_json_text = await step_generate_text(content_generate_service, req.model, req.content)

                # 코드펜스 제거 후 JSON 파싱
                clean = strip_code_fence_to_json(raw_json_text)
                try:
                    data = json.loads(clean)
                except Exception as e:
                    logger.warning("[4] JSON parse failed; fallback to empty. err=%s", e)
                    data = {}
                tags = data.get("tags", []) or []
                categories = data.get("categories", []) or []
                logger.info("[4] tags=%s categories=%s", tags, categories)

            elif pid == "5":
                if not fact_checked_text:
                    raise RuntimeError("[5] fact_checked_text is empty")

                image_urls = [r.get("image_url") for r in uploaded_results if isinstance(r, dict) and r.get("image_url")]
                image_ids = [r.get("image_id") for r in uploaded_results if isinstance(r, dict) and r.get("image_id")]
                first_image_id = image_ids[0] if image_ids else None

                req = ContentRequest(content=tmpl.format(fact_checked_text=fact_checked_text, image_urls=image_urls))
                html_result_text = await step_generate_text(content_generate_service, req.model, req.content)
                logger.info("[5] html_result_text=%s", html_result_text)
                logger.info("[5] html_result len=%s", len(html_result_text))

                parser = HtmlParser()
                parsed = safe_parse_and_validate(html_result_text, parser)
                if not parsed:
                    # 포스팅 건너뛰고 상위 로직에 '스킵' 처리만 남깁니다.
                    # 예: return {"status":"skipped","reason":"invalid parse"}
                    raise RuntimeError("Parsed result invalid. Skip posting.")
                title, content = parsed
                logger.info(f"[5] title={title}, content={content}")

                post_data = {
                    "title": title,
                    "content": content,
                    "categories": categories,
                    "tags": tags,
                    "image_id": first_image_id,
                }
                create_url = f"{wordpress_api_base}/posts/create-post/"
                resp = await robust_post_form(create_url, post_data)
                logger.info("[5] create_post resp=%s", resp)

            else:
                logger.warning(f"[pipeline] unknown step id={pid}")

    finally:
        # DB 세션 종료
        try:
            next(db_gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    asyncio.run(main())
