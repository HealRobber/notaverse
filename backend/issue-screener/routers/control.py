#!/usr/bin/env python3
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from services.runner import runner_manager
from services.screener_gemini import gemini_screener

router = APIRouter(prefix="/control", tags=["control"])


@router.post("/start")
def start(
    idle_min: float = Query(2.0, ge=0.1),
    idle_max: float = Query(60.0, ge=0.1),
):
    if idle_max < idle_min:
        raise HTTPException(status_code=400, detail="idle_max must be >= idle_min")

    ok = runner_manager.start(
        screener=gemini_screener,
        idle_min_sec=idle_min,
        idle_max_sec=idle_max,
    )
    if not ok:
        raise HTTPException(status_code=409, detail="Runner already running")

    logger.info("Runner started")
    return {"ok": True, "status": runner_manager.status()}


@router.post("/stop")
def stop():
    ok = runner_manager.stop()
    if not ok:
        raise HTTPException(status_code=409, detail="Runner not running")
    logger.info("Runner stopping")
    return {"ok": True, "status": runner_manager.status()}


@router.get("/status")
def status():
    return runner_manager.status()
