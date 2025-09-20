# services/db_service.py
from typing import Generator
from sqlalchemy.orm import Session

# 프로젝트 구조에 맞춰 경로 조정 (예: package 루트가 app 라면 from app.db import get_db)
from db import get_db as _get_db, get_session_factory as _get_session_factory, create_tables as _create_tables


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI Depends에서 사용.
    기존 "from services.db_service import get_db" 는 그대로 유지.
    내부적으로 app/db.py의 get_db를 위임 호출합니다.
    """
    yield from _get_db()


# (선택) 필요 시 직접 세션 팩토리가 필요한 곳을 위한 헬퍼들도 노출
get_session_factory = _get_session_factory
create_tables = _create_tables
