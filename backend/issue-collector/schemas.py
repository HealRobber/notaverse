from __future__ import annotations
from pydantic import BaseModel, HttpUrl
from datetime import datetime

class CollectedTopic(BaseModel):
    source: str
    raw_id: str | None = None
    title: str
    summary: str | None = None
    url: HttpUrl
    image_url: str | None = None
    language: str | None = None
    country: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    score: float | None = None
    published_at: datetime | None = None
    payload: dict | None = None
