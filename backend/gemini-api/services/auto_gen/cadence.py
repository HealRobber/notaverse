# services/auto_gen/cadence.py
from datetime import datetime, timedelta
import re

# 허용: DAILY@H, DAILY@HH, DAILY@H:MM, DAILY@HH:MM
DAILY_RE = re.compile(
    r"^DAILY@(?P<hour>\d{1,2})(?::(?P<min>\d{1,2}))?$",
    re.IGNORECASE
)

def compute_next_run(now_kst: datetime, cadence: str) -> datetime:
    """
    croniter 없이 DAILY만 지원.
    - DAILY@H 또는 DAILY@HH       → 분은 0으로 가정
    - DAILY@H:MM / DAILY@HH:MM    → 그대로 사용
    반환은 now_kst와 동일한 naive datetime.
    """
    if not cadence:
        raise ValueError("cadence is empty")

    c = cadence.strip()

    # DAILY
    m = DAILY_RE.match(c)
    if m:
        hh = int(m.group("hour"))
        mm = int(m.group("min") or 0)
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError(f"Invalid DAILY time: {cadence}")
        target = now_kst.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return target if now_kst < target else (target + timedelta(days=1))

    # CRON 미지원
    if c.upper().startswith("CRON:"):
        raise ValueError("CRON cadence is not supported (install croniter or switch to DAILY@HH[:MM]).")

    raise ValueError(f"Unsupported cadence format: {cadence} (use 'DAILY@HH[:MM]')")
