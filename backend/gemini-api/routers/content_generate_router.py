from fastapi import APIRouter
from services.content_generate_service import ContentGenerateService
from models.content_request import ContentRequest
from models.content_response import ContentResponse

router = APIRouter()
gen_service = ContentGenerateService()

@router.post("/generate-content/")
async def generate_content(request: ContentRequest):
    print(f"request : {request}")
    # result = await gen_service.generate_content(model=request.model, topic=request.topic, keyqords=request.keywords)
    result = await gen_service.generate_content(model=request.model, contents=request.content)
    print(f"result : {result}")
    return ContentResponse(
        # title=result["title"],
        body=result.text
    )

@router.post("/generate-image/")
async def generate_image(request: ContentRequest):
    result = await gen_service.generate_image(image_model=request.image_model, contents=request.content) 
    return ContentResponse(
        body="Image generated."
    )