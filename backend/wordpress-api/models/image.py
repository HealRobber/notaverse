from sqlalchemy import Column, Integer, String, TIMESTAMP
from db import Base

class Image(Base):
    __tablename__ = 'images'
    
    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String(255), index=True)
    image_id = Column(Integer)
    created_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")
