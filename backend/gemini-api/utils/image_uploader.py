from __future__ import annotations
import os
from pathlib import Path
from typing import Tuple
from PIL import Image

MAX_MB = float(os.getenv("WP_MAX_UPLOAD_MB", "2"))  # 필요시 늘리세요 (서버 PHP 설정과 맞추기)
MAX_BYTES = int(MAX_MB * 1024 * 1024)
MAX_WIDTH = int(os.getenv("WP_MAX_UPLOAD_WIDTH", "1600"))

def _reencode_to_jpeg(src: Path, dst: Path, quality: int = 85) -> None:
    im = Image.open(src)
    im.load()
    if im.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    w, h = im.size
    if w > MAX_WIDTH:
        h = int(h * (MAX_WIDTH / w))
        w = MAX_WIDTH
        im = im.resize((w, h), Image.LANCZOS)
    im.save(dst, format="JPEG", quality=quality, optimize=True, progressive=True)

def ensure_uploadable(src_path: str) -> Tuple[str, str]:
    """
    src_path를 검사해 너무 크면 JPEG로 리사이즈/재인코딩.
    반환: (업로드에 쓸 실제 경로, mime)
    """
    p = Path(src_path)
    if not p.exists():
        raise FileNotFoundError(src_path)

    # 이미 작은 경우
    if p.stat().st_size <= MAX_BYTES:
        ext = p.suffix.lower()
        if ext in (".jpg", ".jpeg"):
            return str(p), "image/jpeg"
        if ext == ".png":
            return str(p), "image/png"
        if ext == ".webp":
            return str(p), "image/webp"
        if ext == ".gif":
            return str(p), "image/gif"
        return str(p), "application/octet-stream"

    # 크면 JPEG로 바꿔서 임시 경로 반환
    out = p.with_suffix(".upload.jpg")
    _reencode_to_jpeg(p, out, quality=85)
    if out.stat().st_size > MAX_BYTES:
        # 그래도 크면 더 줄이기
        _reencode_to_jpeg(p, out, quality=75)
    return str(out), "image/jpeg"
