from pydantic import BaseModel

class ContentResponse(BaseModel):
    # title: str
    body: str