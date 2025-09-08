from fastapi import FastAPI
from routers import post_router

app = FastAPI()

app.include_router(post_router.router, prefix="/posts", tags=["WordPress API"])

@app.get("/")
def health_check():
    return {"status": "ok"}