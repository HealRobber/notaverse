# routers/pipeline_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from services.db_service import get_db
from typing import List
from schemas.pipeline_schema import PipelineOut, PipelineCreate, PipelineUpdate
from services.pipeline_service import PipelineService

router = APIRouter()
pipeline_service = PipelineService()

# PIPELINE 목록 조회
@router.get("/", response_model=List[PipelineOut])
def get_pipelines(db: Session = Depends(get_db)):
    return pipeline_service.get_pipelines(db)

# PIPELINE 단건 조회 By ID
@router.get("/{pipeline_id}", response_model=PipelineOut)
def get_pipeline_by_id(pipeline_id: int, db: Session = Depends(get_db)):
    pipeline = pipeline_service.get_pipeline_by_id(db, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found.")
    return pipeline

# PIPELINE 생성
@router.post("/", response_model=PipelineOut, status_code=status.HTTP_201_CREATED)
def create_pipeline(payload: PipelineCreate, db: Session = Depends(get_db)):
    created = pipeline_service.create_pipeline(db, payload)
    return created

# PIPELINE 수정
@router.put("/{pipeline_id}", response_model=PipelineOut)
def update_pipeline(pipeline_id: int, payload: PipelineUpdate, db: Session = Depends(get_db)):
    updated = pipeline_service.update_pipeline(db, pipeline_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Pipeline not found.")
    return updated

# PIPELINE 삭제
@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pipeline(pipeline_id: int, db: Session = Depends(get_db)):
    ok = pipeline_service.delete_pipeline(db, pipeline_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Pipeline not found.")
    # 204 이므로 바디 없음
