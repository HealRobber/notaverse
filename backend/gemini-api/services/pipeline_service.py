from sqlalchemy.orm import Session
from models.pipeline import Pipeline

class PipelineService:

    # Pipeline 조회
    def get_pipelines(self, db: Session):
        return db.query(Pipeline).order_by(Pipeline.id.desc()).all()

    # Pipeline 단일 조회 (id 기준)
    def get_pipeline_by_id(self, db: Session, pipeline_id: int):
        return db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()