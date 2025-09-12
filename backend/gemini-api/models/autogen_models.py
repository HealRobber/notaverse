from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import String, Text, Integer, BigInteger, DateTime, Enum, JSON, ForeignKey, Index, UniqueConstraint, func
from datetime import datetime
from .enums import SeriesStatus, EpisodeStatus, JobType, JobStatus
from db import Base

class Image(Base):
    __tablename__ = "images"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_url: Mapped[str] = mapped_column(String(255), nullable=False)
    image_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category_ids: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    tag_ids: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    featured_media_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    series_id: Mapped[int | None] = mapped_column(ForeignKey("series.id"))
    episode_no: Mapped[int | None] = mapped_column(Integer)

    series: Mapped["Series"] = relationship(back_populates="posts")

Index("idx_posts_series", Post.series_id, Post.episode_no)

class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

class Series(Base):
    __tablename__ = "series"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    seed_topic: Mapped[str] = mapped_column(String(255), nullable=False)
    pipeline_id: Mapped[int] = mapped_column(ForeignKey("pipelines.id"), nullable=False)
    cadence: Mapped[str] = mapped_column(String(64), nullable=False)
    next_run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[SeriesStatus] = mapped_column(Enum(SeriesStatus), default=SeriesStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    topic: Mapped["Topic"] = relationship()
    pipeline: Mapped["Pipeline"] = relationship()
    episodes: Mapped[list["SeriesEpisode"]] = relationship(back_populates="series", cascade="all, delete-orphan")
    posts: Mapped[list["Post"]] = relationship(back_populates="series")

class SeriesEpisode(Base):
    __tablename__ = "series_episodes"
    __table_args__ = (UniqueConstraint("series_id", "episode_no", name="uk_series_episode"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), nullable=False)
    episode_no: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_title: Mapped[str] = mapped_column(String(255), nullable=False)
    planned_outline: Mapped[str | None] = mapped_column(Text)
    post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id"))
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[EpisodeStatus] = mapped_column(Enum(EpisodeStatus), default=EpisodeStatus.planned)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    series: Mapped["Series"] = relationship(back_populates="episodes")
    post: Mapped["Post"] = relationship()

class ContentJob(Base):
    __tablename__ = "content_jobs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    available_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

Index("idx_status_time", ContentJob.status, ContentJob.available_at, ContentJob.scheduled_at)
