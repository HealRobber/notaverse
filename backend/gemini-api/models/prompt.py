from sqlalchemy import Column, Integer, Text, TIMESTAMP
from db import Base

class Prompt(Base):
    __tablename__ = 'prompts'
    
    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")
