# settings.py (추가/수정)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Dict, Any
from urllib.parse import quote_plus

class Settings(BaseSettings):
    # === Scheduler / Misc ===
    schedule_cron: str = "0 * * * *"
    run_token: str = "itengz"
    redis_url: Optional[str] = None

    # === MySQL 연결 정보 ===
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str = "database"
    DB_INTERNAL_PORT: int = 3306
    MANAGER_DB_NAME: str

    # === 커넥션 풀/엔진 옵션 ===
    DB_ECHO: bool = True
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE_SEC: int = 1800
    DB_POOL_PRE_PING: bool = True
    DB_POOL_TIMEOUT_SEC: int = 30

    # 드라이버 타임아웃
    DB_CONNECT_TIMEOUT_SEC: int = 10
    DB_READ_TIMEOUT_SEC: int = 30
    DB_WRITE_TIMEOUT_SEC: int = 30

    # === HTTP/외부 API 공통 ===
    WORDPRESS_API_BASE: str = "http://wordpressapi:32552"
    STEP_MAX_RETRIES: int = 3
    STEP_MAX_BACKOFF: int = 20
    HTTP_TIMEOUT_SEC: float = 180.0

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def wordpress_base(self) -> str:
        return self.WORDPRESS_API_BASE.rstrip("/")

    @property
    def database_url_sync(self) -> str:
        user = quote_plus(self.DB_USER)
        pwd = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+pymysql://{user}:{pwd}@{self.DB_HOST}:{self.DB_INTERNAL_PORT}/{self.MANAGER_DB_NAME}"
            f"?charset=utf8mb4"
            f"&connect_timeout={self.DB_CONNECT_TIMEOUT_SEC}"
            f"&read_timeout={self.DB_READ_TIMEOUT_SEC}"
            f"&write_timeout={self.DB_WRITE_TIMEOUT_SEC}"
        )

    @property
    def database_url_async(self) -> str:
        user = quote_plus(self.DB_USER)
        pwd = quote_plus(self.DB_PASSWORD)
        return f"mysql+aiomysql://{user}:{pwd}@{self.DB_HOST}:{self.DB_INTERNAL_PORT}/{self.MANAGER_DB_NAME}?charset=utf8mb4"

    def sync_engine_kwargs(self) -> Dict[str, Any]:
        return {
            "echo": self.DB_ECHO,
            "pool_pre_ping": self.DB_POOL_PRE_PING,
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
            "pool_recycle": self.DB_POOL_RECYCLE_SEC,
            "pool_timeout": self.DB_POOL_TIMEOUT_SEC,
            "future": True,
        }

    def async_engine_kwargs(self) -> Dict[str, Any]:
        return {
            "echo": self.DB_ECHO,
            "pool_pre_ping": self.DB_POOL_PRE_PING,
            "pool_recycle": self.DB_POOL_RECYCLE_SEC,
            "future": True,
        }

settings = Settings()
