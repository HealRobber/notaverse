from sqlalchemy.orm import Session
from db import SessionLocal

# DB 세션 가져오기
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
