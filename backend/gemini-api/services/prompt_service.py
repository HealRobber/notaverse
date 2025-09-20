import logging
from sqlalchemy.orm import Session
from models.prompt import Prompt
from schemas.prompt_schema import PromptCreate, PromptUpdate

logger = logging.getLogger(__name__)

class PromptService:

    # Prompt 조회
    def get_prompts(self, db: Session):
        logger.info(f"[PromptService] Method : get_prompts")
        return db.query(Prompt).order_by(Prompt.id.desc()).all()

    # Prompt 단일 조회 (id 기준)
    def get_prompt_by_id(self, db: Session, prompt_id: int):
        logger.info(f"[PromptService] Method : get_prompt_by_id")
        return db.query(Prompt).filter(Prompt.id == prompt_id).first()

    # PROMPT 생성
    def create_prompt(self, prompt: PromptCreate, db: Session):
        logger.info(f"[PromptService] Method : create_prompt")
        create_prompt = Prompt(prompt=prompt.prompt)
        db.add(create_prompt)
        db.commit()
        db.refresh(create_prompt)
        return create_prompt

    # PROMPT 업데이트
    def update_prompt(self, prompt_id: int, prompt: PromptUpdate, db: Session):
        logger.info(f"[PromptService] Method : update_prompt")
        db_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
        if not db_prompt:
            return None
        db_prompt.prompt = prompt.prompt
        db.commit()
        db.refresh(db_prompt)
        return db_prompt

    # PROMPT 삭제
    def delete_prompt(self, prompt_id: int, db: Session):
        logger.info(f"[PromptService] Method : delete_prompt")
        db_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
        delete_prompt_id = db_prompt.id
        if not db_prompt:
            return None
        db.delete(db_prompt)
        db.commit()
        return delete_prompt_id