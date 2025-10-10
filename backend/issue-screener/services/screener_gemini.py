#!/usr/bin/env python3
from __future__ import annotations
import json
from typing import Optional, Dict
import re
import requests
from loguru import logger
from config import settings
from db import SessionLocal
from services.prompt_service import PromptService
from services.topic_service import LLMQuotaExceededError

# ─────────────────────────────────────────────────────────────
# 설정 기본값 (환경변수/설정 없으면 안전 기본값 사용)
# ─────────────────────────────────────────────────────────────
DEFAULT_TEXT_MODEL = getattr(settings, "GEMINI_TEXT_MODEL", None) or getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
ENDPOINT = (getattr(settings, "GEMINI_API_BASE", "http://geminiapi:32553/gemini").rstrip("/")) + "/generate-content/"
TIMEOUT = int(getattr(settings, "GEMINI_TIMEOUT", 20))
API_KEY = getattr(settings, "GEMINI_API_KEY", None)  # 필요 없으면 None

# DB에서 가져올 스크리닝 프롬프트 선택 (없으면 최신 1건 사용)
SCREEN_PROMPT_ID = getattr(settings, "SCREEN_PROMPT_ID", 21)  # int 또는 None


# ─────────────────────────────────────────────────────────────
# HTTP 헤더
# ─────────────────────────────────────────────────────────────
def _headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["Authorization"] = f"Bearer {API_KEY}"
    return h


# ─────────────────────────────────────────────────────────────
# 프롬프트 로딩 & 렌더링
# - 템플릿은 DB에 저장: {{title}}, {{summary}} 플레이스홀더 권장
# - content/body/prompt/text 중 존재하는 필드를 컨텐츠로 사용(유연 처리)
# ─────────────────────────────────────────────────────────────
def _extract_prompt_text(prompt_obj) -> Optional[str]:
    # Prompt 모델의 속성명이 프로젝트마다 다를 수 있으니 방어적으로 처리
    for attr in ("content", "body", "prompt", "text"):
        if hasattr(prompt_obj, attr):
            val = getattr(prompt_obj, attr)
            if isinstance(val, str) and val.strip():
                return val
    return None


def _render_template(tmpl: str, title: str, summary: Optional[str]) -> str:
    """Simple placeholder replacement: {title}, {summary}"""
    rendered = tmpl.replace("{title}", (title or "").strip())
    rendered = rendered.replace("{summary}", ((summary or "").strip() or "(no summary)"))

    # If the template doesn’t include placeholders, add minimal context in English.
    if "{title}" not in tmpl and "{summary}" not in tmpl:
        rendered = (
            f"{rendered}\n\n"
            f"Title: {(title or '').strip()}\n"
            f"Summary: {((summary or '').strip() or '(no summary)')}"
        )

    return rendered



def _load_screening_prompt() -> str:
    """DB에서 스크리닝용 프롬프트 텍스트 로드."""
    ps = PromptService()
    with SessionLocal() as db:
        if SCREEN_PROMPT_ID:
            prom = ps.get_prompt_by_id(db, int(SCREEN_PROMPT_ID))
            if not prom:
                raise RuntimeError(f"[Prompt] SCREEN_PROMPT_ID={SCREEN_PROMPT_ID} 를 찾을 수 없습니다.")
        else:
            prompts = ps.get_prompts(db)
            if not prompts:
                raise RuntimeError("[Prompt] 등록된 프롬프트가 없습니다.")
            prom = prompts[0]  # 최신 1건 (id DESC)

    text = _extract_prompt_text(prom)
    if not text:
        raise RuntimeError("[Prompt] 프롬프트 본문(content/body/prompt/text)이 비어있습니다.")
    return text

def _extract_json_from_text(text: str) -> dict:
    """
    - ```json ... ``` 같은 코드펜스 제거
    - 텍스트 중 첫 { 부터 마지막 } 까지 잘라 JSON 파싱
    - 실패하면 예외 발생
    """
    if not text:
        raise RuntimeError("empty response body")

    # 1) 코드펜스 제거 (앞뒤 공백 포함)
    # ```json\n ... \n``` 또는 ``` ... ``` 패턴 제거
    fenced = re.compile(r"^\s*```[a-zA-Z]*\s*([\s\S]*?)\s*```", re.MULTILINE)
    m = fenced.match(text)
    if m:
        text = m.group(1).strip()

    # 2) 혹시 또 남은 백틱/마크다운성이 있으면 정리
    text = text.strip()

    # 3) 첫 { 와 마지막 } 기준으로 슬라이스
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"no JSON object found in body: {text[:200]}")

    candidate = text[start:end+1].strip()

    # 4) 실제 파싱
    return json.loads(candidate)


# ─────────────────────────────────────────────────────────────
# Gemini 스크리너
# 반환: {"score": int, "decision": "CLAIM"|"SKIP", "reason": str}
# ─────────────────────────────────────────────────────────────
def gemini_screener(title: str, summary: Optional[str]) -> dict:
    # 1) 프롬프트 로드 & 렌더링
    tmpl = _load_screening_prompt()
    prompt = _render_template(tmpl, title=title, summary=summary)
    logger.info(f"[screener_gemini] prompt: {prompt}")

    # 2) 요청 바디 구성 (다른 서비스의 generate-content 규격)
    req_body = {
        "model": DEFAULT_TEXT_MODEL,  # 비워도 서버의 validator가 기본값 채워주지만 명시
        "content": [
            {"role": "user", "parts": [prompt]}
        ]
    }

    # 3) 호출
    try:
        r = requests.post(ENDPOINT, headers=_headers(), json=req_body, timeout=TIMEOUT)
    except requests.RequestException as e:
        logger.error(f"[GeminiAPI] 연결 오류: {e}")
        raise

    # 4) 쿼터/레이트 리밋 탐지
    if r.status_code == 429:
        logger.warning("[GeminiAPI] 429 Too Many Requests (quota/token limit)")
        raise LLMQuotaExceededError("quota/token exceeded")

    if not (200 <= r.status_code < 300):
        msg = f"[GeminiAPI] HTTP {r.status_code} {r.text[:300]}"
        logger.error(msg)
        raise RuntimeError(msg)

    # 5) 응답 파싱 (ContentResponse: body)
    try:
        data = r.json()
    except Exception:
        data = {"body": r.text}

    body_text = ""
    if isinstance(data, dict) and isinstance(data.get("body"), str):
        body_text = data["body"].strip()
    else:
        raise RuntimeError(f"[GeminiAPI] invalid response schema: {str(data)[:300]}")

    low = body_text.lower()
    if any(k in low for k in ["quota", "rate limit", "exceeded", "token limit", "billing", "overuse"]):
        logger.warning("[GeminiAPI] 본문에서 quota/limit 관련 키워드 감지")
        raise LLMQuotaExceededError("quota/token exceeded (body hint)")

    # 6) LLM이 출력한 JSON 파싱
    try:
        parsed = _extract_json_from_text(body_text)
    except Exception as e:
        raise RuntimeError(f"[GeminiAPI] body JSON parse error: {e} | body={body_text[:300]}")

    # 7) 정규화 & 리턴
    score = int(parsed.get("score", 0))
    decision = str(parsed.get("decision", "SKIP")).strip().upper()
    if decision not in ("CLAIM", "SKIP"):
        decision = "SKIP"
    reason = str(parsed.get("reason", "")).strip()[:400]

    result = {"score": score, "decision": decision, "reason": reason}
    logger.debug(f"[GeminiAPI] screener result: {result}")
    return result
