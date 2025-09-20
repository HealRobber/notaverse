from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, JSON, BigInteger, Text, TIMESTAMP, ForeignKey

from db import Base


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    func_key: Mapped[str] = mapped_column(String(128))
    cron_expr: Mapped[str] = mapped_column(String(64))
    params_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    coalesce: Mapped[bool] = mapped_column(Boolean, default=True)
    max_instances: Mapped[int] = mapped_column(Integer, default=1)
    misfire_grace: Mapped[int] = mapped_column(Integer, default=300)
    lock_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)


class JobRun(Base):
    __tablename__ = "job_runs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    scheduled_time: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    start_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    result_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
