import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from settings import settings
from services.schedulers.locking import acquire_lock
from services.schedulers.job_registery import REGISTRY
from db import get_async_session_factory
from services.schedulers.job_repos import fetch_enabled_jobs, create_job_run, finish_job_run, get_job

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None
_registered_versions: Dict[str, int] = {}


async def _execute_job(job_id: str, params: Dict[str, Any], scheduled_time: Optional[datetime]):
    # 실행 이력 생성
    AsyncSessionLocal = get_async_session_factory()
    async with AsyncSessionLocal() as session:
        run_id = await create_job_run(session, job_id, scheduled_time)
        await session.commit()

    try:
        # 실행 전 DB 상태/락/함수 확인
        async with AsyncSessionLocal() as session:
            job = await get_job(session, job_id)
            if not job or not job.enabled:
                status = {"status": "skipped", "reason": "disabled-or-missing", "job_id": job_id}
                async with AsyncSessionLocal() as s2:
                    await finish_job_run(s2, run_id, "skipped", status, None)
                    await s2.commit()
                return status

            func = REGISTRY.get(job.func_key)
            if not func:
                msg = f"unknown func_key={job.func_key}"
                async with AsyncSessionLocal() as s2:
                    await finish_job_run(s2, run_id, "error", None, msg)
                    await s2.commit()
                return {"status": "error", "reason": msg, "job_id": job_id}

            lock_key = job.lock_key or f"lock:{job.id}"

        async with acquire_lock(settings.redis_url, lock_key) as lock:
            if lock is None:
                result = {"status": "skipped", "reason": "locked", "job_id": job_id}
                async with AsyncSessionLocal() as session:
                    await finish_job_run(session, run_id, "skipped", result, None)
                    await session.commit()
                return result

            # 실제 잡 실행
            try:
                result = await func(params)
                async with AsyncSessionLocal() as session:
                    await finish_job_run(session, run_id, "ok", result, None)
                    await session.commit()
                return result
            except Exception as e:
                logger.exception("job failed: %s", job_id)
                async with AsyncSessionLocal() as session:
                    await finish_job_run(session, run_id, "error", None, str(e))
                    await session.commit()
                return {"status": "error", "reason": str(e), "job_id": job_id}

    except Exception as e:
        logger.exception("job outer failed: %s", job_id)
        AsyncSessionLocal = get_async_session_factory()
        async with AsyncSessionLocal() as session:
            await finish_job_run(session, run_id, "error", None, f"outer: {e}")
            await session.commit()
        return {"status": "error", "reason": f"outer: {e}", "job_id": job_id}


async def _run_guarded(job_id: str, params: Dict[str, Any]):
    return await _execute_job(job_id, params, scheduled_time=datetime.now(timezone.utc))


def is_scheduler_running() -> bool:
    return _scheduler is not None


async def _reconcile_jobs():
    global _scheduler
    if not _scheduler:
        return
    try:
        AsyncSessionLocal = get_async_session_factory()
        async with AsyncSessionLocal() as session:
            jobs = await fetch_enabled_jobs(session)

        seen = set()
        for j in jobs:
            seen.add(j.id)
            trigger = CronTrigger.from_crontab(j.cron_expr)
            params = j.params_json or {}

            if _registered_versions.get(j.id) != j.version:
                _scheduler.add_job(
                    _run_guarded,
                    trigger=trigger,
                    id=j.id,
                    kwargs={"job_id": j.id, "params": params},
                    coalesce=bool(j.coalesce),
                    max_instances=int(j.max_instances),
                    misfire_grace_time=int(j.misfire_grace),
                    replace_existing=True,
                )
                _registered_versions[j.id] = j.version
                logger.info("job %s registered/updated (version=%s, cron=%s)", j.id, j.version, j.cron_expr)

        # 등록 해제(더는 enabled 아님/삭제됨)
        for existing in list(_registered_versions.keys()):
            if existing not in seen:
                try:
                    _scheduler.remove_job(existing)
                except Exception:
                    pass
                _registered_versions.pop(existing, None)
                logger.info("job %s removed (no longer enabled in DB)", existing)

    except Exception:
        logger.exception("reconcile failed")


async def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler:
        return _scheduler

    sched = AsyncIOScheduler(timezone=timezone.utc)
    sched.start()
    _scheduler = sched
    logger.info("APScheduler started")

    # 최초 동기화 + 주기 동기화
    await _reconcile_jobs()
    sched.add_job(
        _reconcile_jobs,
        trigger="interval",
        seconds=30,  # settings에 노출 원하시면 settings.schedule_sync_interval_sec 로 변경
        id="_reconcile.jobs",
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )
    logger.info("reconcile job registered")
    return sched


async def stop_scheduler() -> bool:
    global _scheduler
    if not _scheduler:
        return False
    try:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
    finally:
        _scheduler = None
        _registered_versions.clear()
    return True


async def run_now(params: Dict[str, Any], job_id: str):
    global _scheduler
    if _scheduler:
        _scheduler.add_job(
            _run_guarded,
            kwargs={"job_id": job_id, "params": params},
            next_run_time=datetime.now(timezone.utc),
        )
        return {"status": "queued", "job_id": job_id}
    else:
        return await _run_guarded(job_id, params)
