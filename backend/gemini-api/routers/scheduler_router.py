from fastapi import APIRouter, Header, HTTPException
from typing import Optional, Dict, Any

from services.schedulers.scheduler import is_scheduler_running, start_scheduler, stop_scheduler, run_now
from settings import settings

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def _check_token(x_run_token: Optional[str]):
    if settings.run_token and x_run_token != settings.run_token:
        raise HTTPException(status_code=401, detail="invalid run token")


@router.get("/status")
async def status():
    return {
        "running": is_scheduler_running(),
        "redis": bool(settings.redis_url),
    }


@router.post("/start")
async def start(x_run_token: Optional[str] = Header(None)):
    _check_token(x_run_token)
    await start_scheduler()
    return {"status": "started"}


@router.post("/stop")
async def stop(x_run_token: Optional[str] = Header(None)):
    _check_token(x_run_token)
    ok = await stop_scheduler()
    return {"status": "stopped" if ok else "already-stopped"}


@router.post("/run-now/{job_id}")
async def run_now_endpoint(job_id: str, params: Dict[str, Any], x_run_token: Optional[str] = Header(None)):
    _check_token(x_run_token)
    return await run_now(params, job_id=job_id)
