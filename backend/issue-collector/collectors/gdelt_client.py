# collectors/gdelt_client.py
from __future__ import annotations
from typing import Iterable, List, Tuple
import json
import re
from collections import Counter
from urllib.parse import urlparse

from loguru import logger
import requests
from dateutil import parser as dtparse

from schemas import CollectedTopic
from config import settings

BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

# ──────────────────────────────────────────────────────────────────────────────
# 기본값 / 상수
# ──────────────────────────────────────────────────────────────────────────────
MIN_QUERY_LEN = 3
DEFAULT_QUERY = '(news OR politics OR economy OR technology OR sports OR entertainment OR business OR world)'
DEFAULT_TIMESPAN = '3h'
DEFAULT_MAXRECORDS = 200
DEFAULT_HOT_ISSUES = 10
DEFAULT_LANG = None            # 필터 미적용
DEFAULT_REQUIRE_IMAGE = False

STOPWORDS = {
    # 영어 불용어/미디어명
    "the","a","an","and","or","of","to","in","on","for","with","at","by","from","as",
    "is","are","was","were","be","been","being","that","this","these","those","it","its",
    "but","not","over","after","amid","vs","into","about","more","new","latest",
    "breaking","update","live","today","yesterday","tomorrow",
    "reuters","ap","afp","bbc","cnn","nytimes","bloomberg","guardian","washington","post","times",
}
TOKEN_PATTERN = re.compile(r"[A-Za-z가-힣0-9]+")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")

# ──────────────────────────────────────────────────────────────────────────────
# HTTP / JSON
# ──────────────────────────────────────────────────────────────────────────────
def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "notaverse-collector/1.0 (+https://notaverse.org)",
        "Accept": "application/json",
    })
    return s

def _load_json(resp: requests.Response) -> dict:
    resp.raise_for_status()
    ctype = (resp.headers.get("Content-Type") or "").lower()
    text = resp.text or ""
    logger.debug("GDELT resp: status={} len={} ctype={} url={}",
                 resp.status_code, len(text), ctype, resp.url)

    if not text.strip():
        return {"articles": []}

    if "json" in ctype:
        try:
            return resp.json()
        except json.JSONDecodeError:
            pass

    if "too short or too long" in text.lower():
        logger.error("GDELT query rejected as too short/long. url={}", resp.url)
        return {"articles": []}

    try:
        return json.loads(text.strip())
    except Exception:
        return {"articles": []}

def _query_once(session: requests.Session, query: str, timespan: str, maxrecords: int) -> list[dict]:
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "sort": "DateDesc",
        "timespan": timespan,
        "maxrecords": str(maxrecords),
    }
    r = session.get(BASE, params=params, timeout=30)
    data = _load_json(r)
    return data.get("articles") or []

# ──────────────────────────────────────────────────────────────────────────────
# 텍스트/필터 유틸
# ──────────────────────────────────────────────────────────────────────────────
def _sanitize_query(raw: str | None) -> str:
    if not raw:
        return DEFAULT_QUERY
    q = (raw or "").strip()
    if q in {"*", '""', "''"}:
        return DEFAULT_QUERY
    core = q.replace('"', "").replace("'", "")
    if len(core) < MIN_QUERY_LEN:
        return DEFAULT_QUERY
    return q

def _has_image(a: dict) -> bool:
    img = (a.get("socialimage") or "").strip()
    if img.startswith("http"):
        return True
    u = (a.get("url") or "").strip().lower()
    return u.endswith(IMAGE_EXTS)

def _lang_is(a: dict, lang_name: str | None) -> bool:
    if not lang_name:
        return True
    return (a.get("language") or "").strip().lower() == lang_name.strip().lower()

def _tokenize(text: str) -> List[str]:
    tokens = [t.lower() for t in TOKEN_PATTERN.findall(text)]
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]

def _ngrams(tokens: List[str], n: int) -> List[Tuple[str, ...]]:
    return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]

def _extract_issue_candidates(titles: List[str]) -> List[Tuple[str, int]]:
    counter = Counter()
    for ttl in titles:
        toks = _tokenize(ttl)
        for g in _ngrams(toks, 2):
            counter[g] += 1
        for g in _ngrams(toks, 3):
            counter[g] += 1

    def ok(gram: Tuple[str, ...]) -> bool:
        if any(t in STOPWORDS for t in gram):
            return False
        joined = " ".join(gram)
        if re.fullmatch(r"\d+( \d+)*", joined):
            return False
        return True

    return [(" ".join(g), c) for g, c in counter.most_common(200) if ok(g)]

def _pick_representatives(issues: List[Tuple[str, int]], articles: List[dict], limit: int) -> List[Tuple[str, dict, int]]:
    def _parse_dt(a: dict):
        sd = a.get("seendate") or a.get("publishDate") or a.get("date")
        try:
            return dtparse.parse(sd) if sd else None
        except Exception:
            return None

    reps: List[Tuple[str, dict, int]] = []
    used_urls, used_domains = set(), set()
    sorted_articles = sorted(articles, key=lambda a: (_parse_dt(a) or 0), reverse=True)

    for phrase, score in issues:
        phrase_lc = phrase.lower()
        chosen = None
        for a in sorted_articles:
            ttl = (a.get("title") or "").lower()
            if phrase_lc in ttl:
                url = a.get("url")
                if not url or url in used_urls:
                    continue
                domain = urlparse(url).netloc
                if domain not in used_domains:
                    chosen = a
                    used_domains.add(domain)
                    break
                if chosen is None:
                    chosen = a
        if chosen:
            used_urls.add(chosen.get("url"))
            reps.append((phrase, chosen, score))
        if len(reps) >= limit:
            break
    return reps

def _as_topic(a: dict, extra_tags: List[str] | None = None, score: int | None = None) -> CollectedTopic:
    url = a.get("url") or a.get("sourceurl") or "about:blank"
    title = a.get("title") or ""
    summary = a.get("sourceCommonName")
    image = a.get("socialimage")
    lang = a.get("language")
    country = a.get("sourceCountry")
    published_at = None
    seendate = a.get("seendate") or a.get("publishDate") or a.get("date")
    if seendate:
        try:
            published_at = dtparse.parse(seendate)
        except Exception:
            published_at = None

    return CollectedTopic(
        source="gdelt",
        raw_id=url,
        title=title[:1024],
        summary=summary,
        url=url,
        image_url=image,
        language=lang,
        country=country,
        category=None,
        tags=extra_tags or None,
        score=score,
        published_at=published_at,
        payload=a,
    )

# ──────────────────────────────────────────────────────────────────────────────
# 엔트리포인트 (.env 기반)
# ──────────────────────────────────────────────────────────────────────────────
def fetch_gdelt_hot_issues() -> Iterable[CollectedTopic]:
    """
    .env 설정을 읽어서 핫이슈 기사 1건씩 반환
    (언어/이미지/HOT_ISSUE_COUNT/쿼리/기간/레코드)
    """
    s = _new_session()

    query = _sanitize_query(getattr(settings, "GDELT_QUERY", DEFAULT_QUERY))
    timespan = getattr(settings, "GDELT_TIMESPAN", DEFAULT_TIMESPAN) or DEFAULT_TIMESPAN
    maxrecords = int(getattr(settings, "GDELT_MAX_RECORDS", DEFAULT_MAXRECORDS) or DEFAULT_MAXRECORDS)

    lang = getattr(settings, "GDELT_LANGUAGE", DEFAULT_LANG) or DEFAULT_LANG
    require_image = str(getattr(settings, "GDELT_REQUIRE_IMAGE", DEFAULT_REQUIRE_IMAGE)).lower() == "true"
    issue_count = int(getattr(settings, "GDELT_HOT_ISSUE_COUNT", DEFAULT_HOT_ISSUES) or DEFAULT_HOT_ISSUES)

    articles = _query_once(s, query, timespan, maxrecords)
    if not articles:
        return

    # 1) 필터 (언어/이미지/제목)
    filtered = []
    for a in articles:
        if not _lang_is(a, lang):
            continue
        if require_image and not _has_image(a):
            continue
        if not (a.get("title") or "").strip():
            continue
        filtered.append(a)
    if not filtered:
        return

    # 2) 이슈 후보 추출 → 3) 대표 기사 선택
    titles = [a.get("title") or "" for a in filtered]
    issues = _extract_issue_candidates(titles)
    reps = _pick_representatives(issues, filtered, issue_count) if issues else []

    if reps:
        for phrase, a, score in reps:
            yield _as_topic(a, extra_tags=[phrase], score=score)
        return

    # 후보가 없으면 최신 N건
    for a in filtered[:issue_count]:
        yield _as_topic(a)
