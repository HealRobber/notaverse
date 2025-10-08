from __future__ import annotations
from utils.hashing import fingerprint_from
from schemas import CollectedTopic

def make_fingerprint(item: CollectedTopic) -> str:
    return fingerprint_from(item.title, str(item.url))
