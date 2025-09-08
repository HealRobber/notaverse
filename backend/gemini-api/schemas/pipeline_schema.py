from pydantic import BaseModel
from datetime import datetime

class PipelineBase(BaseModel):
    prompt_array: str

class PipelineOut(PipelineBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}