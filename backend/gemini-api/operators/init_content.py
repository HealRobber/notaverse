import asyncio
import log_config ## logger 로그 남기기 위한 import (사용되고 있음)
import logging
import json
import httpx

from services.create_article_service import CreateArticleService
from services.db_service import get_db
from services.content_generate_service import ContentGenerateService
from models.content_request import ContentRequest
from sqlalchemy.orm import Session
from utils.html_parser import HtmlParser

logger = logging.getLogger(__name__)

async def main():
    pipeline_id = 1  # 조회할 pipeline ID
    topic = """
한국 주식 시장의 행보와 2025년 트렌드 분석
    """
    wordpress_api_url = "http://wordpressapi"

    create_article_service = CreateArticleService()
    content_generate_service = ContentGenerateService()

    # get_db()는 제너레이터 함수이므로, 직접 호출 후 next()로 세션 획득
    db_generator = get_db()
    db: Session = next(db_generator)

    try:
        pipeline = create_article_service.fetch_pipeline(db, pipeline_id)
        prompt_ids = pipeline.prompt_array.split(',')

        for prompt_id in prompt_ids:
            prompt = create_article_service.fetch_prompt(db, int(prompt_id.strip()))

            if prompt_id == "1":
                content_request = ContentRequest(content=prompt.prompt.format(topic=topic))
                generated_content = await content_generate_service.generate_content(content_request.model, content_request.content)

            elif prompt_id == "2":
                content_request = ContentRequest(content=prompt.prompt.format(generated_content=generated_content))
                fact_checked_text = await content_generate_service.generate_content(content_request.model, content_request.content)

            elif prompt_id == "3":
                logger.info(f"prompt.id: {prompt.id} / prompt.prompt: {prompt.prompt}")
                content_request = ContentRequest(content=prompt.prompt.format(n=2, fact_checked_text=fact_checked_text))
                saved_image_paths = await content_generate_service.generate_image(content_request.image_model, content_request.content)

                uploaded_results = await upload_images_to_api(saved_image_paths, f"{wordpress_api_url}:32552/posts/upload-image/")
                logger.info(f"uploaded_results: {uploaded_results}")

            elif prompt_id == "4":
                # logger.info(f"prompt.id: {prompt.id} / prompt.prompt: {prompt.prompt}")
                content_request = ContentRequest(content=prompt.prompt.format(fact_checked_text=fact_checked_text))
                tag_category_result = await content_generate_service.generate_content(content_request.model, content_request.content)

                # "```json ... ```" 제거
                clean_text = tag_category_result.candidates[0].content.parts[0].text.strip("```").replace("json", "", 1).strip()
                # JSON 파싱
                data = json.loads(clean_text)

                # tag, category 추출
                tags = data.get("tags", [])
                categories = data.get("categories", [])

            elif prompt_id == "5":
                image_urls = [res["image_url"] for res in uploaded_results]
                image_ids = [item["image_id"] for item in uploaded_results]
                # 첫번째 이미지를 대표 이미지로 썸네일 등록
                first_image_id = image_ids[0] if image_ids else None

                logger.info(f"image_urls: {image_urls}")
                content_request = ContentRequest(content=prompt.prompt.format(fact_checked_text=fact_checked_text, image_urls=image_urls))
                html_result = await content_generate_service.generate_content(content_request.model, content_request.content)
                logger.info(f"html_result: {html_result}")

                url = "http://app-address/create-post/"

                # Get Title, Content from HTML parsing
                parser = HtmlParser()
                title, content = parser.parse_for_wp_content(html_result)

                # 요청할 데이터 준비
                data = {
                    "title": title,
                    "content": content,
                    "categories": categories,
                    "tags": tags,
                    "image_id": first_image_id  # 필요 없으면 None 또는 "" 가능
                }

                await upload_content_to_api(data, f"{wordpress_api_url}:32552/posts/create-post/")

    finally:
        # 제너레이터 닫아 세션 종료
        try:
            next(db_generator)
        except StopIteration:
            pass

async def upload_images_to_api(image_paths, api_url):
    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0)) as client:
        results = []
        for image_path in image_paths:
            # 파일을 바이너리 모드로 연다
            with open(image_path, "rb") as f:
                files = {"image": (image_path, f, "image/png")}
                response = await client.post(api_url, files=files)
                response.raise_for_status()
                results.append(response.json())
        return results

async def upload_content_to_api(data, api_url):
    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0)) as client:
        response = await client.post(api_url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            return {
              "statusCode": response.status_code,
              "text": response.text
            }

if __name__ == "__main__":
    asyncio.run(main())