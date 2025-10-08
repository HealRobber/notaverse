from __future__ import annotations
from typing import List, Dict, Any, Union
from google.genai import types as gatypes

# 당신 프로젝트의 모델 경로에 맞춰 임포트하세요.
from models.content_request import ContentRequest, ContentMessage

PromptLike = Union[
    str,
    ContentRequest,
    List[ContentMessage],
    List[Dict[str, Any]],  # 외부에서 이미 dict 배열로 들어오는 경우도 지원
]

def to_ga_contents(prompt: PromptLike) -> List[gatypes.Content]:
    """
    다양한 입력(prompt)을 Google GenAI SDK의 정식 타입(List[gatypes.Content])으로 변환합니다.
    - 문자열      → [Content(role="user", parts=[Part(text=...))])]
    - ContentRequest → 재귀 처리(content 필드)
    - List[ContentMessage] → 각 메시지를 Content/Part로 변환
    - List[dict] (SDK-유사 구조) → 안전하게 정규화 후 Content/Part로 변환
    """

    # 1) 단일 문자열
    if isinstance(prompt, str):
        text = prompt.strip()
        if not text:
            raise ValueError("Empty prompt text")
        return [gatypes.Content(role="user", parts=[gatypes.Part(text=text)])]

    # 2) Pydantic ContentRequest
    if isinstance(prompt, ContentRequest):
        return to_ga_contents(prompt.content)

    # 3) List[ContentMessage]
    if isinstance(prompt, list) and prompt and isinstance(prompt[0], ContentMessage):
        out: List[gatypes.Content] = []
        for m in prompt:
            parts: List[gatypes.Part] = []
            for p in (m.parts or []):
                if isinstance(p, str):
                    t = p.strip()
                    if t:
                        parts.append(gatypes.Part(text=t))
                elif isinstance(p, dict):
                    # {"text": "..."} | {"inline_data": ...} | {"file_data": ...}
                    if "text" in p and isinstance(p["text"], str):
                        t = p["text"].strip()
                        if t:
                            parts.append(gatypes.Part(text=t))
                    elif "inline_data" in p:
                        parts.append(gatypes.Part(inline_data=p["inline_data"]))
                    elif "file_data" in p:
                        parts.append(gatypes.Part(file_data=p["file_data"]))
                    # 그 외 형태는 스킵
            if parts:
                out.append(gatypes.Content(role=m.role or "user", parts=parts))
        if not out:
            raise ValueError("Normalized contents is empty (List[ContentMessage])")
        return out

    # 4) 이미 dict 리스트(외부에서 들어온 SDK-유사 구조)
    if isinstance(prompt, list) and prompt and isinstance(prompt[0], dict):
        out: List[gatypes.Content] = []
        for m in prompt:
            role = (m.get("role") or "user").strip() or "user"
            raw_parts = m.get("parts") or []
            parts: List[gatypes.Part] = []
            for p in raw_parts:
                if isinstance(p, str):
                    t = p.strip()
                    if t:
                        parts.append(gatypes.Part(text=t))
                elif isinstance(p, dict):
                    if "text" in p and isinstance(p["text"], str):
                        t = p["text"].strip()
                        if t:
                            parts.append(gatypes.Part(text=t))
                    elif "inline_data" in p:
                        parts.append(gatypes.Part(inline_data=p["inline_data"]))
                    elif "file_data" in p:
                        parts.append(gatypes.Part(file_data=p["file_data"]))
            if parts:
                out.append(gatypes.Content(role=role, parts=parts))
        if not out:
            raise ValueError("Normalized contents is empty (List[dict])")
        return out

    raise TypeError(f"Unsupported prompt type: {type(prompt)}")
