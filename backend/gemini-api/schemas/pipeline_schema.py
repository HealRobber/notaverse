# schemas/pipeline_schema.py
from pydantic import BaseModel, field_validator
from datetime import datetime
import json
from typing import List, Optional, Any

def _normalize_prompt_array_to_json(v: Any) -> str:
    """
    입력을 JSON 문자열로 표준화합니다.
    - [1,2,3] (list) → "[1,2,3]"
    - "1,2,3" (csv)  → "[1,2,3]"
    - "[1,2,3]" (json string) → 그대로 검증 후 사용
    """
    if v is None:
        return "[]"

    # 이미 리스트인 경우
    if isinstance(v, list):
        nums = []
        for x in v:
            try:
                nums.append(int(x))
            except Exception:
                continue
        return json.dumps(nums, ensure_ascii=False)

    # 문자열인 경우 처리
    if isinstance(v, str):
        s = v.strip()
        # JSON 문자열일 가능성
        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    nums = []
                    for x in parsed:
                        try:
                            nums.append(int(x))
                        except Exception:
                            continue
                    return json.dumps(nums, ensure_ascii=False)
            except Exception:
                pass
        # CSV 형태 "1,2,3"
        parts = [p.strip() for p in s.split(",") if p.strip()]
        nums = []
        for p in parts:
            try:
                nums.append(int(p))
            except Exception:
                continue
        return json.dumps(nums, ensure_ascii=False)

    # 기타 타입은 빈 배열
    return "[]"


class PipelineBase(BaseModel):
    prompt_array: str
    description: str


class PipelineOut(PipelineBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PipelineCreate(BaseModel):
    description: str
    prompt_array: List[int] | str

    @field_validator("prompt_array", mode="before")
    @classmethod
    def normalize_prompt_array(cls, v):
        return _normalize_prompt_array_to_json(v)


class PipelineUpdate(BaseModel):
    description: Optional[str] = None
    prompt_array: Optional[List[int] | str] = None

    @field_validator("prompt_array", mode="before")
    @classmethod
    def normalize_prompt_array(cls, v):
        if v is None:
            return None
        return _normalize_prompt_array_to_json(v)
