from datetime import datetime
import pytz
from sqlalchemy import select, func
from db import SessionLocal
from models.enums import JobType, SeriesStatus
from services.auto_gen.cadence import compute_next_run
from models import Series, ContentJob

import models  # noqa: F401  # 패키지 로딩만으로도 전부 등록됨


KST = pytz.timezone("Asia/Seoul")

def run_scheduler() -> None:
    db = SessionLocal()
    try:
        # due 인 연재 선택 (잠금)
        series_list = db.execute(
            select(Series)
            .where(
                Series.status == SeriesStatus.active,
                Series.next_run_at <= func.now()
            )
            .with_for_update()
        ).scalars().all()

        for s in series_list:
            # PLAN_NEXT 잡 투입
            db.add(ContentJob(job_type=JobType.PLAN_NEXT, payload={"series_id": s.id}))
            # next_run_at 갱신
            now_kst = datetime.now(KST)
            s.next_run_at = compute_next_run(now_kst, s.cadence)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run_scheduler()
