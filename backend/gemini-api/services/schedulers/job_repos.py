from typing import List, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from models.jobs import Job, JobRun


async def fetch_enabled_jobs(session: AsyncSession) -> List[Job]:
    res = await session.execute(select(Job).where(Job.enabled == True))
    return list(res.scalars().all())


async def get_job(session: AsyncSession, job_id: str) -> Optional[Job]:
    res = await session.execute(select(Job).where(Job.id == job_id))
    return res.scalar_one_or_none()


async def create_job_run(session: AsyncSession, job_id: str, scheduled_time: Optional[datetime]) -> int:
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # MySQL TIMESTAMP naive 저장
    run = JobRun(job_id=job_id, scheduled_time=scheduled_time, start_time=now, status="running")
    session.add(run)
    await session.flush()
    return int(run.id)


async def finish_job_run(session: AsyncSession, run_id: int, status: str, result: Optional[Dict], error_text: Optional[str]):
    res = await session.execute(select(JobRun).where(JobRun.id == run_id))
    run = res.scalar_one()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run.end_time = now
    run.status = status
    run.result_json = result
    run.error_text = error_text
    await session.flush()
