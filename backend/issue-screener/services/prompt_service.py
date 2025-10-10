from loguru import logger
from sqlalchemy.orm import Session
from models.prompt import Prompt

class PromptService:

    # Prompt 조회
    def get_prompts(self, db: Session):
        logger.info(f"[PromptService] Method : get_prompts")
        return db.query(Prompt).order_by(Prompt.id.desc()).all()

    # Prompt 단일 조회 (id 기준)
    def get_prompt_by_id(self, db: Session, prompt_id: int):
        logger.info(f"[PromptService] Method : get_prompt_by_id")
        return db.query(Prompt).filter(Prompt.id == prompt_id).first()