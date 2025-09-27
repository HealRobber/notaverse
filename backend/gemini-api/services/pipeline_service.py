# services/pipeline_service.py
from sqlalchemy.orm import Session
from models.pipeline import Pipeline
from schemas.pipeline_schema import PipelineCreate, PipelineUpdate

class PipelineService:

    # Pipeline 조회
    def get_pipelines(self, db: Session):
        return db.query(Pipeline).order_by(Pipeline.id.desc()).all()

    # Pipeline 단일 조회 (id 기준)
    def get_pipeline_by_id(self, db: Session, pipeline_id: int):
        return db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()

    # Pipeline 생성
    def create_pipeline(self, db: Session, payload: PipelineCreate):
        obj = Pipeline(
            description=payload.description,
            prompt_array=payload.prompt_array,  # 이미 JSON 문자열로 정규화됨
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Pipeline 수정(부분 업데이트)
    def update_pipeline(self, db: Session, pipeline_id: int, payload: PipelineUpdate):
        obj = self.get_pipeline_by_id(db, pipeline_id)
        if not obj:
            return None

        if payload.description is not None:
            obj.description = payload.description
        if payload.prompt_array is not None:
            obj.prompt_array = payload.prompt_array  # JSON 문자열

        db.commit()
        db.refresh(obj)
        return obj

    # Pipeline 삭제
    def delete_pipeline(self, db: Session, pipeline_id: int) -> bool:
        obj = self.get_pipeline_by_id(db, pipeline_id)
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True
