from __future__ import annotations
import typer
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from config import settings
from db import init_db
from utils.logging import setup_logging
from pipeline.runner import run_pipeline

app = typer.Typer(pretty_exceptions_show_locals=False)

@app.command("run-once")
def run_once():
    """한 번 실행하여 이슈를 수집합니다."""
    setup_logging(settings.LOG_LEVEL)
    init_db()
    res = run_pipeline()
    logger.info(f"Done. {res}")

@app.command("schedule")
def schedule():
    setup_logging(settings.LOG_LEVEL)
    logger.warning("[BOOT] schedule() entered: TZ={} CRON={}",
                   settings.TZ, settings.COLLECTOR_SCHEDULE_CRON)

    init_db()
    logger.info("[OK] init_db() done")

    job_defaults = {"misfire_grace_time": 3600, "coalesce": True, "max_instances": 1}
    sched = BlockingScheduler(timezone=settings.TZ, job_defaults=job_defaults)
    logger.info("[OK] BlockingScheduler created")

    try:
        trigger = CronTrigger.from_crontab(settings.COLLECTOR_SCHEDULE_CRON, timezone=settings.TZ)
        logger.info("[OK] CronTrigger created: {}", settings.COLLECTOR_SCHEDULE_CRON)
    except Exception as e:
        logger.exception("[FATAL] Invalid CRON '{}': {}", settings.COLLECTOR_SCHEDULE_CRON, e)
        raise

    sched.add_job(_job, trigger=trigger, id="collector-job", replace_existing=True)
    logger.info("Scheduled with CRON '{}' (TZ={})", settings.COLLECTOR_SCHEDULE_CRON, settings.TZ)

    # 동작 확인용: 기동 직후 1회 즉시 실행(테스트 후 주석 가능)
    # from datetime import datetime
    # sched.add_job(_job, id="collector-job-initial", next_run_time=datetime.now(settings.TZ), replace_existing=True)

    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


def _job():
    try:
        res = run_pipeline()
        logger.info(f"Job success: {res}")
    except Exception as e:
        logger.exception(f"Job failed: {e}")

if __name__ == "__main__":
    app()
