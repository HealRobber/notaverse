# main.py
from fastapi import FastAPI
from loguru import logger

# 우리가 만든 컨트롤 라우터 (start/stop/status)
from routers.control import router as control_router

app = FastAPI()

# 라우터 등록
app.include_router(control_router)

@app.get("/healthz")
def healthz():
    return {"ok": True}
