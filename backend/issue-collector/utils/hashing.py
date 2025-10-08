from __future__ import annotations
import hashlib

def fingerprint_from(title: str, url: str) -> str:
    base = f"{title.strip()}|{url.strip()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
