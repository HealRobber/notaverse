from fastapi import APIRouter
from services.content_generate_service import ContentGenerateService
from models.content_request import ContentRequest
from models.content_response import ContentResponse

router = APIRouter()
gen_service = ContentGenerateService()

@router.post("/generate-content/")
async def generate_content(request: ContentRequest):
    print(f"request : {request}")
    # 가장 간단: 요청 객체 그대로 전달
    result = await gen_service.generate_content(request)
    print(f"result : {result}")
    return ContentResponse(body=result.text)

@router.post("/generate-image/")
async def generate_image(request: ContentRequest):
    result = await gen_service.generate_image(request)
    return ContentResponse(
        body="Image generated."
    )