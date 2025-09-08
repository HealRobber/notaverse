# 베이스 이미지: Python 3.13 slim 버전
FROM python:3.13-slim

# 작업 디렉토리 생성
WORKDIR /app
# Shared Volume용 폴더 생성
RUN mkdir /app/images
# 애플리케이션 코드 복사
COPY . .
# 필요한 라이브러리 설치
RUN pip install --no-cache-dir -r requirements.txt

# FastAPI 앱 실행 (Uvicorn)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "32553", "--reload"]