
from __future__ import annotations
import json
import re
import logging
from typing import Any, Dict, List, Optional, Union

from common.llm import generate_images_with_retry
from common.http import robust_upload_images
from models.content_request import ContentMessage, ContentRequest

logger = logging.getLogger(__name__)

def _strip_bom_and_whitespace(s: str) -> str:
    return s.lstrip("\ufeff").strip()


def _extract_code_fence_block(s: str) -> Optional[str]:
    m = re.search(r"(?s)(?:^|[\r\n])(?:```|~~~)\s*(?:json|javascript|js|ts|typescript|python|py)?\s*\n(?P<code>.*?)(?:\r?\n)(?:```|~~~)\s*(?:$|[\r\n])", s)
    if m:
        return m.group("code").strip()
    return None


def _remove_comments_and_trailing_commas(s: str) -> str:
    s = re.sub(r"(?<!https:)(?<!http:)//.*?$", "", s, flags=re.M)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s


def _extract_first_json_substring(s: str) -> Optional[str]:
    s = s.strip()
    start = s.find("[")
    end = s.rfind("]")
    if start != -1 and end != -1 and end > start:
        return s[start:end + 1].strip()
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return s[start:end + 1].strip()
    return None


def parse_visual_components(
    data: Union[str, List[Dict[str, Any]], Dict[str, Any]]
) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        if any(not isinstance(x, dict) for x in data):
            raise TypeError("visual_components: list elements must be dicts")
        return data

    if isinstance(data, dict):
        return [data]

    if not isinstance(data, str):
        raise TypeError("parse_visual_components: unsupported type")

    s = _strip_bom_and_whitespace(data)

    # Extract code fence if present
    inner = _extract_code_fence_block(s)
    if inner is not None:
        s = inner

    # Direct parse
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return [obj]
        if isinstance(obj, list):
            if any(not isinstance(x, dict) for x in obj):
                raise TypeError("visual_components(JSON): list elements must be dicts")
            return obj
        raise TypeError("Top-level JSON must be a list or dict")
    except json.JSONDecodeError:
        pass

    # Clean comments/trailing commas and retry
    s2 = _remove_comments_and_trailing_commas(s)
    try:
        obj = json.loads(s2)
        if isinstance(obj, dict):
            return [obj]
        if isinstance(obj, list):
            if any(not isinstance(x, dict) for x in obj):
                raise TypeError("visual_components(JSON cleaned): list elements must be dicts")
            return obj
        raise TypeError("Top-level JSON (cleaned) must be a list or dict")
    except json.JSONDecodeError:
        pass

    # Extract first plausible JSON substring and retry
    sub = _extract_first_json_substring(s2)
    if sub:
        obj = json.loads(sub)
        if isinstance(obj, dict):
            return [obj]
        if isinstance(obj, list):
            if any(not isinstance(x, dict) for x in obj):
                raise TypeError("visual_components(JSON extracted): list elements must be dicts")
            return obj
        raise TypeError("Top-level JSON (extracted) must be a list or dict")

    preview = s[:200].replace("\n", "\\n")
    raise json.JSONDecodeError(f"Could not parse JSON from input (preview: {preview} ...)", s, 0)


async def enrich_visual_components_with_images(
    visual_components: List[Dict[str, Any]],
    content_generate_service: Any,
    upload_url: str,
    use_first_image_only: bool = True,
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = [dict(comp) for comp in visual_components]

    for comp in result:
        comp_type = str(comp.get("type", "")).strip()

        if comp_type == "표":
            continue

        image_prompt = (comp.get("image_prompt") or comp.get("prompt") or "").strip()
        if not image_prompt:
            continue

        content = [ContentMessage(role="user", parts=[image_prompt])]
        req = ContentRequest(content=content)
        image_model = getattr(req, "image_model", None)

        try:
            saved_image_paths = await generate_images_with_retry(
                content_generate_service,
                image_model,
                image_prompt,
            )
        except Exception:
            continue

        if not saved_image_paths:
            continue

        paths_to_upload = [saved_image_paths[0]] if use_first_image_only else list(saved_image_paths)
        try:
            uploaded_url = await robust_upload_images(paths_to_upload, upload_url)
        except Exception:
            continue

        clean_url = extract_image_urls(uploaded_url)

        image_ids = extract_image_ids(uploaded_url)
        first_id = image_ids[0] if image_ids else None

        if not clean_url:
            continue

        comp["image_urls"] = clean_url

    return result, first_id

async def process_visual_components_from_str(
    raw_json: Union[str, List[Dict[str, Any]], Dict[str, Any]],
    content_generate_service: Any,
    upload_url: str,
    use_first_image_only: bool = True,
) -> List[Dict[str, Any]]:
    components = parse_visual_components(raw_json)
    return await enrich_visual_components_with_images(
        components,
        content_generate_service,
        upload_url,
        use_first_image_only=use_first_image_only,
    )

# 업로드 결과에서 URL만 뽑아내는 헬퍼
def extract_image_urls(uploaded) -> list[str]:
    urls: list[str] = []
    if isinstance(uploaded, dict):
        # 단일 dict인 경우
        v = uploaded.get("image_url") or uploaded.get("url") or uploaded.get("source_url") or uploaded.get("link")
        if isinstance(v, str) and v.strip():
            urls.append(v.strip())
        else:
            guid = uploaded.get("guid")
            if isinstance(guid, dict):
                r = guid.get("rendered")
                if isinstance(r, str) and r.strip():
                    urls.append(r.strip())
        return urls

    if isinstance(uploaded, list):
        for item in uploaded:
            if isinstance(item, str):
                if item.strip():
                    urls.append(item.strip())
            elif isinstance(item, dict):
                v = item.get("image_url") or item.get("url") or item.get("source_url") or item.get("link")
                if isinstance(v, str) and v.strip():
                    urls.append(v.strip())
                else:
                    guid = item.get("guid")
                    if isinstance(guid, dict):
                        r = guid.get("rendered")
                        if isinstance(r, str) and r.strip():
                            urls.append(r.strip())
    return urls

def extract_image_ids(uploaded):
    if isinstance(uploaded, dict):
        return [uploaded["image_id"]] if "image_id" in uploaded else []
    if isinstance(uploaded, list):
        return [x["image_id"] for x in uploaded if isinstance(x, dict) and "image_id" in x]
    return []
