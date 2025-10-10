#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from typing import Optional, Dict, Callable
from threading import Event

from loguru import logger
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from config import settings
from db import SessionLocal
from models.topic import Topic, TopicStatus


class ScreeningError(Exception):
    """스크리닝 일반 오류"""


class LLMQuotaExceededError(ScreeningError):
    """LLM 토큰/쿼터 초과 → 즉시 종료 신호로 사용"""


def _load_payload(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _dump_payload(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)


class TopicService:
    """토픽(status=NEW) 처리 및 상태 업데이트 담당"""

    def fetch_oldest_new(self, session: Session) -> Optional[Topic]:
        stmt = (
            select(Topic)
            .where(Topic.status == TopicStatus.NEW)
            .order_by(func.coalesce(Topic.published_at, Topic.collected_at).asc(), Topic.id.asc())
            .limit(1)
        )
        return session.scalars(stmt).first()

    @staticmethod
    def prelength_filter(title: str, summary: Optional[str]) -> Optional[str]:
        if len((title or "").strip()) < int(getattr(settings, "MIN_TITLE_LEN", 8)):
            return "제목 길이 부족(사전필터)"
        if summary and len(summary.strip()) < int(getattr(settings, "MIN_SUMMARY_LEN", 0)):
            return "요약 길이 부족(사전필터)"
        return None

    @staticmethod
    def _update_to_skipped(session: Session, topic: Topic, reason: str, screener: dict) -> bool:
        base = _load_payload(topic.payload)
        scr = base.setdefault("screener", {})
        scr.update({
            **screener,
            "final_decision": "SKIP",
            "final_reason": reason[:400],
            "ts": int(time.time()),
        })
        res = session.execute(
            update(Topic)
            .where(Topic.id == topic.id, Topic.status == TopicStatus.NEW)
            .values(status=TopicStatus.SKIPPED, payload=_dump_payload(base))
        )
        return res.rowcount == 1

    @staticmethod
    def _update_to_claimed(session: Session, topic: Topic, screener: dict) -> bool:
        base = _load_payload(topic.payload)
        scr = base.setdefault("screener", {})
        scr.update({
            **screener,
            "final_decision": "CLAIM",
            "ts": int(time.time()),
        })
        res = session.execute(
            update(Topic)
            .where(Topic.id == topic.id, Topic.status == TopicStatus.NEW)
            .values(status=TopicStatus.CLAIMED, payload=_dump_payload(base))
        )
        return res.rowcount == 1

    @staticmethod
    def _annotate_error(session: Session, topic: Topic, stage: str, message: str) -> None:
        base = _load_payload(topic.payload)
        errs = base.setdefault("errors", [])
        errs.append({"stage": stage, "message": message[:500], "ts": int(time.time())})
        session.execute(
            update(Topic).where(Topic.id == topic.id).values(payload=_dump_payload(base))
        )

    def process_one(
        self,
        screener: Callable[[str, Optional[str]], Dict],
        sleep_between_items: float = 0.2
    ) -> Dict[str, int]:
        stats = {"processed": 0, "skipped": 0, "claimed": 0, "posted": 0, "conflict": 0}
        with SessionLocal() as session:
            topic = self.fetch_oldest_new(session)
            if not topic:
                return stats

            title = topic.title or ""
            summary = topic.summary or ""

            pre = self.prelength_filter(title, summary)
            if pre:
                screener_meta = {"score": 0, "decision": "SKIP", "reason": pre}
                ok = self._update_to_skipped(session, topic, pre, screener_meta)
                try:
                    session.commit()
                except:
                    session.rollback()
                    raise
                if ok:
                    stats["skipped"] += 1
                    stats["processed"] += 1
                    logger.info(f"[SKIPPED:사전필터] id={topic.id} | {pre}")
                else:
                    stats["conflict"] += 1
                    logger.info(f"[CONFLICT] id={topic.id} 이미 처리됨")
                time.sleep(sleep_between_items)
                return stats

            # 외부 스크리너 호출 (예: Gemini)
            try:
                result = screener(title, summary) or {}
                decision = str(result.get("decision", "SKIP")).upper()
                score = int(result.get("score", 0))
                reason = str(result.get("reason", ""))[:400]
            except LLMQuotaExceededError:
                raise
            except Exception as e:
                logger.warning(f"스크리닝 실패 id={topic.id}: {e}")
                self._annotate_error(session, topic, "screen", f"screening_error: {e}")
                try:
                    session.commit()
                except:
                    session.rollback()
                    raise
                stats["processed"] += 1
                time.sleep(sleep_between_items)
                return stats

            screener_meta = {"score": score, "decision": decision, "reason": reason}

            if decision != "CLAIM":
                ok = self._update_to_skipped(session, topic, reason or "스크리너에 의해 스킵", screener_meta)
                try:
                    session.commit()
                except:
                    session.rollback()
                    raise
                if ok:
                    stats["skipped"] += 1
                    stats["processed"] += 1
                    logger.info(f"[SKIPPED] id={topic.id} | score={score} | {reason}")
                else:
                    stats["conflict"] += 1
                    logger.info(f"[CONFLICT] id={topic.id} NEW 아님")
                time.sleep(sleep_between_items)
                return stats

            # CLAIM
            claimed_ok = self._update_to_claimed(session, topic, screener_meta)
            try:
                session.commit()
            except:
                session.rollback()
                raise
            if not claimed_ok:
                stats["conflict"] += 1
                logger.info(f"[CONFLICT] id={topic.id} 다른 작업이 먼저 처리")
                time.sleep(sleep_between_items)
                return stats

            stats["claimed"] += 1
            stats["processed"] += 1
            logger.info(f"[CLAIMED] id={topic.id} | {title[:60]}")
            time.sleep(sleep_between_items)
            return stats

    def process_loop_forever(
        self,
        screener: Callable[[str, Optional[str]], Dict],
        stop_event: Event,
        idle_min_sec: float = 2.0,
        idle_max_sec: float = 60.0,
    ) -> None:
        """
        - stop_event.set() 호출 시 안전 종료
        - LLMQuotaExceededError 발생 시 즉시 종료
        - NEW 없음: idle_min~idle_max 지수백오프
        """
        backoff = idle_min_sec
        logger.info("무한 처리 루프 시작")
        while not stop_event.is_set():
            try:
                stats = self.process_one(screener=screener, sleep_between_items=0.1)
            except LLMQuotaExceededError:
                logger.error("LLM 쿼터/토큰 한도 초과 감지. 루프 종료.")
                break

            if sum(stats.values()) == 0:
                logger.info(f"NEW 없음. {backoff:.1f}s 대기 후 재시도…")
                # 대기 중 중지 요청 확인
                stop_event.wait(backoff)
                if stop_event.is_set():
                    break
                backoff = min(backoff * 2, idle_max_sec)
            else:
                backoff = idle_min_sec

        logger.info("무한 처리 루프 종료")
