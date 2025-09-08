from sqlalchemy import Column, Integer, Text, TIMESTAMP
from db import Base

class Pipeline(Base):
    __tablename__ = 'pipelines'
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_array = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")
