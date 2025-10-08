# app/common/http.py
from __future__ import annotations
import io, csv
from typing import Any, Optional, Iterable
from json import JSONDecodeError
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from loguru import logger


def new_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3, backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=["HEAD","GET","OPTIONS"]
    )
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({
        "User-Agent": "notaverse-collector/1.0 (+https://notaverse.org)"
    })
    return s

def debug_response(r: requests.Response) -> None:
    logger.error(
        "HTTP %s %s\nContent-Type: %s\nLength: %s\nPreview: %r",
        r.status_code, r.url, r.headers.get("Content-Type"),
        len(r.content), r.text[:300]
    )

def get_json(url: str, session: Optional[requests.Session] = None, **kw) -> Any:
    s = session or new_session()
    r = s.get(url, timeout=30, **kw)
    r.raise_for_status()
    ctype = (r.headers.get("Content-Type") or "").lower()
    if "json" not in ctype:
        debug_response(r)
        raise ValueError(f"Expected JSON but got {ctype} at {url}")
    try:
        return r.json()
    except JSONDecodeError:
        debug_response(r)
        raise

def get_text(url: str, session: Optional[requests.Session] = None, **kw) -> str:
    s = session or new_session()
    r = s.get(url, timeout=30, **kw)
    r.raise_for_status()
    return r.text

def get_tsv_rows(url: str, session: Optional[requests.Session] = None, delimiter: str = "\t", **kw) -> list[dict[str, str]]:
    txt = get_text(url, session=session, **kw)
    reader = csv.DictReader(io.StringIO(txt), delimiter=delimiter)
    return list(reader)
