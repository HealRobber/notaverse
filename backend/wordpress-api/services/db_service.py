from sqlalchemy.orm import Session
from models.image import Image
from models.post import Post
from datetime import datetime
from db import SessionLocal
from typing import List

# 이미지 정보 DB에 저장
def insert_image(db: Session, image_url: str, image_id: int):
    db_image = Image(image_url=image_url, image_id=image_id)
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image

# 글 정보 DB에 저장
def insert_post(db: Session, title: str, content: str, category_ids: List[int], tag_ids: List[int], image_id: int = None):
    category_ids_str = ",".join(str(cid) for cid in category_ids)
    tag_ids_str = ",".join(str(tid) for tid in tag_ids)

    db_post = Post(
        title=title,
        content=content,
        category_ids=category_ids_str,
        tag_ids=tag_ids_str,
        featured_media_id=image_id,
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

# DB 세션 가져오기
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
