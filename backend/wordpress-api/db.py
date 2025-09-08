from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
MANAGER_DB_NAME = os.getenv("MANAGER_DB_NAME")
DB_INTERNAL_PORT = os.getenv("DB_INTERNAL_PORT")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@database:{DB_INTERNAL_PORT}/{MANAGER_DB_NAME}"

# DB 연결 엔진 생성
engine = create_engine(DATABASE_URL, echo=True)

# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모델의 베이스 클래스
Base = declarative_base()

# 테이블 생성
Base.metadata.create_all(bind=engine)