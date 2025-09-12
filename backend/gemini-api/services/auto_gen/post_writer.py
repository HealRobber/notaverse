from sqlalchemy import select
from sqlalchemy.orm import Session
from models.autogen_models import Series, SeriesEpisode, Post, Image
from models.enums import EpisodeStatus

from services.auto_gen.gemini_client import generate_content_and_images
from services.auto_gen.wp_rest_client import upload_images, create_post
from services.auto_gen.taxonomy import extract_taxonomy
from utils.html_parser import HtmlParser  # 기존에 사용하시던 파서

import logging

logger = logging.getLogger(__name__)

def make_short_summary(content_html: str) -> str:
    return (content_html[:1000] + "...") if len(content_html) > 1000 else content_html

def write_and_post(db: Session, series_id: int, episode_no: int) -> None:
    ep = db.execute(
        select(SeriesEpisode)
        .where(
            SeriesEpisode.series_id == series_id,
            SeriesEpisode.episode_no == episode_no
        )
        .with_for_update()
    ).scalar_one_or_none()
    if not ep:
        raise ValueError(f"planned episode not found: series={series_id}, ep={episode_no}")

    series = db.get(Series, series_id)
    if not series:
        raise ValueError(f"Series not found: {series_id}")

    ep.status = EpisodeStatus.posting

    # 1) 본문/이미지 생성 (Gemini)
    content_html, image_paths = generate_content_and_images(
        planned_title=ep.planned_title,
        outline=ep.planned_outline or "",
        pipeline_id=series.pipeline_id
    )

    # 2) 이미지 업로드 (REST API → image_id/image_url 응답)
    uploaded = upload_images(image_paths or [])
    image_ids = [r.get("image_id") for r in uploaded if isinstance(r, dict) and r.get("image_id") is not None]
    image_urls = [r.get("image_url") for r in uploaded if isinstance(r, dict) and r.get("image_url")]
    featured_media_id = image_ids[0] if image_ids else None

    # 로컬 DB(images) 기록(옵션)
    for url, iid in zip(image_urls, image_ids):
        db.add(Image(image_url=url, image_id=int(iid)))

    # 3) 제목/본문 분리(파서)
    parser = HtmlParser()
    title, content_body = parser.parse_for_wp_content(content_html)
    logger.info(f"[gemini_client] title : {title} / content : {content_body}")

    # 4) 카테고리/태그 추출 (LLM → 휴리스틱 폴백)
    cats, tgs = extract_taxonomy(
        title=title,
        content_html=content_body,
        seed_topic=series.seed_topic if series else None,
        max_categories=1,
        max_tags=7,
    )
    logger.info("[taxonomy] cats=%s, tags=%s", cats, tgs)

    # 5) 포스트 생성 (REST JSON)
    resp = create_post(
        title=title,
        content=content_body,
        categories=cats,
        tags=tgs,
        image_id=featured_media_id,
    )

    # 5) 로컬 posts 기록 및 에피소드 완료 처리
    post = Post(
        title=title,
        content=content_body,
        category_ids="",  # REST 서버에서 최종 매핑/저장하므로 로컬은 비워둠(옵션)
        tag_ids="",
        featured_media_id=featured_media_id or 0,
        series_id=series_id,
        episode_no=episode_no,
    )
    db.add(post)
    db.flush()

    ep.post_id = post.id
    ep.summary = make_short_summary(post.content)
    ep.status = EpisodeStatus.posted
