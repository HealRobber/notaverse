import mimetypes
import os, logging, requests, json
from typing import List, Dict, Any
from pathlib import Path
from utils.image_uploader import ensure_uploadable

logger = logging.getLogger(__name__)

WORDPRESS_API_BASE = (os.getenv("WORDPRESS_API_BASE", "http://wordpressapi:32552")).rstrip("/")
TIMEOUT = float(os.getenv("WP_API_TIMEOUT", "180.0"))
UPLOAD_FIELD = os.getenv("WP_UPLOAD_FIELD", "image")  # 기본 image, 필요시 file로 변경

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})

def _as_str_list(x) -> List[str]:
    return [str(i).strip() for i in (x or []) if str(i).strip()]

def _form_repeat(data: Dict[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for k, v in data.items():
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            for item in v:
                s = str(item).strip()
                if s:
                    out.append((k, s))
        else:
            s = str(v).strip()
            if s:
                out.append((k, s))
    return out

def _log_422(resp: requests.Response) -> str:
    try:
        detail = resp.json()
    except Exception:
        detail = resp.text
    logger.error("[create_post] 422 detail: %s", detail)
    return json.dumps(detail, ensure_ascii=False) if not isinstance(detail, str) else detail

def create_post(
    *,
    title: str,
    content: str,
    categories: List[str] | List[int] | None,
    tags: List[str] | List[int] | None,
    image_id: int | None,
) -> Dict[str, Any]:
    url = f"{WORDPRESS_API_BASE}/posts/create-post/"

    cats = _as_str_list(categories)
    tgs  = _as_str_list(tags)
    # 안전빵: 최소 1개씩 보냄(서버가 필수로 요구할 수 있음)
    if not cats: cats = ["일반"]
    if not tgs:  tgs  = ["뉴스"]

    safe_title = (title or "").strip() or "Untitled"
    safe_content = content or "<p></p>"

    # ---- 1) JSON 바디 시도 ----
    payload_json: Dict[str, Any] = {
        "title": safe_title,
        "content": safe_content,
        "status": "publish",     # 일부 서버는 status 요구
        "categories": cats,      # 문자열 리스트
        "tags": tgs,
    }
    if image_id is not None:
        try:
            payload_json["image_id"] = int(image_id)
        except Exception:
            logger.warning("image_id not int-like, omitting: %r", image_id)

    resp = SESSION.post(url, json=payload_json, timeout=TIMEOUT,
                        headers={"Content-Type": "application/json", "Accept": "application/json"})
    if resp.ok:
        return resp.json()
    if resp.status_code != 422:
        logger.error("[create_post] non-200: %s", resp.text[:500])
        resp.raise_for_status()
    err1 = _log_422(resp)

    # ---- 2) x-www-form-urlencoded (반복 키) 시도 ----
    form_payload = {
        "title": safe_title,
        "content": safe_content,
        "status": "publish",
        "categories": cats,   # categories=A&categories=B...
        "tags": tgs,
    }
    if "image_id" in payload_json:
        form_payload["image_id"] = payload_json["image_id"]
    resp2 = SESSION.post(url, data=_form_repeat(form_payload), timeout=TIMEOUT)
    if resp2.ok:
        return resp2.json()
    if resp2.status_code != 422:
        logger.error("[create_post] form non-200: %s", resp2.text[:500])
        resp2.raise_for_status()
    err2 = _log_422(resp2)

    # ---- 3) x-www-form-urlencoded (CSV 문자열) 시도 ----
    csv_payload = {
        "title": safe_title,
        "content": safe_content,
        "status": "publish",
        "categories": ",".join(cats),  # "A,B"
        "tags": ",".join(tgs),
    }
    if "image_id" in payload_json:
        csv_payload["image_id"] = payload_json["image_id"]
    resp3 = SESSION.post(url, data=csv_payload, timeout=TIMEOUT)
    if resp3.ok:
        return resp3.json()

    # 전부 실패 → 에러 메시지 최대한 합쳐서 던짐
    err3 = _log_422(resp3) if resp3.status_code == 422 else resp3.text[:500]
    raise requests.HTTPError(f"create_post 422. json:{err1} | form:{err2} | csv:{err3}")


def upload_images(image_paths: List[str]) -> List[Dict[str, Any]]:
    url = f"{WORDPRESS_API_BASE}/posts/upload-image/"
    results: List[Dict[str, Any]] = []

    for raw in image_paths:
        src = Path(raw)
        if not src.exists():
            logger.error("[upload_images] not found: %s", raw)
            continue

        # 업로드 가능 크기/포맷 보정
        up_path, mime = ensure_uploadable(str(src))
        up_file = Path(up_path)
        size = up_file.stat().st_size
        logger.info("[upload_images] sending %s (%d bytes, %s)", up_file.name, size, mime)

        # 1차: 설정된 필드명(기본 image)
        with open(up_file, "rb") as f:
            files = {UPLOAD_FIELD: (up_file.name, f, mime)}
            resp = SESSION.post(url, files=files, timeout=TIMEOUT)

        if resp.ok:
            results.append(resp.json())
            continue

        # 422/4xx/5xx 상세 로깅
        detail = None
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        logger.error("[upload_images] %s → %s", up_file.name, detail)

        # 2차: 필드명을 'file'로 바꿔 재시도 (일부 서버는 file 기대)
        if UPLOAD_FIELD != "file":
            with open(up_file, "rb") as f:
                files = {"file": (up_file.name, f, mime)}
                resp2 = SESSION.post(url, files=files, timeout=TIMEOUT)
            if resp2.ok:
                results.append(resp2.json())
                continue
            try:
                detail2 = resp2.json()
            except Exception:
                detail2 = resp2.text
            logger.error("[upload_images] retry(file) %s → %s", up_file.name, detail2)

        # 3차: MIME 문제 같으면 JPEG로 강제 변환 후 재시도
        if mime != "image/jpeg":
            from utils.image_uploader import _reencode_to_jpeg  # 내부 사용
            forced = up_file.with_suffix(".forced.jpg")
            _reencode_to_jpeg(up_file, forced, quality=80)
            with open(forced, "rb") as f:
                files = {UPLOAD_FIELD: (forced.name, f, "image/jpeg")}
                resp3 = SESSION.post(url, files=files, timeout=TIMEOUT)
            if resp3.ok:
                results.append(resp3.json())
                continue
            try:
                detail3 = resp3.json()
            except Exception:
                detail3 = resp3.text
            logger.error("[upload_images] retry(jpeg) %s → %s", forced.name, detail3)
            # 마지막 실패는 그대로 진행 (상위에서 처리)

    return results

