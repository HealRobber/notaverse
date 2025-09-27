from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict
import asyncio
import time
import traceback

from services.db_service import get_db
from models.RunInitContent import RunInitContentReq, RunInitContentResp
from operators.init_content import run_init_content_with_db
from operators.job_store import job_store

router = APIRouter()

@router.post("/run", response_model=RunInitContentResp)
async def run_sync(payload: RunInitContentReq, db: Session = Depends(get_db)):
    try:
        result = await run_init_content_with_db(
            db,
            topic=payload.topic,
            photo_count=payload.photo_count,
            llm_model=payload.llm_model,
            target_chars=payload.target_chars,
        )
        return RunInitContentResp(status="ok", result=result)
    except Exception as e:
        return RunInitContentResp(status="error", detail=str(e))

# 권장: 비동기 실행 + 폴링
@router.post("/run-async")
async def run_async(payload: RunInitContentReq) -> Dict[str, Any]:
    jid = job_store.new_job()

    async def _worker():
        job_store.update(jid, status="running")

        # ★ 요청과 분리된 새 DB 세션을 백그라운드 태스크에서 직접 열어 사용
        db_gen = get_db()
        db2: Session = next(db_gen)
        try:
            result = await run_init_content_with_db(
                db2,
                topic=payload.topic,
                photo_count=payload.photo_count,
                llm_model=payload.llm_model,
                target_chars=payload.target_chars,
            )
            steps = result.get("steps", {}) if isinstance(result, dict) else {}
            job_store.update(
                jid,
                status="done",
                result=result,
                steps=steps,
                finished_at=time.time(),    # ★ time 사용
            )
        except Exception as e:
            traceback.print_exc()
            job_store.update(
                jid,
                status="error",
                error=f"{e}",
                finished_at=time.time(),    # ★ time 사용
            )
        finally:
            try:
                next(db_gen)  # close session
            except StopIteration:
                pass

    asyncio.create_task(_worker())
    return {"status": "accepted", "job_id": jid}

@router.get("/status/{job_id}")
async def status(job_id: str) -> Dict[str, Any]:
    st = job_store.get(job_id)
    if not st:
        raise HTTPException(404, "job not found")
    return {
        "status": st.status,
        "steps": st.steps,
        "error": st.error,
        "started_at": st.started_at,
        "finished_at": st.finished_at,
        "has_result": st.result is not None,
    }

@router.get("/result/{job_id}")
async def result(job_id: str) -> Dict[str, Any]:
    st = job_store.get(job_id)
    if not st:
        raise HTTPException(404, "job not found")
    if st.status != "done" or st.result is None:
        return {"status": st.status, "detail": "not ready"}
    return {"status": "ok", "result": st.result}
