import logging
import log_config

from fastapi import FastAPI
from routers import content_generate_router, prompt_router, parameter_router, pipeline_router, scheduler_router, post_router

logger = logging.getLogger(__name__)


app = FastAPI()

app.include_router(content_generate_router.router, prefix="/gemini", tags=["Gemini API"])
app.include_router(prompt_router.router, prefix="/prompts", tags=["Prompt API"])
app.include_router(parameter_router.router, prefix="/parameters", tags=["Parameter API"])
app.include_router(pipeline_router.router, prefix="/pipelines", tags=["Pipeline API"])
app.include_router(scheduler_router.router, prefix="/schedulers", tags=["Scheduler API"])
app.include_router(post_router.router, prefix="/post", tags=["Content API"])

@app.get("/")
def health_check():
    return {"status": "ok"}