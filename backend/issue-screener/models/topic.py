from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Optional
from models.base import Base
import enum

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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[TopicSource] = mapped_column(
        Enum(TopicSource, name="topic_source"),  # 이름 고정(마이그레이션 안정)
        nullable=False,
        index=True,
    )
    raw_id: Mapped[Optional[str]] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text())
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(2048))
    language: Mapped[Optional[str]] = mapped_column(String(16))
    country: Mapped[Optional[str]] = mapped_column(String(16))
    category: Mapped[Optional[str]] = mapped_column(String(64))
    tags: Mapped[Optional[str]] = mapped_column(String(512))
    score: Mapped[Optional[float]] = mapped_column(Float(asdecimal=False))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    status: Mapped[TopicStatus] = mapped_column(
        Enum(TopicStatus, name="topic_status"),
        default=TopicStatus.NEW,  # 파이썬 기본값
        server_default=TopicStatus.NEW.value,  # DB 기본값(마이그레이션 시 유용)
        nullable=False,
        index=True,
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    # DB는 LONGTEXT + CHECK(json_valid(payload))
    payload: Mapped[Optional[str]] = mapped_column(Text(collation="utf8mb4_bin"))
