# utils/db_utils.py
from __future__ import annotations
import uuid
from typing import Mapping, Any, Optional, Iterable

from sqlalchemy import MetaData, Table
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from loguru import logger

def _get_topic_table(session: Session, table_name: str = "topic") -> Table:
    metadata = MetaData()
    return Table(table_name, metadata, autoload_with=session.bind)

def insert_topic_dedup(
    session: Session,
    row: Mapping[str, Any],
    *,
    table_name: str = "topic",
    id_field: Optional[str] = None,             # AUTO_INCREMENT면 None, UUID PK면 "id"
    unique_cols: tuple[str, str] = ("source", "raw_id"),
) -> bool:
    """
    (source, raw_id) UNIQUE 전제로 '중복 무시' insert.
    - PostgreSQL: ON CONFLICT DO NOTHING
    - MySQL/MariaDB: ON DUPLICATE KEY UPDATE (no-op)
    - 기타: 일반 INSERT 후 IntegrityError 캐치
    return: True(신규 insert), False(중복/무시)
    """
    topic_tbl = _get_topic_table(session, table_name)
    data = dict(row)

    # UUID PK 스키마 지원
    if id_field and id_field in topic_tbl.c and not data.get(id_field):
        data[id_field] = str(uuid.uuid4())

    dialect = session.bind.dialect.name  # 'postgresql' | 'mysql' | 'mariadb' | ...

    try:
        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(topic_tbl).values(**data).on_conflict_do_nothing(
                index_elements=list(unique_cols)
            )
            session.execute(stmt)
            session.commit()
            return True

        elif dialect in ("mysql", "mariadb"):
            from sqlalchemy.dialects.mysql import insert as my_insert
            stmt = my_insert(topic_tbl).values(**data)
            # no-op 업데이트: 유니크 키 컬럼을 자기 자신으로 덮어쓰기
            upd = {col: stmt.inserted[col] for col in unique_cols if col in topic_tbl.c}
            if not upd:
                # 안전장치: 테이블 첫 컬럼이라도 no-op
                first_col = list(topic_tbl.c.keys())[0]
                upd = {first_col: getattr(topic_tbl.c, first_col)}
            stmt = stmt.on_duplicate_key_update(**upd)
            session.execute(stmt)
            session.commit()
            return True

        else:
            # 기타 DB
            stmt = topic_tbl.insert().values(**data)
            try:
                session.execute(stmt)
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False

    except IntegrityError:
        session.rollback()
        return False
    except Exception as e:
        session.rollback()
        logger.exception("insert_topic_dedup failed: {}", e)
        raise

def bulk_insert_topics_dedup(
    session: Session,
    rows: Iterable[Mapping[str, Any]],
    *,
    table_name: str = "topic",
    id_field: Optional[str] = None,
    unique_cols: tuple[str, str] = ("source", "raw_id"),
) -> tuple[int, int]:
    """
    여러 건을 순차 삽입. 각 건은 insert_topic_dedup 로직을 따릅니다.
    return: (inserted_count, skipped_count)
    """
    inserted, skipped = 0, 0
    for row in rows:
        ok = insert_topic_dedup(session, row, table_name=table_name, id_field=id_field, unique_cols=unique_cols)
        if ok:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped
