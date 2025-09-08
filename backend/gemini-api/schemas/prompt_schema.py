from pydantic import BaseModel
from datetime import datetime

class PromptBase(BaseModel):
    prompt: str

class PromptCreate(PromptBase):
    pass

class PromptUpdate(PromptBase):
    pass

class PromptOut(PromptBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}