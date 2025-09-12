import time
from datetime import timedelta, datetime, timezone
from sqlalchemy import select, func
from db import SessionLocal
from models.enums import JobType, JobStatus
from services.auto_gen.series_planner import plan_next_episode
from services.auto_gen.post_writer import write_and_post
from models import ContentJob

import models  # noqa: F401  # 패키지 로딩만으로도 전부 등록됨

BACKOFF_SECONDS = 60

def fetch_one_job(db) -> ContentJob | None:
    # 경쟁 환경에서도 안전: SKIP LOCKED
    job = db.execute(
        select(ContentJob)
        .where(
            ContentJob.status == JobStatus.queued,
            ContentJob.available_at <= func.now()
        )
        .order_by(ContentJob.scheduled_at.asc(), ContentJob.id.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    ).scalar_one_or_none()

    if job:
        job.status = JobStatus.running
        job.started_at = func.now()
    return job


def handle_success(job: ContentJob) -> None:
    job.status = JobStatus.done
    job.finished_at = func.now()


def _utcnow_naive() -> datetime:
    # DB가 naive DATETIME이면 naive UTC로 맞춰주거나, 로컬 정책에 맞게 변경
    return datetime.utcnow().replace(tzinfo=None)

def handle_failure(job: ContentJob, err_msg: str) -> None:
    job.attempts += 1
    job.last_error = (err_msg[:2000] if err_msg else "")
    if job.attempts >= job.max_attempts:
        job.status = JobStatus.failed
        job.finished_at = _utcnow_naive()
    else:
        job.status = JobStatus.queued
        job.available_at = _utcnow_naive() + timedelta(seconds=BACKOFF_SECONDS)  # ✅ 실제 시각 값으로 저장


def run_once() -> bool:
    db = SessionLocal()
    try:
        job = fetch_one_job(db)
        if not job:
            db.commit()
            return False

        try:
            if job.job_type == JobType.PLAN_NEXT:
                plan_next_episode(db, job.payload["series_id"])
            elif job.job_type == JobType.WRITE_AND_POST:
                write_and_post(db, job.payload["series_id"], job.payload["episode_no"])
            else:
                raise ValueError(f"Unknown job_type: {job.job_type}")

            handle_success(job)
            db.commit()
            return True

        except Exception as e:
            handle_failure(job, str(e))
            db.commit()
            return True

    finally:
        db.close()


if __name__ == "__main__":
    while True:
        progressed = run_once()
        if not progressed:
            time.sleep(2)
