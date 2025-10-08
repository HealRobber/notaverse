from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # === MySQL 연결 정보 ===
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str = "database"
    DB_INTERNAL_PORT: int = 3306
    MANAGER_DB_NAME: str

    # GDELT
    GDELT_QUERY: str = "(news OR politics OR economy OR technology OR sports OR entertainment OR business OR world)"
    GDELT_TIMESPAN: str = "3h"
    GDELT_MAX_RECORDS: int = 10
    # 폴백/자동확장 옵션(신규)
    GDELT_FALLBACK_QUERY: str = ""
    GDELT_AUTOWIDEN_ON_EMPTY: bool = True  # 0건이면 timespan을 48h → 72h 순으로 넓혀 시도
    GDELT_AUTOWIDEN_STEPS: str = "6h,12h,24h"
    GDELT_LANGUAGE: str = "English"
    GDELT_REQUIRE_IMAGE: bool = True

    # Reddit
    REDDIT_CLIENT_ID: str
    REDDIT_CLIENT_SECRET: str
    REDDIT_USER_AGENT: str = "notaverse-collector/1.0"
    REDDIT_USE_ALL: bool = False
    REDDIT_SUBREDDITS: str = "worldnews,news,technology,Korea"
    REDDIT_LISTING: str = "top"
    REDDIT_TIME_FILTER: str = "hour"
    REDDIT_LIMIT: int = 10

    # Naver API
    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""
    NAVER_NEWS_QUERIES: str = "속보,경제,부동산,주식,금리,환율,청년,정부 발표,대출,연말정산"
    NAVER_DISPLAY: int = 20
    NAVER_SORT: str = "date"

    # 수집량/기간/중복 제어(신규)
    NAVER_MAX_PER_QUERY: int = 30  # 각 키워드 최대 생성 개수(0은 무제한)
    NAVER_MAX_AGE_HOURS: int = 24  # pubDate 기준 최근 N시간 이내만
    NAVER_DEDUP_BY_URL: bool = True  # 동일 URL 중복 제거

    # Naver 대안: 랭킹(인기기사) 스크래핑 모드
    NAVER_USE_RANKING_SCRAPE: bool = True  # true면 Open API 대신 인기기사 페이지 스크래핑
    NAVER_RANKING_SECTIONS: str = "all"  # all 또는 "100,101,102,103,104,105"
    NAVER_MAX_TOTAL: int = 10  # 전체 수집 상한(0은 무제한)
    NAVER_MAX_PER_SECTION: int = 0
    NAVER_DEDUP_BY_URL: bool = True

    # Scheduler (변경된 변수명)
    COLLECTOR_SCHEDULE_CRON: str = "0 */3 * * *"  # 기본: 3시간마다
    LOG_LEVEL: str = "INFO"
    TZ: str = "Asia/Seoul"

    @property
    def DB_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_INTERNAL_PORT}/{self.MANAGER_DB_NAME}"

settings = Settings()
