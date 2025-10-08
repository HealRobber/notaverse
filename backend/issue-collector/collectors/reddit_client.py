from __future__ import annotations
from typing import Iterable, Iterator
from datetime import datetime, timezone
import time
from loguru import logger
import praw
import prawcore

from schemas import CollectedTopic          # ← 절대 임포트 권장
from config import settings                 # ← 절대 임포트 권장

def _client() -> praw.Reddit:
    reddit = praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
        ratelimit_seconds=5,   # PRAW 내부 sleep 힌트(과도한 요청 방지)
    )
    reddit.read_only = True
    return reddit


def _iter_listing(subreddit: praw.models.Subreddit, listing: str, time_filter: str, limit: int) -> Iterator:
    listing = (listing or "top").lower()
    if listing == "hot":
        return subreddit.hot(limit=limit)
    if listing == "new":
        return subreddit.new(limit=limit)
    if listing == "rising":
        return subreddit.rising(limit=limit)
    # default: top
    return subreddit.top(time_filter=(time_filter or "day").lower(), limit=limit)


def _safe_thumbnail(thumb: str | None) -> str | None:
    if thumb and thumb.startswith("http"):
        return thumb
    return None


def fetch_reddit() -> Iterable[CollectedTopic]:
    """
    .env 예시
      REDDIT_USE_ALL=true
      REDDIT_SUBREDDITS=worldnews,news,technology,Korea
      REDDIT_LISTING=top        # hot,new,top,rising
      REDDIT_TIME_FILTER=hour   # hour,day,week,month,year,all (top에서만 의미)
      REDDIT_LIMIT=100
    """
    reddit = _client()
    use_all = bool(settings.REDDIT_USE_ALL)
    listing = (settings.REDDIT_LISTING or "top").lower()
    time_filter = (settings.REDDIT_TIME_FILTER or "day").lower()
    limit = int(settings.REDDIT_LIMIT or 50)

    subs = ["all"] if use_all else [s.strip() for s in (settings.REDDIT_SUBREDDITS or "").split(",") if s.strip()]

    for sub in subs:
        # 서브레딧 접근 예외(금지/존재X 등) 대비
        try:
            subreddit = reddit.subreddit(sub)
            posts = _iter_listing(subreddit, listing, time_filter, limit)
        except (prawcore.exceptions.Forbidden, prawcore.exceptions.NotFound) as e:
            logger.warning("Skip subreddit %s (%s)", sub, e)
            continue
        except prawcore.exceptions.PrawcoreException as e:
            logger.error("Reddit API error on subreddit %s: %s", sub, e)
            # 일시 오류 가능 → 다음 서브레딧으로 진행
            continue

        # 포스트 순회 중 개별 항목 예외 방어
        fetched = 0
        for attempt in range(2):  # 목록 단위로 한 번 재시도
            try:
                for p in posts:
                    try:
                        url = getattr(p, "url", None)
                        if not url:
                            continue
                        title = getattr(p, "title", "") or ""
                        created_utc = float(getattr(p, "created_utc", 0) or 0)
                        created = datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else None
                        score_val = getattr(p, "score", 0) or 0
                        score = float(score_val)
                        thumb = _safe_thumbnail(getattr(p, "thumbnail", None))

                        yield CollectedTopic(
                            source="reddit",
                            raw_id=getattr(p, "id", None) or url,
                            title=title[:1024],
                            summary=(getattr(p, "selftext", None) or None),
                            url=url,
                            image_url=thumb,
                            language=None,
                            country=None,
                            category=sub,
                            tags=[sub],
                            score=score,
                            published_at=created,
                            payload={
                                "subreddit": sub,
                                "permalink": f"https://reddit.com{getattr(p, 'permalink', '')}",
                                "over_18": bool(getattr(p, "over_18", False)),
                                "num_comments": int(getattr(p, "num_comments", 0) or 0),
                            },
                        )
                        fetched += 1
                    except Exception as ie:
                        # 개별 포스트만 스킵
                        logger.debug("Skip a post in %s due to: %s", sub, ie)
                break  # 정상 순회 완료 → 재시도 루프 탈출
            except prawcore.exceptions.ResponseException as e:
                # 5xx/일시적 네트워크 오류 시 짧게 대기 후 한 번 재시도
                logger.warning("Transient error on %s (attempt %d): %s", sub, attempt + 1, e)
                time.sleep(2)
                continue
            except prawcore.exceptions.RateLimitExceeded as e:
                # 레이트리밋: 권고 대기시간 반영
                sleep_for = getattr(e, "sleep_time", 5) or 5
                logger.warning("Rate limited on %s: sleeping %ss", sub, sleep_for)
                time.sleep(sleep_for)
                continue
            except prawcore.exceptions.PrawcoreException as e:
                # 기타 PRAW 코어 예외 → 서브레딧 단위로 중단
                logger.error("Stop fetching %s due to: %s", sub, e)
                break

        logger.info("Fetched %d posts from r/%s (%s/%s)", fetched, sub, listing, time_filter)
