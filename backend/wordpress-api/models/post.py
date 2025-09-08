from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP
from db import Base

class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    content = Column(Text)
    category_ids = Column(String(255))
    tag_ids = Column(String(255))
    featured_media_id = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")
