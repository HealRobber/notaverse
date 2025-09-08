from sqlalchemy.orm import Session
from models.parameter import Parameter
from schemas.parameter_schema import ParameterCreate, ParameterUpdate

class ParameterService:

    # Parameter 조회
    def get_parameters(self, db: Session):
        return db.query(Parameter).order_by(Parameter.id.desc()).all()

    # PARAMETER 생성
    def create_parameter(self, parameter: ParameterCreate, db: Session):
        create_parameter = Parameter(parameter=parameter.parameter)
        db.add(create_parameter)
        db.commit()
        db.refresh(create_parameter)
        return create_parameter

    # PARAMETER 업데이트
    def update_parameter(self, parameter_id: int, parameter: ParameterUpdate, db: Session):
        db_parameter = db.query(Parameter).filter(Parameter.id == parameter_id).first()
        if not db_parameter:
            return None
        db_parameter.parameter = parameter.parameter
        db.commit()
        db.refresh(db_parameter)
        return db_parameter

    # PARAMETER 삭제
    def delete_parameter(self, parameter_id: int, db: Session):
        db_parameter = db.query(Parameter).filter(Parameter.id == parameter_id).first()
        delete_parameter_id = db_parameter.id
        if not db_parameter:
            return None
        db.delete(db_parameter)
        db.commit()
        return delete_parameter_id