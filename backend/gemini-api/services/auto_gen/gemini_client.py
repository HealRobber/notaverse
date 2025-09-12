from __future__ import annotations

import os
import re
import json
import asyncio
import logging
from typing import List, Tuple, Optional

from db import SessionLocal
from models.pipeline import Pipeline
from models.prompt import Prompt
from services.content_generate_service import ContentGenerateService  # ← 사용자 제공 서비스
from models.content_request import ContentRequest

logger = logging.getLogger(__name__)

# 환경변수로 모델/이미지개수 조정
TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")
IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "imagen-3.0-generate-001")
IMAGE_COUNT = int(os.getenv("GEN_IMAGE_COUNT", "2"))  # 1~3 권장

_service = ContentGenerateService()


# ----------------------------
# 내부 유틸
# ----------------------------
def _strip_code_fences(s: str) -> str:
    """```json ... ``` 같은 펜스를 제거"""
    if s is None:
        return ""
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _first_text_from_response(resp) -> str:
    """
    google.genai 응답에서 첫 텍스트를 안전하게 추출
    """
    try:
        # 후보 1: candidates[0].content.parts[*].text
        parts = resp.candidates[0].content.parts
        texts = []
        for p in parts:
            t = getattr(p, "text", None)
            if t:
                texts.append(t)
        if texts:
            return "\n".join(texts).strip()
    except Exception:
        pass

    # 후보 2: resp.text (라이브러리 버전에 따라 제공되기도 함)
    t = getattr(resp, "text", None)
    if isinstance(t, str) and t.strip():
        return t.strip()

    logger.warning("[gemini_client] text not found in response; returning empty string")
    return ""


def _json_or_none(s: str) -> Optional[dict]:
    """문자열을 JSON으로 파싱 (코드펜스 제거 및 관대한 파싱)"""
    s = _strip_code_fences(s)
    try:
        return json.loads(s)
    except Exception:
        # 흔한 실수: 키에 따옴표 없음 → 간이 보정
        s2 = re.sub(r"(\w+)\s*:", r'"\1":', s)
        try:
            return json.loads(s2)
        except Exception:
            return None


def _ensure_html(s: str) -> str:
    """생성 결과가 순수 텍스트면 간단히 HTML로 감싸기"""
    if "<" in s and ">" in s:
        return s
    # 단락 분리
    paras = [x.strip() for x in s.split("\n") if x.strip()]
    if not paras:
        return "<p></p>"
    return "<p>" + "</p>\n<p>".join(paras) + "</p>"


def _load_pipeline_prompts(pipeline_id: int) -> List[str]:
    """pipelines.prompt_array => prompts.prompt 로 해석"""
    with SessionLocal() as db:
        pipeline = db.get(Pipeline, pipeline_id)
        if not pipeline or not (pipeline.prompt_array or "").strip():
            return []
        try:
            ids = [int(x.strip()) for x in pipeline.prompt_array.split(",") if x.strip()]
        except Exception:
            ids = []
        if not ids:
            return []
        rows = (
            db.query(Prompt)
            .filter(Prompt.id.in_(ids))
            .order_by(Prompt.id.asc())
            .all()
        )
        return [r.prompt for r in rows if r and (r.prompt or "").strip()]


def _render_pipeline_prompt(base_context: str, prompt_texts: List[str]) -> str:
    """
    프롬프트 배열을 하나의 지시문으로 합침.
    - {planned_title}, {outline} 플레이스홀더만 치환 (그 외는 원문 유지)
    """
    merged = [base_context, "\n\n### Pipeline Steps"]
    for i, p in enumerate(prompt_texts, 1):
        merged.append(f"\n[Step {i}]\n{p}")
    merged.append(
        "\n\n### Output Requirements\n"
        "- 결과는 **HTML 본문**만 출력(마크다운 금지, 코드펜스 금지).\n"
        "- 한국어로 작성.\n"
        "- <h1>는 제목 1개, 그 아래 <h2>/<h3>로 구조화.\n"
        "- 표가 필요하면 <table> 사용(간결하게).\n"
        "- 출처/참조가 있으면 마지막에 <section id='refs'>로 표시(선택).\n"
    )
    return "\n".join(merged)


def _image_prompt(planned_title: str, outline: str) -> str:
    """
    이미지 생성용 프롬프트. 모델 특성을 몰라도 좋은 보편 지시문.
    """
    return (
        "다음 블로그 글과 어울리는 표지형/삽화 이미지를 생성하세요.\n"
        f"- 제목: {planned_title}\n"
        f"- 개요:\n{outline}\n"
        f"- 필요한 이미지 수: {IMAGE_COUNT}장\n"
        "- 글과 직접 맞물리는 상징적/설명적 장면을 고해상도로 제작.\n"
        "- 사진풍 또는 일러스트풍 중 글 톤에 맞게 자연스러운 색감.\n"
        "- 텍스트/워터마크/로고 절대삽입금지.\n"
    )


def _run(coro):
    """
    동기 컨텍스트에서 안전하게 코루틴 실행.
    (worker/scheduler는 비동기 루프를 사용하지 않으므로 asyncio.run 사용)
    """
    return asyncio.run(coro)


# ----------------------------
# 공개 API
# ----------------------------
def generate_outline_title(
    series_title: str,
    seed_topic: str,
    recent_summaries: List[str],
    next_episode_no: int
) -> Tuple[str, str]:
    """
    반환: (outline, planned_title)
    """
    sys = (
        "당신은 블로그 연재 기획자입니다. 아래 정보를 읽고 **다음 회차**의 제목과 개요를 제안하십시오.\n"
        "- 시리즈 제목과 시드 토픽을 고려하되, 중복 주제는 피하고 흐름이 이어지도록 하세요.\n"
        "- 톤: 명확하고 간결한 한국어.\n"
        "- 출력은 JSON 객체로만 반환하세요. 키: title, outline\n"
        "  - title: 60자 이내의 매력적 한국어 제목\n"
        "  - outline: 소제목/핵심포인트 5~7개(불릿 텍스트)\n"
    )
    user = {
        "series_title": series_title,
        "seed_topic": seed_topic,
        "next_episode_no": next_episode_no,
        "recent_summaries": recent_summaries or [],
    }
    prompt = (
        f"{sys}\n\n"
        f"# 입력\n{json.dumps(user, ensure_ascii=False, indent=2)}\n\n"
        "# 출력 형식(예)\n"
        '{"title":"...", "outline":"- 포인트1\\n- 포인트2\\n- 포인트3"}\n'
    )

    resp = _run(_service.generate_content(TEXT_MODEL, contents=prompt))
    text = _first_text_from_response(resp)
    data = _json_or_none(text) or {}

    title = (data.get("title") or f"{series_title} #{next_episode_no}: {seed_topic}").strip()
    outline = (data.get("outline") or "- 개요 항목1\n- 개요 항목2\n- 개요 항목3").strip()
    return outline, title


def generate_content_and_images(
    planned_title: str,
    outline: str,
    pipeline_id: int
) -> Tuple[str, List[str]]:
    """
    반환: (content_html, image_paths, tag_ids, category_ids)
    - tag_ids / category_ids 는 WordPress 쪽에서 매핑하기 전이므로 기본 [] 반환
    """
    # 1) 파이프라인 프롬프트 적재
    prompt_texts = _load_pipeline_prompts(pipeline_id)
    base_context = (
        f"아래 제목과 개요를 바탕으로 고품질 블로그 글을 작성하세요.\n"
        f"- 제목: {planned_title}\n"
        f"- 개요:\n{outline}\n"
        "- 독자는 일반 기술/트렌드에 관심이 있는 성인 독자입니다.\n"
        "- 과장/허위 금지, 근거 기반으로 서술.\n"
        "- 불필요한 서론 길게 금지, 핵심부터 전달.\n"
    )
    full_prompt = _render_pipeline_prompt(
        base_context=base_context,
        prompt_texts=[p.replace("{planned_title}", planned_title).replace("{outline}", outline) for p in prompt_texts]
    )

    # 2) 본문 생성
    resp = _run(_service.generate_content(ContentRequest(content=full_prompt)))
    text = _first_text_from_response(resp)
    content_html = _ensure_html(text)

    logger.info(f"[gemini_client] text : {text}")

    # 3) 이미지 생성
    img_prompt = _image_prompt(planned_title, outline)
    image_paths = _run(_service.generate_image(ContentRequest(content=img_prompt))) or []

    return content_html, image_paths
