import requests
from requests.auth import HTTPBasicAuth
from fastapi import UploadFile
from dotenv import load_dotenv
from typing import Tuple, List
import os

class WordPressService:
    # .env 파일 로드
    load_dotenv()
    WP_SITE = os.getenv("WP_SITE")
    WORDPRESS_USER_NAME = os.getenv("WORDPRESS_USER_NAME")
    WORDPRESS_API_PASSWORD = os.getenv("WORDPRESS_API_PASSWORD")

    # API AUTH 세팅
    AUTH = HTTPBasicAuth(WORDPRESS_USER_NAME, WORDPRESS_API_PASSWORD)

    CF_HEADERS = {
        "Host": "www.notaverse.org",
        "X-Forwarded-Proto": "https",
    }

    # CATEGORY LIST 생성
    def create_category(self, categories: List[str]) -> Tuple[List[int], List[str]]:
        category_ids = []
        failed_categories = []

        for category in categories:
            print(category)
            url = f'{self.WP_SITE}/wp-json/wp/v2/categories'
            res = requests.post(url, json={'name': category}, auth=self.AUTH, headers=self.CF_HEADERS)
            if res.status_code == 201:
                category_ids.append(res.json()['id'])
            elif res.status_code == 400 and 'term_id' in res.json()['data']:
                category_ids.append(res.json()['data']['term_id'])
            else:
                failed_categories.append(category)
                print(f"[category 생성 실패] '{category}': {res.status_code} {res.text}")

        return category_ids, failed_categories

    # TAG LIST 생성
    def create_tags(self, tags: List[str]) -> Tuple[List[int], List[str]]:
        tag_ids = []
        failed_tags = []

        for tag in tags:
            print(tag)
            url = f'{self.WP_SITE}/wp-json/wp/v2/tags'
            res = requests.post(url, json={'name': tag}, auth=self.AUTH, headers=self.CF_HEADERS)
            if res.status_code == 201:
                tag_ids.append(res.json()['id'])
            elif res.status_code == 400 and 'term_id' in res.json()['data']:
                tag_ids.append(res.json()['data']['term_id'])
            else:
                failed_tags.append(tag)
                print(f"[tag 생성 실패] '{tag}': {res.status_code} {res.text}")
        
        return tag_ids, failed_tags

    # 이미지 업로드 처리
    def upload_image(self, file: UploadFile):
        url = f'{self.WP_SITE}/wp-json/wp/v2/media'
        files = {
            'file': (file.filename, file.file, file.content_type)
        }
        res = requests.post(
                    url,
                    files=files,
                    auth=self.AUTH,
                    headers=self.CF_HEADERS
                )
        print("has Authorization header?:", "Authorization" in res.request.headers)
        print("status:", res.status_code)
        print("body:", res.text)
        if res.status_code == 201:
            media = res.json()
            return media['source_url']  # 이미지 URL만 반환
        else:
            return None

    # 이미지 URL로 ID 가져오기
    def get_image_id(self, image_url):
        # 파일명 추출
        filename = image_url.rstrip('/').split('/')[-1]

        # 검색 쿼리
        params = {
            'search': filename,
            'per_page': 10  # 검색 결과 최대 10개
        }

        url = f'{self.WP_SITE}/wp-json/wp/v2/media'

        response = requests.get(url, params=params, auth=self.AUTH, headers=self.CF_HEADERS)
        if response.status_code != 200:
            print(f"Failed to fetch media: {response.status_code} {response.text}")
            return None

        media_items = response.json()
        # 정확히 URL 일치하는 미디어 찾기
        for item in media_items:
            if 'source_url' in item and item['source_url'] == image_url:
                return item['id']
        return None


    # 글 등록
    def create_post(self, title, content, categories, tags, featured_media_id=None):
        url = f'{self.WP_SITE}/wp-json/wp/v2/posts'
        
        data = {
            'title': title,
            'content': content,
            'status': 'publish',
            'categories': categories,
            'tags': tags,
        }
        
        if featured_media_id:
            data['featured_media'] = featured_media_id

        print(f"data: {data}")

        res = requests.post(url, json=data, auth=self.AUTH, headers=self.CF_HEADERS)
        if res.status_code == 201:
            return res.json()
        else:
            return None