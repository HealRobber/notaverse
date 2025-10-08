from __future__ import annotations

def to_text(raw) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if hasattr(raw, "text") and isinstance(getattr(raw, "text"), str):
        return raw.text
    try:
        cands = getattr(raw, "candidates", None)
        if cands:
            chunks = []
            for c in cands:
                content = getattr(c, "content", None)
                if content and getattr(content, "parts", None):
                    for p in content.parts:
                        t = getattr(p, "text", None)
                        if isinstance(t, str):
                            chunks.append(t)
            if chunks:
                return "\n\n".join(chunks)
    except Exception:
        pass
    return str(raw)

def strip_code_fence_to_json(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return t
    if t.startswith("```"):
        t = t[3:].lstrip()
        if t.lower().startswith("json"):
            t = t[4:].lstrip()
        if t.endswith("```"):
            t = t[:-3]
        t = t.strip()
    return t
