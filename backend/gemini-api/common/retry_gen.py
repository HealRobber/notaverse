# common/retry_gen.py
from __future__ import annotations
import asyncio
from typing import Union, List, Optional, Dict, Any
from models.content_request import ContentRequest, ContentMessage  # 경로 맞게 수정

def _normalize_to_sdk_contents(
    prompt: Union[str, ContentRequest, List[ContentMessage], List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    # case 1) 단일 문자열 → 단일 user 메시지
    if isinstance(prompt, str):
        req = ContentRequest(content=[ContentMessage.from_text(prompt, role="user")])
        return req.to_sdk_contents()

    # case 2) 이미 ContentRequest
    if isinstance(prompt, ContentRequest):
        return prompt.to_sdk_contents()

    # case 3) List[ContentMessage]
    if isinstance(prompt, list) and prompt and isinstance(prompt[0], ContentMessage):
        req = ContentRequest(content=prompt)  # model 필드는 서비스에서 따로 넣거나 여기서 기본 채움
        return req.to_sdk_contents()

    # case 4) 이미 SDK 규격(dict) 리스트로 넘어온 경우(옵셔널)
    if isinstance(prompt, list) and prompt and isinstance(prompt[0], dict):
        # parts가 문자열이면 감싸주고, 공백 메시지는 제거
        out: List[Dict[str, Any]] = []
        for m in prompt:
            role = (m.get("role") or "user").strip() or "user"
            parts = m.get("parts") or []
            norm_parts: List[Dict[str, Any]] = []
            for p in parts:
                if isinstance(p, str):
                    t = p.strip()
                    if t:
                        norm_parts.append({"text": t})
                elif isinstance(p, dict):
                    if p.get("text") or p.get("inline_data") or p.get("file_data"):
                        # 그대로 넣음
                        # (필요시 text strip)
                        if "text" in p and isinstance(p["text"], str):
                            tt = p["text"].strip()
                            if tt:
                                p = {**p, "text": tt}
                            else:
                                continue
                        norm_parts.append(p)
            if norm_parts:
                out.append({"role": role, "parts": norm_parts})
        if not out:
            raise ValueError("normalized SDK-contents is empty")
        return out

    raise TypeError(f"Unsupported prompt type: {type(prompt)}")

async def generate_text_with_retry(
    service,
    model: str,
    prompt: Union[str, ContentRequest, List[ContentMessage], List[Dict[str, Any]]],
    *,
    max_retries: int | None = None,
) -> str:
    retries = max_retries if max_retries is not None else settings.STEP_MAX_RETRIES
    last_err: Optional[Exception] = None

    # 한 번만 정규화
    contents = _normalize_to_sdk_contents(prompt)

    for attempt in range(retries):
        try:
            resp = await service.generate_content(model, contents)  # ← 서비스는 SDK 규격만 받음
            text = to_text(resp)
            if not text:
                raise RuntimeError("empty text")
            return text
        except Exception as e:
            last_err = e
            await asyncio.sleep(jittered_backoff(attempt))
    raise last_err or RuntimeError("generate_text_with_retry failed")
