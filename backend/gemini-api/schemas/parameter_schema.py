from pydantic import BaseModel
from datetime import datetime

class ParameterBase(BaseModel):
    parameter: str

class ParameterCreate(ParameterBase):
    pass

class ParameterUpdate(ParameterBase):
    pass

class ParameterOut(ParameterBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}