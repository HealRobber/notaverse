from __future__ import annotations
import asyncio
import logging
import json
from typing import Any, Optional, List, Dict
from sqlalchemy.orm import Session

import log_config  # noqa: F401
from settings import settings
from services.db_service import get_db
from services.create_article_service import CreateArticleService
from services.content_generate_service import ContentGenerateService
from models.content_request import ContentRequest
from utils.html_parser import HtmlParser
from utils.validators import safe_parse_and_validate

from common.llm import generate_text_with_retry, generate_images_with_retry
from common.text import strip_code_fence_to_json
from common.http import robust_post_form, robust_upload_images

logger = logging.getLogger(__name__)
DEFAULT_TARGET_CHARS = 2000  # 없을 때 사용할 기본 글자 수

# ──────────────────────────────────────────────────────────────────────────────
# 내부 유틸
# ──────────────────────────────────────────────────────────────────────────────
def _parse_prompt_ids(raw: str | List[int]) -> List[str]:
    """DB Text(JSON/CSV) → 문자열 ID 리스트"""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(int(x)) for x in raw]
    s = str(raw).strip()
    if not s:
        return []
    if s.startswith("[") and s.endswith("]"):
        try:
            arr = json.loads(s)
            return [str(int(x)) for x in arr]
        except Exception:
            pass
    return [p.strip() for p in s.split(",") if p.strip()]

def _pick_model(req: ContentRequest, override: Optional[str]) -> Optional[str]:
    """요청으로 들어온 llm_model이 우선, 없으면 ContentRequest.model"""
    return override or getattr(req, "model", None)

# ──────────────────────────────────────────────────────────────────────────────
# 단일 진입점: FastAPI/CLI 공용
# ──────────────────────────────────────────────────────────────────────────────
async def run_init_content_with_db(
    db: Session,
    *,
    topic: str,
    photo_count: int = 1,
    llm_model: Optional[str] = None,
    pipeline_id: int = 1,
    target_chars: Optional[int] = None,
) -> Dict[str, Any]:
    create_article_service = CreateArticleService()
    content_generate_service = ContentGenerateService()

    pipeline = create_article_service.fetch_pipeline(db, pipeline_id)
    prompt_ids = _parse_prompt_ids(pipeline.prompt_array)

    generated_content: Optional[str] = None
    fact_checked_text: Optional[str] = None
    html_result_text: Optional[str] = None
    first_image_id: Optional[int] = None
    uploaded_results: List[dict] = []
    tags: List[str] = []
    categories: List[str] = []
    post_resp: Optional[Dict[str, Any]] = None
    step_log: Dict[str, str] = {}

    tc = target_chars or DEFAULT_TARGET_CHARS

    for pid in prompt_ids:
        prompt_obj = create_article_service.fetch_prompt(db, int(pid))
        tmpl = prompt_obj.prompt

        try:
            if pid == "1":
                # 1) 초안 생성
                req = ContentRequest(content=tmpl.format(topic=topic, target_chars=tc))
                model = _pick_model(req, llm_model)
                if not model:
                    raise RuntimeError("No LLM model specified for step 1")
                generated_content = await generate_text_with_retry(
                    content_generate_service, model, req.content
                )
                step_log[pid] = f"generated_content_len={len(generated_content)}"

            elif pid == "2":
                # 2) 사실 검증
                if not generated_content:
                    raise RuntimeError("generated_content is empty")
                req = ContentRequest(content=tmpl.format(generated_content=generated_content))
                model = _pick_model(req, llm_model)
                if not model:
                    raise RuntimeError("No LLM model specified for step 2")
                fact_checked_text = await generate_text_with_retry(
                    content_generate_service, model, req.content
                )
                step_log[pid] = f"fact_checked_text_len={len(fact_checked_text)}"

            elif pid == "3":
                # 3) 이미지 생성 → 업로드
                if not fact_checked_text:
                    raise RuntimeError("fact_checked_text is empty")
                req = ContentRequest(content=tmpl.format(n=photo_count, fact_checked_text=fact_checked_text))
                saved_image_paths = await generate_images_with_retry(
                    content_generate_service, getattr(req, "image_model", None), req.content
                )
                upload_url = f"{settings.wordpress_base}/posts/upload-image/"
                uploaded_results = await robust_upload_images(saved_image_paths, upload_url)
                step_log[pid] = f"uploaded_images={len(uploaded_results)}"

            elif pid == "4":
                # 4) 태그/카테고리 추출(JSON)
                if not fact_checked_text:
                    raise RuntimeError("fact_checked_text is empty")
                req = ContentRequest(content=tmpl.format(fact_checked_text=fact_checked_text))
                model = _pick_model(req, llm_model)
                if not model:
                    raise RuntimeError("No LLM model specified for step 4")
                raw_json_text = await generate_text_with_retry(
                    content_generate_service, model, req.content
                )
                clean = strip_code_fence_to_json(raw_json_text)
                try:
                    data = json.loads(clean)
                except Exception as e:
                    logger.warning("[4] JSON parse failed; fallback empty: %s", e)
                    data = {}
                tags = data.get("tags", []) or []
                categories = data.get("categories", []) or []
                step_log[pid] = f"tags={len(tags)}, categories={len(categories)}"

            elif pid == "5":
                # 5) HTML 구성
                if not fact_checked_text:
                    raise RuntimeError("fact_checked_text is empty")
                image_urls = [r.get("image_url") for r in uploaded_results if isinstance(r, dict) and r.get("image_url")]
                image_ids  = [r.get("image_id") for r in uploaded_results if isinstance(r, dict) and r.get("image_id")]
                first_image_id = image_ids[0] if image_ids else None

                req = ContentRequest(content=tmpl.format(fact_checked_text=fact_checked_text, image_urls=image_urls))
                model = _pick_model(req, llm_model)
                if not model:
                    raise RuntimeError("No LLM model specified for step 5")
                html_result_text = await generate_text_with_retry(
                    content_generate_service, model, req.content
                )

            elif pid == "8":

                if not html_result_text:
                    raise RuntimeError("html_result_text is empty")

                req = ContentRequest(content=tmpl.format(input_html_content=html_result_text))
                model = _pick_model(req, llm_model)
                if not model:
                    raise RuntimeError("No LLM model specified for step 8")
                extended_html_result_text = await generate_text_with_retry(
                    content_generate_service, model, req.content
                )

                parser = HtmlParser()
                parsed = safe_parse_and_validate(extended_html_result_text, parser)
                if not parsed:
                    raise RuntimeError("Parsed result invalid. Skip posting.")
                title, content = parsed

                post_data = {
                    "title": title,
                    "content": content,
                    "categories": categories,
                    "tags": tags,
                    "image_id": first_image_id,
                }
                create_url = f"{settings.wordpress_base}/posts/create-post/"
                post_resp = await robust_post_form(create_url, post_data)
                step_log[pid] = "post_done"

            else:
                step_log[pid] = "unknown_step_skipped"

        except Exception as e:
            logger.exception("[step %s] failed: %s", pid, e)
            step_log[pid] = f"error:{e}"
            # 필요시 raise로 전체 중단하도록 변경 가능

    safe_post_summary = None
    if isinstance(post_resp, dict):
        safe_post_summary = {k: post_resp.get(k) for k in ("id", "link", "slug", "status") if k in post_resp}

    return {
        "pipeline_id": pipeline_id,
        "topic": topic,
        "photo_count": photo_count,
        "llm_model": llm_model,
        "steps": step_log,
        "tags": tags,
        "categories": categories,
        "uploaded_images": len(uploaded_results),
        "post": safe_post_summary,
    }

# ──────────────────────────────────────────────────────────────────────────────
# CLI 용 래퍼(옵션): 동일 로직 재사용
# ──────────────────────────────────────────────────────────────────────────────
async def run_init_content(*, topic: str, photo_count: int = 1, llm_model: Optional[str] = None) -> Dict[str, Any]:
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        return await run_init_content_with_db(db, topic=topic, photo_count=photo_count, llm_model=llm_model)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--photo-count", type=int, default=1)
    parser.add_argument("--llm-model", type=str, default=None)
    args = parser.parse_args()
    asyncio.run(run_init_content(topic=args.topic, photo_count=args.photo_count, llm_model=args.llm_model))
