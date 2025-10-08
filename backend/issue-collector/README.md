# Notaverse Issue Collector (Docker Compose)

GDELT(전 세계), Reddit(r/all 지원), Naver(뉴스 Open API 또는 인기기사 랭킹 스크래핑)에서
이슈를 수집하여 PostgreSQL `topics` 테이블에 저장합니다.

## 준비
1) `.env` 값 채우기
   - `COLLECTOR_SCHEDULE_CRON=0 */3 * * *`  # 3시간마다
2) `docker compose up --build collector-scheduler`  # 주기 실행
   또는
   `docker compose up --build collector-run-once`   # 1회 실행

## 동작
- Reddit: `REDDIT_USE_ALL=true` 시 `/r/all`에서 Top/Hot을 시간대 기준으로 수집
- Naver: `NAVER_USE_RANKING_SCRAPE=true` 시 인기기사 페이지 스크래핑
         false 시 뉴스 Open API(쿼리 필수) 사용
- GDELT: 쿼리 문법으로 국가/언어/키워드 등 필터링 가능

## 테이블
topics(id, source, raw_id, title, summary, url, image_url, language, country, category,
       tags, score, published_at, collected_at, status, fingerprint, payload)

- fingerprint(title+url) unique로 중복 방지
- Notaverse gemini-api에서 status NEW를 가져가 CLAIMED/POSTED로 전이 추천
