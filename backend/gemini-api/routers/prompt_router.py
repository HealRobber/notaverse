from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from services.db_service import get_db
from typing import List
from schemas.prompt_schema import PromptOut, PromptCreate, PromptUpdate
from models.prompt import Prompt
from services.prompt_service import PromptService

router = APIRouter()
prompt_service = PromptService()

# PROMPT 조회
@router.get("/", response_model=List[PromptOut])
def get_prompts(db: Session = Depends(get_db)):
    return prompt_service.get_prompts(db)

# PROMPT 조회 By ID
@router.get("/{prompt_id}", response_model=PromptOut)
def get_prompt_by_id(prompt_id: int, db: Session = Depends(get_db)):
    prompt = prompt_service.get_prompt_by_id(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    return prompt

# PROMPT 생성
@router.post("/", response_model=PromptOut)
def create_prompt(prompt: PromptCreate, db: Session = Depends(get_db)):
    return prompt_service.create_prompt(prompt, db)
    
# PROMPT 업데이트
@router.put("/{prompt_id}", response_model=PromptOut)
def update_prompt(prompt_id: int, prompt: PromptUpdate, db: Session = Depends(get_db)):
    update_prompt = prompt_service.update_prompt(prompt_id, prompt, db)
    if not update_prompt:
        raise HTTPException(status_code=404, detail="Failed to update prompt.")
    return update_prompt

# PROMPT 삭제
@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(prompt_id: int, db: Session = Depends(get_db)):
    delete_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not delete_prompt:
        raise HTTPException(status_code=404, detail="Failed to delete prompt.")
    delete_prompt_id = prompt_service.delete_prompt(prompt_id, db)
    return f"Prompt deleted - Prompt ID {delete_prompt_id}"