from __future__ import annotations
import re
import json
import logging
from typing import List, Tuple, Optional

from models.content_request import ContentRequest
from services.content_generate_service import ContentGenerateService

logger = logging.getLogger(__name__)

# 환경: 필요시 조절
MAX_INPUT_CHARS = 6000   # LLM에 넘길 텍스트 길이 제한
MAX_CATS_DEFAULT = 3
MAX_TAGS_DEFAULT = 10

# 아주 간단한 불용어 셋(한국어/영문 혼합; 필요시 확장)
STOPWORDS = {
    "그리고","그러나","하지만","또한","그러면서","이어서","있다","없다","하는","하는가","합니다","했다","된다",
    "대한","대한민국","소개","분석","정리","최신","기술","동향","오늘","이번","문제","해결","방법",
    "the","and","with","for","from","that","this","those","these","into","onto","about","your","ours","mine",
}

# ---------- 유틸 ----------
def _strip_html(html: str) -> str:
    if not html:
        return ""
    # 제거: script/style
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.I | re.S)
    # 태그 제거
    text = re.sub(r"<[^>]+>", " ", html)
    # 엔티티/공백 정리
    text = re.sub(r"&[a-zA-Z#0-9]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _top_keywords(text: str, k: int = 10) -> List[str]:
    if not text:
        return []
    # 한글/영문 토큰 추출
    toks = re.findall(r"[가-힣]{2,}|[A-Za-z][A-Za-z0-9_-]{2,}", text)
    freq = {}
    for t in toks:
        t_norm = t.lower()
        if len(t_norm) < 2:
            continue
        if t_norm in STOPWORDS:
            continue
        # 숫자/순번처럼 의미 적은 토큰 제외
        if re.fullmatch(r"\d+", t_norm):
            continue
        freq[t_norm] = freq.get(t_norm, 0) + 1
    # 상위 k개
    return [w for w, _ in sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:k]]

def _dedupe_preserve(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for s in seq:
        s = s.strip()
        if not s or s.lower() in seen:
            continue
        seen.add(s.lower())
        out.append(s)
    return out

def _safe_json(text: str) -> Optional[dict]:
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = t[3:].lstrip()
        if t.lower().startswith("json"):
            t = t[4:].lstrip()
        if t.endswith("```"):
            t = t[:-3]
        t = t.strip()
    try:
        return json.loads(t)
    except Exception:
        # 키 무따옴표 보정(간단)
        t2 = re.sub(r"(\w+)\s*:", r'"\1":', t)
        try:
            return json.loads(t2)
        except Exception:
            return None

# ---------- LLM 프롬프트 ----------
def _taxonomy_prompt(title: str, plain_text: str, seed_topic: Optional[str], max_cats: int, max_tags: int) -> str:
    return (
        "당신은 워드프레스 블로그의 분류/태그 전문가입니다.\n"
        "아래 글의 제목과 본문을 보고 **카테고리(categorIES)와 태그(tags)**를 한국어로 선정하세요.\n"
        "- 카테고리는 상위 개념 1~{mc}개 (짧고 포괄적)\n"
        "- 태그는 5~{mt}개 (핵심 키워드, 제품/인물/기술명 포함)\n"
        "- 일반어(예: '분석','정리','최신')는 제외\n"
        "- 출력은 JSON만. 예: {\"categories\":[\"AI\", \"챗GPT\"], \"tags\":[\"GPT 스토어\",\"맞춤형 GPT\"]}\n"
        + ("- 참고 시드 토픽: " + seed_topic + "\n" if seed_topic else "")
        + "\n"
        f"# 제목\n{title}\n\n"
        f"# 본문(일부)\n{plain_text[:MAX_INPUT_CHARS]}\n"
    ).format(mc=max_cats, mt=max_tags)

# ---------- 공개 API ----------
def extract_taxonomy(
    title: str,
    content_html: str,
    seed_topic: Optional[str] = None,
    max_categories: int = MAX_CATS_DEFAULT,
    max_tags: int = MAX_TAGS_DEFAULT,
) -> Tuple[List[str], List[str]]:
    """
    1) LLM으로 카테고리/태그 추출(JSON)
    2) 실패 시 휴리스틱으로 폴백
    반환: (categories(list[str]), tags(list[str]))
    """
    # 1) LLM 시도
    plain = _strip_html(content_html)
    prompt = _taxonomy_prompt(title, plain, seed_topic, max_categories, max_tags)
    try:
        svc = ContentGenerateService()
        req = ContentRequest(content=prompt)  # model 기본값 validator
        import asyncio
        resp = asyncio.run(svc.generate_content(req))  # generate_content(ContentRequest) 지원
        # 응답 텍스트 추출
        txt = ""
        try:
            # candidates parts 우선
            parts = resp.candidates[0].content.parts
            tmp = []
            for p in parts:
                t = getattr(p, "text", None)
                if t:
                    tmp.append(t)
            if tmp:
                txt = "\n".join(tmp)
        except Exception:
            t = getattr(resp, "text", None)
            if isinstance(t, str):
                txt = t
        data = _safe_json(txt) or {}
        cats = data.get("categories") or []
        tags = data.get("tags") or []
        cats = _dedupe_preserve([str(x) for x in cats])[:max_categories]
        tags = _dedupe_preserve([str(x) for x in tags])[:max_tags]
        if cats or tags:
            return cats, tags
    except Exception as e:
        logger.warning("[taxonomy] LLM extraction failed: %s", e)

    # 2) 휴리스틱 폴백
    kw = _top_keywords(plain, k=max(max_tags, 8))
    # 간단 카테고리: 제목/시드에서 핵심 1~2개
    title_kw = _top_keywords(title, k=3)
    seed_kw = _top_keywords(seed_topic or "", k=2)
    cats = _dedupe_preserve((title_kw + seed_kw)[:max_categories]) or ["일반"]
    tags = _dedupe_preserve(kw[:max_tags]) or ["블로그", "기사"]
    return cats, tags
