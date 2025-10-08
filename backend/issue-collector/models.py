from __future__ import annotations
from datetime import datetime
from typing import Any

from sqlalchemy import (
    String, Integer, Text, DateTime, Enum, JSON, UniqueConstraint, Index, Float
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
import enum


class Base(DeclarativeBase):
    pass


class TopicSource(enum.Enum):
    GDELT = "gdelt"
    REDDIT = "reddit"
    NAVER = "naver"


class TopicStatus(enum.Enum):
    NEW = "new"
    CLAIMED = "claimed"
    POSTED = "posted"
    SKIPPED = "skipped"


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Python 타입힌트는 enum/str/float/datetime 처럼 "파이썬 타입"을 사용
    source: Mapped[TopicSource] = mapped_column(
        Enum(TopicSource, name="topic_source"),  # 이름 고정(마이그레이션 안정)
        nullable=False,
        index=True,
    )

    raw_id: Mapped[str | None] = mapped_column(String(255), index=True)

    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048))

    language: Mapped[str | None] = mapped_column(String(16))
    country: Mapped[str | None] = mapped_column(String(16))
    category: Mapped[str | None] = mapped_column(String(64))
    tags: Mapped[str | None] = mapped_column(String(512))

    score: Mapped[float | None] = mapped_column(Float)

    # datetime은 파이썬의 datetime 타입으로 힌트, 컬럼은 DateTime(timezone=True) 권장
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    status: Mapped[TopicStatus] = mapped_column(
        Enum(TopicStatus, name="topic_status"),
        default=TopicStatus.NEW,          # 파이썬 기본값
        server_default=TopicStatus.NEW.value,  # DB 기본값(마이그레이션 시 유용)
        nullable=False,
        index=True,
    )

    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_topics_fingerprint"),
        Index("ix_topics_source_status_time", "source", "status", "collected_at"),
        Index("ix_topics_published_time", "published_at"),
    )

    def __repr__(self) -> str:
        return f"<Topic id={self.id} source={self.source.value} status={self.status.value}>"
