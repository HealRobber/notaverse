# 베이스 이미지: Python 3.13 slim 버전
FROM python:3.13-slim

# 작업 디렉토리 생성
WORKDIR /app
# 애플리케이션 코드 복사
COPY . .
# 필요한 라이브러리 설치
RUN pip install --no-cache-dir -r requirements.txt

ENV TZ=${TZ:-Asia/Seoul}

# CMD ["python", "-m", "cli", "run-once"]
# 임시 대기용 무한루프
# CMD ["tail", "-f", "/dev/null"]