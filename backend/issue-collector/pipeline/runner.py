# runner.py
from __future__ import annotations

from typing import Dict, Any, List
from sqlalchemy.exc import IntegrityError
from loguru import logger

from db import SessionLocal
from models import Topic, TopicSource, TopicStatus
from schemas import CollectedTopic
from collectors.gdelt_client import fetch_gdelt_hot_issues
# 필요 시 활성화:
from collectors.reddit_client import fetch_reddit
from collectors.naver_client import fetch_naver_news
from collectors.naver_rank_client import fetch_naver_ranking
from config import settings
from pipeline.dedup import make_fingerprint


def _to_source_enum(src: str) -> TopicSource:
    """문자열 소스를 TopicSource Enum으로 변환."""
    s = (src or "").lower()
    if s == "gdelt":
        return TopicSource.GDELT
    if s == "reddit":
        return TopicSource.REDDIT
    if s == "naver":
        return TopicSource.NAVER
    raise ValueError(f"Unknown source: {src}")


def _topic_to_model(item: CollectedTopic) -> Topic:
    """
    CollectedTopic(Pydantic) → Topic(SQLAlchemy ORM) 변환.
    - tags: 리스트/None → 문자열(예: "tag1,tag2") 저장 규약 유지
    """
    fp = make_fingerprint(item)
    return Topic(
        source=_to_source_enum(item.source),
        raw_id=item.raw_id,
        title=(item.title or "")[:1024],
        summary=item.summary,
        url=str(item.url),
        image_url=item.image_url,
        language=item.language,
        country=item.country,
        category=item.category,
        tags=",".join(item.tags) if item.tags else None,
        score=item.score,
        published_at=item.published_at,
        status=TopicStatus.NEW,
        fingerprint=fp,
        payload=item.payload or {},
    )


def run_pipeline() -> dict:
    """
    수집 파이프라인 실행:
      1) GDELT 핫이슈 수집 (언어/이미지/HOT_ISSUE_COUNT는 .env로 제어)
      2) (옵션) Reddit / Naver 수집
      3) DB insert (UNIQUE 제약으로 중복 무시)
    return: {"inserted": int, "duplicates": int, "total": int}
    """
    collected: List[CollectedTopic] = []

    # 1) GDELT (핫이슈; .env: GDELT_LANGUAGE / GDELT_REQUIRE_IMAGE / GDELT_HOT_ISSUE_COUNT)
    gdelt_items = list(fetch_gdelt_hot_issues())
    collected.extend(gdelt_items)

    # 2) Reddit (r/all 지원)
    if getattr(settings, "REDDIT_USE_ALL", False):
        collected.extend(list(fetch_reddit()))
    else:
        collected.extend(list(fetch_reddit()))

    # 3) Naver: 랭킹 스크래핑 vs Open API
    if getattr(settings, "NAVER_USE_RANKING_SCRAPE", False):
        collected.extend(list(fetch_naver_ranking()))
    else:
        collected.extend(list(fetch_naver_news()))

    logger.info(f"Collected raw items: {len(collected)}")

    inserted = 0
    skipped_dup = 0

    with SessionLocal() as session:
        for item in collected:
            model = _topic_to_model(item)
            session.add(model)
            try:
                session.commit()
                inserted += 1
            except IntegrityError:
                # (source, raw_id) 혹은 fingerprint UNIQUE 제약으로 중복 발생 시
                session.rollback()
                skipped_dup += 1
            except Exception as e:
                # 예기치 못한 예외는 로그 남기고 다음 아이템 진행
                session.rollback()
                logger.exception("Insert failed for URL={} error={}", item.url, e)

    logger.info(f"Inserted: {inserted}, Duplicates skipped: {skipped_dup}")
    return {"inserted": inserted, "duplicates": skipped_dup, "total": len(collected)}


if __name__ == "__main__":
    result = run_pipeline()
    logger.info("Run result: {}", result)
