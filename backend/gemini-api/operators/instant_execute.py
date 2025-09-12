from datetime import datetime, timedelta
from db import SessionLocal
from models import Prompt, Pipeline, Series

s = SessionLocal()
try:
    pr = Prompt(prompt="간결하고 명확한 한국어로 핵심부터 서술하라.")
    s.add(pr); s.flush()

    pl = Pipeline(prompt_array=str(pr.id))
    s.add(pl); s.flush()

    ser = Series(
        title="AI 주간 이슈",
        seed_topic="생성형 AI 최신 동향",
        pipeline_id=pl.id,
        cadence="DAILY@09:30",
        next_run_at=(datetime.utcnow() - timedelta(minutes=1)),  # 지금보다 과거
    )
    s.add(ser); s.commit()
    print("seeded series_id=", ser.id)
finally:
    s.close()