from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict

class RunInitContentReq(BaseModel):
    topic: str = Field(..., min_length=1)
    photo_count: int = Field(..., ge=0, le=10)
    llm_model: Optional[str] = Field(None, description="override text LLM model")
    target_chars: Optional[int] = Field(
        None, ge=100, le=20000, description="desired post length (approx chars)"
    )

class RunInitContentResp(BaseModel):
    status: str
    result: Optional[Dict[str, Any]] = None
    detail: Optional[str] = None
