# app/collectors/naver_rank_client.py
from __future__ import annotations
import requests
from loguru import logger
from bs4 import BeautifulSoup
from typing import Iterable
from schemas import CollectedTopic
from config import settings

RANKING_URL = "https://news.naver.com/main/ranking/popularDay.naver"

def _fetch_html(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NotaverseCollector/1.0)"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def fetch_naver_ranking() -> Iterable[CollectedTopic]:
    logger.info(f"fetch_naver_ranking()")
    raw = (settings.NAVER_RANKING_SECTIONS or "").strip().lower()
    if raw == "all":
        # '' = 메인(전체) 페이지 포함
        sections = ["", "100", "101", "102", "103", "104", "105"]
    else:
        sections = [s.strip() for s in raw.split(",") if s.strip()]

    # .env 제어 옵션 (문자여도 안전하게 파싱)
    try:
        max_total = int(str(getattr(settings, "NAVER_MAX_TOTAL", "0")).strip() or "0")
    except Exception:
        max_total = 0
    try:
        per_section = int(str(getattr(settings, "NAVER_MAX_PER_SECTION", "0")).strip() or "0")
    except Exception:
        per_section = 0
    dedup_by_url = str(getattr(settings, "NAVER_DEDUP_BY_URL", "true")).lower().strip() == "true"

    emitted_total = 0
    seen_urls: set[str] = set()

    # 시작 시 설정 로그(문제 추적용)
    logger.info(f"[NAVER RANK] sections={sections} max_total={max_total} per_section={per_section} dedup={dedup_by_url}")


    for sid in sections:
        # 전역 상한 도달 시 즉시 종료 (페이지 파싱도 생략)
        if max_total > 0 and emitted_total >= max_total:
            logger.info(f"[NAVER RANK] reached global cap before section parse")
            return

        url = RANKING_URL if sid == "" else f"{RANKING_URL}?sid={sid}"
        html = _fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")

        anchors = soup.select("a.list_title")
        if not anchors:
            anchors = soup.select("ol.ranking_list a")

        emitted_this_section = 0
        for a in anchors:
            # 전역/섹션 상한 즉시 체크 → 루프 깊이 진입 전 차단
            if max_total > 0 and emitted_total >= max_total:
                logger.info(f"[NAVER RANK] reached global cap mid-section")
                return
            if per_section > 0 and emitted_this_section >= per_section:
                break

            link = a.get("href") or ""
            if link and not link.startswith("http"):
                link = "https://news.naver.com" + link
            if not link:
                continue

            if dedup_by_url and link in seen_urls:
                continue
            if dedup_by_url:
                seen_urls.add(link)

            title = a.get_text(strip=True)[:1024]

            yield CollectedTopic(
                source="naver",
                raw_id=link,
                title=title,
                summary=None,
                url=link,
                image_url=None,
                language="ko",
                country="KR",
                category=None,
                tags=["랭킹" if sid == "" else f"랭킹:{sid}"],
                score=None,
                published_at=None,
                payload={"ranking_source": url},
            )

            emitted_total += 1
            emitted_this_section += 1

        logger.debug(
            "[NAVER RANK] section={}} emitted={}} total={}}",
            sid or "main", emitted_this_section, emitted_total
        )
