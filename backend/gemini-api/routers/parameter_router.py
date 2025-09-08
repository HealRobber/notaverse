from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from services.db_service import get_db
from typing import List
from schemas.parameter_schema import ParameterOut, ParameterCreate, ParameterUpdate
from models.parameter import Parameter
from services.parameter_service import ParameterService

router = APIRouter()
parameter_service = ParameterService()

# PARAMETER 조회
@router.get("/", response_model=List[ParameterOut])
def get_parameters(db: Session = Depends(get_db)):
    return parameter_service.get_parameters(db)

# PARAMETER 생성
@router.post("/", response_model=ParameterOut)
def create_parameters(parameter: ParameterCreate, db: Session = Depends(get_db)):
    return parameter_service.create_parameter(parameter, db)
    
# PARAMETER 업데이트
@router.put("/{parameter_id}", response_model=ParameterOut)
def update_parameters(parameter_id: int, parameter: ParameterUpdate, db: Session = Depends(get_db)):
    update_parameter = parameter_service.update_parameter(parameter_id, parameter, db)
    if not update_parameter:
        raise HTTPException(status_code=404, detail="Failed to update parameter.")
    return update_parameter

# PARAMETER 삭제
@router.delete("/{parameter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_parameters(parameter_id: int, db: Session = Depends(get_db)):
    delete_parameter = db.query(Parameter).filter(Parameter.id == parameter_id).first()
    if not delete_parameter:
        raise HTTPException(status_code=404, detail="Failed to delete parameter.")
    delete_parameter_id = parameter_service.delete_parameter(parameter_id, db)
    return f"Parameter deleted - Parameter ID {delete_parameter_id}"