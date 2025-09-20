# fallback_parser.py
from typing import Tuple, Optional
from bs4 import BeautifulSoup

def naive_fallback(html: str) -> Tuple[Optional[str], Optional[str]]:
    soup = BeautifulSoup(html, "html.parser")

    # title 후보: og:title > h1 > <title>
    meta_og = soup.find("meta", property="og:title")
    if meta_og and meta_og.get("content"):
        t = meta_og["content"].strip()
    else:
        h1 = soup.find("h1")
        t = h1.get_text(strip=True) if h1 else None
        if not t:
            if soup.title and soup.title.string:
                t = soup.title.string.strip()

    # content 후보: <article> or <main> or body 텍스트
    main = soup.find("article") or soup.find("main") or soup.body
    c = None
    if main:
        c = main.get_text(separator=" ", strip=True)

    return t, c
