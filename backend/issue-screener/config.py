from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # === MySQL 연결 정보 ===
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str = "database"
    DB_INTERNAL_PORT: int = 3306
    MANAGER_DB_NAME: str

    LOG_LEVEL: str = "INFO"
    TZ: str = "Asia/Seoul"

    @property
    def DB_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_INTERNAL_PORT}/{self.MANAGER_DB_NAME}"

settings = Settings()
