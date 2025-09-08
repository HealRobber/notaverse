from sqlalchemy import Column, Integer, Text, TIMESTAMP
from db import Base

class Parameter(Base):
    __tablename__ = 'parameters'
    
    id = Column(Integer, primary_key=True, index=True)
    parameter = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")
