# /app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os

load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
MANAGER_DB_NAME = os.getenv("MANAGER_DB_NAME")
DB_INTERNAL_PORT = os.getenv("DB_INTERNAL_PORT")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@database:{DB_INTERNAL_PORT}/{MANAGER_DB_NAME}"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def create_tables():
    # !! 모델 먼저 등록 !!
    import models  # noqa: F401  # 등록만 목적
    Base.metadata.create_all(bind=engine)
