from sqlalchemy import select, func
from sqlalchemy.orm import Session
from models.autogen_models import Series, SeriesEpisode, ContentJob
from models.enums import EpisodeStatus, JobType

# Gemini 호출부 래퍼
from services.auto_gen.gemini_client import generate_outline_title


def plan_next_episode(db: Session, series_id: int) -> None:
    """
    - 다음 회차 번호 계산 (MAX + 1)
    - 최근 발행 요약을 참고하여 아웃라인/제목 생성
    - planned 에피소드 레코드 생성
    - 바로 이어서 WRITE_AND_POST 잡 생성
    """
    # 다음 episode_no
    max_no = db.execute(
        select(func.coalesce(func.max(SeriesEpisode.episode_no), 0))
        .where(SeriesEpisode.series_id == series_id)
    ).scalar_one()
    next_no = max_no + 1

    # 최근 5개 요약(posted)
    recent_summaries = db.execute(
        select(SeriesEpisode.summary)
        .where(
            SeriesEpisode.series_id == series_id,
            SeriesEpisode.status == EpisodeStatus.posted
        )
        .order_by(SeriesEpisode.episode_no.desc())
        .limit(5)
    ).scalars().all()

    series = db.get(Series, series_id)
    if not series:
        raise ValueError(f"Series not found: {series_id}")

    outline, planned_title = generate_outline_title(
        series_title=series.title,
        seed_topic=series.seed_topic,
        recent_summaries=[s for s in recent_summaries if s],
        next_episode_no=next_no
    )

    # planned 에피소드 생성
    ep = SeriesEpisode(
        series_id=series_id,
        episode_no=next_no,
        planned_title=planned_title,
        planned_outline=outline,
        status=EpisodeStatus.planned,
    )
    db.add(ep)
    db.flush()  # ep.id 확보

    # 이어서 WRITE_AND_POST 잡 생성
    job = ContentJob(
        job_type=JobType.WRITE_AND_POST,
        payload={"series_id": series_id, "episode_no": next_no, "pipeline_id": series.pipeline_id},
    )
    db.add(job)
