from services.content_generate_service import ContentGenerateService
from services.pipeline_service import PipelineService
from services.prompt_service import PromptService
from sqlalchemy.orm import Session

class CreateArticleService:

    def __init__(self):
        self.content_generate_service = ContentGenerateService()
        self.pipeline_service = PipelineService()
        self.prompt_service = PromptService()
    
    def fetch_pipeline(self, db: Session, pipeline_id: int):
        pipeline = self.pipeline_service.get_pipeline_by_id(db, pipeline_id)
        return pipeline

    def fetch_prompt(self, db: Session, prompt_id: int):
        prompt = self.prompt_service.get_prompt_by_id(db, prompt_id)
        return prompt