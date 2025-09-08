from pydantic import BaseModel, model_validator
from typing import Optional, List

class ContentRequest(BaseModel):
    model: Optional[str] = None
    image_model: Optional[str] = None
    content: str
    keywords: List[str] = []

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