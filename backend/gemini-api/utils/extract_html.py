
from __future__ import annotations
import re
from typing import Optional

def extract_html_from_finalized_content(text: str) -> Optional[str]:
    if not isinstance(text, str) or not text.strip():
        return None

    s = text

    fence_re = re.compile(
        r"```(?P<lang>[a-zA-Z0-9_-]*)\s*\n(?P<code>.*?)(?:\r?\n)```",
        re.DOTALL | re.MULTILINE,
    )

    candidates = []
    for m in fence_re.finditer(s):
        lang = (m.group("lang") or "").strip().lower()
        code = (m.group("code") or "").strip()
        if not code:
            continue
        if lang in {"html", "htm"}:
            candidates.append(("prefer", code))
        elif "<!doctype html" in code.lower() or "<html" in code.lower():
            candidates.append(("htmlish", code))

    if candidates:
        candidates.sort(key=lambda x: (0 if x[0] == "prefer" else 1, -len(x[1])))
        return candidates[0][1]

    lower = s.lower()
    start = lower.find("<!doctype html")
    if start == -1:
        start = lower.find("<html")
    if start != -1:
        end = lower.rfind("</html>")
        if end != -1:
            end += len("</html>")
        else:
            end = len(s)
        return s[start:end].strip()

    return None
