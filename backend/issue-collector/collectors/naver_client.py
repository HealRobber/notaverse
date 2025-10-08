# app/collectors/naver_client.py
from __future__ import annotations
import json
from loguru import logger
from typing import Iterable
from urllib.parse import quote
from datetime import datetime, timedelta, timezone

import requests
from dateutil import parser as dtparse
from schemas import CollectedTopic
from config import settings


NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"

def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "notaverse-collector/1.0 (+https://notaverse.org)",
        "Accept": "application/json",
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    })
    return s

def _load_json(resp: requests.Response) -> dict:
    resp.raise_for_status()
    txt = resp.text or ""
    if not txt.strip():
        logger.warning("NAVER empty body: %s", resp.url)
        return {"items": []}
    try:
        return json.loads(txt.strip())
    except Exception as e:
        logger.error("NAVER malformed JSON: %s preview=%r url=%s", e, txt[:200], resp.url)
        return {"items": []}

def _strip_tags(text: str) -> str:
    return (text or "").replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&")

def fetch_naver_news() -> Iterable[CollectedTopic]:
    logger.info(f"fetch_naver_news()")
    queries = [q.strip() for q in settings.NAVER_NEWS_QUERIES.split(",") if q.strip()]
    display = max(1, int(settings.NAVER_DISPLAY or 20))   # 1..100
    sort = settings.NAVER_SORT or "date"

    # .env 제어 옵션
    per_limit = int(getattr(settings, "NAVER_MAX_PER_QUERY", 0) or 0)  # 0=무제한
    global_limit = int(getattr(settings, "NAVER_MAX_TOTAL", 0) or 0)   # 0=무제한
    max_age_h = int(getattr(settings, "NAVER_MAX_AGE_HOURS", 0) or 0)  # 0=무제한
    dedup_by_url = str(getattr(settings, "NAVER_DEDUP_BY_URL", "true")).lower() == "true"

    now = datetime.now(timezone.utc)
    min_dt = now - timedelta(hours=max_age_h) if max_age_h > 0 else None

    session = _new_session()
    seen_urls: set[str] = set()
    total_emitted = 0

    for q in queries:
        emitted_this_query = 0
        start = 1
        while True:
            url = f"{NAVER_NEWS_URL}?query={quote(q)}&display={display}&sort={quote(sort)}&start={start}"
            data = _load_json(session.get(url, timeout=30))
            items = data.get("items") or []
            if not items:
                break

            for it in items:
                url = it.get("originallink") or it.get("link")
                if not url:
                    continue

                if dedup_by_url:
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                title = _strip_tags(it.get("title") or "")
                summary = _strip_tags(it.get("description") or "")

                published_at = None
                pubdate = it.get("pubDate")
                if pubdate:
                    try:
                        published_at = dtparse.parse(pubdate)
                    except Exception:
                        published_at = None

                if min_dt and published_at and published_at < min_dt:
                    continue

                yield CollectedTopic(
                    source="naver",
                    raw_id=url,
                    title=title[:1024],
                    summary=summary,
                    url=url,
                    image_url=None,
                    language="ko",
                    country="KR",
                    category=None,
                    tags=[q],
                    score=None,
                    published_at=published_at,
                    payload=it,
                )

                emitted_this_query += 1
                total_emitted += 1

                if per_limit > 0 and emitted_this_query >= per_limit:
                    break
                if global_limit > 0 and total_emitted >= global_limit:
                    return

            if per_limit > 0 and emitted_this_query >= per_limit:
                break
            start += display
            if start > 1000:  # 네이버 API 한계
                break
