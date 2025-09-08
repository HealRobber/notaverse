from fastapi import APIRouter, UploadFile, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from services.wp_service import WordPressService
from services.db_service import get_db, insert_image, insert_post 
from sqlalchemy.orm import Session
from typing import List, Union, Optional

router = APIRouter()
wp_service = WordPressService()

@router.post("/upload-image/")
async def upload_image(
    image: UploadFile,
    db: Session = Depends(get_db)
):
    # 워드프레스에 이미지 업로드
    image_url = wp_service.upload_image(image)
    if not image_url:
        raise HTTPException(status_code=400, detail="워드프레스 이미지 업로드 실패")
    print(image_url)
    # (예시용) 워드프레스에서 반환받은 image_id (API로 실제 ID 받아오는 로직 구현 필요)
    image_id = wp_service.get_image_id(image_url)
    
    # DB에 이미지 정보 저장
    db_image = insert_image(db, image_url, image_id)
    
    return {
        "message": "이미지 업로드 및 DB 저장 성공",
        "db_image_id": db_image.id,
        "image_id": db_image.image_id,
        "image_url": db_image.image_url
    }

@router.post("/create-post/")
async def create_post(
    title: str = Form(...),
    content: str = Form(...),
    categories: Union[List[str], str] = Form(...),
    tags: Union[List[str], str] = Form(...),
    image_id: Union[int, str, None] = Form(None),
    db: Session = Depends(get_db)
):

    # IMAGE ID NULL 처리
    try:
        image_id = int(image_id) if image_id not in (None, "", "null") else None
    except ValueError:
        raise HTTPException(status_code=422, detail="image_id는 정수이거나 비워야 합니다.")

    # CATEGORY 리스트 형태 변환
    category_list = parse_str_list(categories)

    # TAG를 리스트 형태로 변환
    tag_list = parse_str_list(tags)
    
    # 워드프레스에서 카테고리와 태그 생성
    category_ids, failed_category = wp_service.create_category(category_list)
    tag_ids, failed_tags = wp_service.create_tags(tag_list)

    print(f"category_ids : {category_ids}")
    print(f"tag_ids : {tag_ids}")
    print(f"failed_tags : {failed_tags}")

    if not category_ids or not tag_ids or failed_tags:
        raise HTTPException(
            status_code=400, 
            detail=f"카테고리 또는 태그 생성 실패 TAG : {', '.join(failed_tags)}"
        )

    # 워드프레스에 글 등록
    wp_post = wp_service.create_post(
        title=title,
        content=content,
        categories=category_ids,
        tags=tag_ids,
        featured_media_id=image_id
    )

    if not wp_post or "id" not in wp_post:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail="워드프레스 글 등록 실패")

    # DB에 글 정보 저장
    db_post = insert_post(
        db,
        title=title,
        content=content,
        category_ids=category_ids,
        tag_ids=tag_ids,
        image_id=image_id
    )

    return {
        "message": "글 등록 및 DB 저장 성공",
        "db_post_id": db_post.id,
        "wp_post_id": wp_post["id"],
        "wp_link": wp_post["link"]
    }

def parse_str_list(value: Union[str, List[str]]) -> List[str]:
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    elif isinstance(value, list):
        if len(value) == 1 and isinstance(value[0], str) and "," in value[0]:
            return [v.strip() for v in value[0].split(",") if v.strip()]
        else:
            return [v.strip() for v in value if isinstance(v, str) and v.strip()]
    else:
        return []