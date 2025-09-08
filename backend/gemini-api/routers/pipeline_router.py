from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from services.db_service import get_db
from typing import List
from schemas.pipeline_schema import PipelineOut
from services.pipeline_service import PipelineService

router = APIRouter()
pipeline_service = PipelineService()

# PIPELINE 조회
@router.get("/", response_model=List[PipelineOut])
def get_pipelines(db: Session = Depends(get_db)):
    return pipeline_service.get_pipelines(db)

# PIPELINE 조회 By ID
@router.get("/{pipeline_id}", response_model=PipelineOut)
def get_pipeline_by_id(pipeline_id: int, db: Session = Depends(get_db)):
    pipeline = pipeline_service.get_pipeline_by_id(db, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found.")
    return pipeline