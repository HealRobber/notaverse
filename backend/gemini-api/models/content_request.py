from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional, Union

# SDK가 허용하는 Part는 {"text": "..."} / {"inline_data": ...} / {"file_data": ...} 등 dict 형태이거나,
# 간편 사용을 위해 문자열도 받게끔 합니다(나중에 text로 변환).
PartLike = Union[str, Dict[str, Any]]

class ContentMessage(BaseModel):
    role: str = "user"
    parts: List[PartLike]

    @classmethod
    def from_text(cls, text: str, role: str = "user") -> "ContentMessage":
        t = (text or "").strip()
        if not t:
            raise ValueError("empty text for ContentMessage")
        return cls(role=role, parts=[t])

class ContentRequest(BaseModel):
    model: Optional[str] = None
    image_model: Optional[str] = None
    content: List[ContentMessage] = Field(default_factory=list)

    @model_validator(mode="after")
    def set_default_text_model(self) -> "ContentRequest":
        if not self.model or self.model.strip() == "":
            self.model = "gemini-2.5-flash"
        return self

    @model_validator(mode="after")
    def set_default_image_model(self) -> "ContentRequest":
        if not self.image_model or self.image_model.strip() == "":
            self.image_model = "gemini-2.0-flash-preview-image-generation"
        return self
