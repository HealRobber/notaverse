from __future__ import annotations
import random
from settings import settings

def jittered_backoff(attempt: int, *, max_backoff: int | None = None) -> float:
    cap = max_backoff if max_backoff is not None else settings.STEP_MAX_BACKOFF
    return min(2 ** attempt, cap) + random.uniform(0.1, 0.9)
