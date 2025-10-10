from __future__ import annotations

import asyncio
import logging
import json
import re

from typing import Any, Optional, List, Dict
from sqlalchemy.orm import Session

import log_config
from common.http import robust_post_form
from services.db_service import get_db
from services.create_article_service import CreateArticleService
from services.content_generate_service import ContentGenerateService
from models.content_request import ContentRequest, ContentMessage
from settings import settings
from utils.visual_merge import process_visual_components_from_str

from common.llm import generate_text_with_retry, generate_images_with_retry


logger = logging.getLogger(__name__)

DEFAULT_TARGET_CHARS = 2000  # 없을 때 사용할 기본 글자 수

# ──────────────────────────────────────────────────────────────────────────────
# 내부 유틸
# ──────────────────────────────────────────────────────────────────────────────
FENCE_START_RE = re.compile(
    r"""^\s*(?P<fence>```|'''|~~~)\s*(?P<lang>[A-Za-z0-9_\-]*)\s*\r?\n""",
    re.DOTALL,
)

def extract_inner_if_fenced(text: str) -> str:
    """
    If the given text starts with a fenced code block (``` / ''' / ~~~),
    return ONLY the inner content of the first such block.
    Otherwise, return the original text unchanged.

    Examples:
      "''' html\\n<style>...</style>\\n'''"  -> "<style>...</style>"
      "```html\\n<style>...</style>\\n```"   -> "<style>...</style>"
      "<style>...</style>"                    -> "<style>...</style>" (unchanged)
    """
    if not isinstance(text, str):
        return text

    s = text.lstrip("\ufeff")  # trim BOM if present
    m = FENCE_START_RE.match(s)
    if not m:
        # doesn't start with a fence → return as-is
        return text

    fence = m.group("fence")
    # position right after the first line (the fence line)
    start_idx = m.end()
    # find the matching closing fence
    close_pat = re.compile(rf"\r?\n{re.escape(fence)}\s*$", re.DOTALL)
    close_m = close_pat.search(s, pos=start_idx)

    if not close_m:
        # no closing fence → fail-safe: return original
        return text

    inner = s[start_idx:close_m.start()]
    return inner.strip()

def _parse_prompt_ids(raw: str | List[int]) -> List[str]:
    """DB Text(JSON/CSV) → 문자열 ID 리스트"""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(int(x)) for x in raw]
    s = str(raw).strip()
    if not s:
        return []
    if s.startswith("[") and s.endswith("]"):
        try:
            arr = json.loads(s)
            return [str(int(x)) for x in arr]
        except Exception:
            pass
    return [p.strip() for p in s.split(",") if p.strip()]


def _pick_model(req: ContentRequest, override: Optional[str]) -> Optional[str]:
    """요청으로 들어온 llm_model이 우선, 없으면 ContentRequest.model"""
    return override or getattr(req, "model", None)


def parse_gemini_json_response(response_text: str):
    """
    Gemini 모델의 응답 텍스트에서 JSON 데이터를 파싱하여 Python 딕셔너리로 반환합니다.
    Args:
        response_text (str): Gemini 모델의 응답 텍스트.
    Returns:
        dict or None: 파싱된 JSON 데이터 (Python 딕셔너리) 또는 파싱 실패 시 None.
    """
    try:
        # 모델이 JSON 응답만 보내도록 프롬프트에서 요청했더라도,
        # 간혹 JSON 블록 외의 다른 텍스트를 포함할 수 있습니다.
        # 따라서 JSON 블록을 정확히 찾아 파싱하는 것이 안전합니다.
        # 보통 모델은 Markdown 코드 블록으로 JSON을 감싸서 줍니다.

        # Markdown JSON 코드 블록 찾기
        json_start_tag = "```json"
        json_end_tag = "```"

        start_index = response_text.find(json_start_tag)
        end_index = response_text.rfind(json_end_tag)  # 마지막 ```를 찾습니다.

        if start_index != -1 and end_index != -1 and start_index < end_index:
            # JSON 블록 추출
            json_str = response_text[start_index + len(json_start_tag):end_index].strip()
        else:
            # Markdown 블록이 없거나 형식이 다를 경우, 전체 응답을 JSON으로 시도
            logging.warning("JSON Markdown 블록을 찾을 수 없습니다. 전체 응답 텍스트로 JSON 파싱을 시도합니다.")
            json_str = response_text.strip()

        # JSON 문자열을 Python 딕셔너리로 파싱
        parsed_data = json.loads(json_str)
        logging.info("JSON 응답 파싱 성공.")
        return parsed_data

    except json.JSONDecodeError as e:
        logging.error(f"JSON 파싱 오류 발생: {e}")
        logging.error(f"파싱 시도 텍스트:\n{json_str[:500]}...")  # 에러 발생 시 앞부분만 출력
        return None
    except Exception as e:
        logging.error(f"예상치 못한 오류 발생: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# 단일 진입점: FastAPI/CLI 공용
# ──────────────────────────────────────────────────────────────────────────────
async def run_post_content_with_db(
    db: Session,
    *,
    topic: str,
    visual_component_count: int = 3,
    llm_model: Optional[str] = None,
    pipeline_id: int = 2,
    target_chars: Optional[int] = None,
) -> Dict[str, Any]:
    create_article_service = CreateArticleService()
    content_generate_service = ContentGenerateService()

    pipeline = create_article_service.fetch_pipeline(db, pipeline_id)
    prompt_ids = _parse_prompt_ids(pipeline.prompt_array)

    step_1_prompt: Optional[str] = None
    step_2_prompt: Optional[str] = None
    step_3_prompt: Optional[str] = None
    step_4_prompt: Optional[str] = None
    step_5_prompt: Optional[str] = None
    step_6_prompt: Optional[str] = None
    step_7_prompt: Optional[str] = None
    step_8_prompt: Optional[str] = None
    step_9_prompt: Optional[str] = None
    step_10_prompt: Optional[str] = None

    audience_type: Optional[str] = None

    generated_content: Optional[str] = None
    point_message: Optional[str] = None
    story_telling: Optional[str] = None
    fact_checked_text: Optional[str] = None
    fact_checked_text_with_ref: Optional[str] = None
    tuned_text: Optional[str] = None
    visual_aids_result: Optional[str] = None
    designed_text: Optional[str] = None
    optimized_text: Optional[str] = None

    categories: List[str] = []
    tags: List[str] = []

    title: Optional[str] = None

    first_id: Optional[int] = None

    uploaded_results: List[dict] = []

    post_resp: Optional[Dict[str, Any]] = None
    step_log: Dict[str, str] = {}

    tc = target_chars or DEFAULT_TARGET_CHARS

    for pid in prompt_ids:
        prompt_obj = create_article_service.fetch_prompt(db, int(pid))
        tmpl = prompt_obj.prompt

        try:
            if pid == "11":
                step_1_prompt = tmpl
                # 1) 토픽 이해 및 독자 분석
                # Prompt1 Content Parameter 생성
                formatted_step_1_prompt = step_1_prompt.format(topic=topic)
                print(f"formatted step_1_prompt: {formatted_step_1_prompt}")
                logger.info(f"step_1_prompt: {formatted_step_1_prompt}")
                contents_step1 = [
                    ContentMessage(role="user", parts=[formatted_step_1_prompt])
                ]
                print(f"contents_step1: {contents_step1}")
                req = ContentRequest(content=contents_step1)
                model = _pick_model(req, llm_model)
                if not model:
                    raise RuntimeError("No LLM model specified for step 1")
                generated_content = await generate_text_with_retry(
                    content_generate_service, model, req
                )

                parsed_json_data = parse_gemini_json_response(generated_content)
                if parsed_json_data:
                    # 파싱된 데이터를 변수에 담기
                    topic_analysis = parsed_json_data.get("topic_analysis")

                    if topic_analysis:
                        target_audience_info = topic_analysis.get("target_audience")
                        key_questions_list = topic_analysis.get("key_questions")
                        categories = topic_analysis.get("categories", [])
                        tags = topic_analysis.get("tags", [])
                        title = topic_analysis.get("title")

                        if target_audience_info:
                            audience_type = target_audience_info.get("type")
                            audience_description = target_audience_info.get("description")
                            tone = target_audience_info.get("tone_and_depth", {}).get("tone")
                            depth = target_audience_info.get("tone_and_depth", {}).get("depth")

                            print(f"가정된 독자층 유형: {audience_type}")
                            print(f"독자층 설명: {audience_description}")
                            print(f"포스팅 톤: {tone}, 깊이: {depth}")

                        if key_questions_list:
                            print("\n독자의 핵심 질문:")
                            for i, q in enumerate(key_questions_list):
                                print(f"{i + 1}. {q}")

                        if categories:
                            print(f"categories: {categories}")
                        if tags:
                            print(f"tags: {tags}")

                    else:
                        print("parsed_json_data에 'topic_analysis' 키가 없습니다.")

            elif pid == "12":
                step_2_prompt = tmpl
                # 2) 핵심 주장 / 메시지 뽑기
                if not generated_content:
                    raise RuntimeError("generated_content is empty")
                # Prompt2 Content Parameter 생성
                formatted_step_2_prompt = step_2_prompt.format(previous_step_output=generated_content)
                contents_step2 = [
                    ContentMessage(role="user", parts=[step_1_prompt]),
                    ContentMessage(role="model", parts=[generated_content]),
                    ContentMessage(role="user", parts=[formatted_step_2_prompt]),
                ]

                req = ContentRequest(content=contents_step2)
                model = _pick_model(req, llm_model)
                if not model:
                    raise RuntimeError("No LLM model specified for step 2")
                point_message = await generate_text_with_retry(
                    content_generate_service, model, req.content
                )
                step_log[pid] = f"point_message_len={len(point_message)}"
                logger.info(f"point_message: {point_message}")

            elif pid == "13":
                step_3_prompt = tmpl
                # 3) 스토리텔링 구조 설계
                if not point_message:
                    raise RuntimeError("point_message is empty")
                # Prompt3 Content Parameter 생성
                formatted_step_3_prompt = step_3_prompt.format(previous_step_output=point_message)
                contents_step3 = [
                    ContentMessage(role="user", parts=[step_2_prompt]),
                    ContentMessage(role="model", parts=[point_message]),
                    ContentMessage(role="user", parts=[formatted_step_3_prompt]),
                ]

                req = ContentRequest(content=contents_step3)
                model = _pick_model(req, llm_model)
                if not model:
                    raise RuntimeError("No LLM model specified for step 3")
                story_telling = await generate_text_with_retry(
                    content_generate_service, model, req.content
                )
                step_log[pid] = f"story_telling_len={len(story_telling)}"
                logger.info(f"story_telling: {story_telling}")

            elif pid == "14":
                step_4_prompt = tmpl
                # 4) 팩트 기반 초안 작성 (with Fact-check Requests)
                if not story_telling:
                    raise RuntimeError("story_telling is empty")
                # Prompt4 Content Parameter 생성
                formatted_step_4_prompt = step_4_prompt.format(tc=tc, previous_step_output=story_telling)
                logger.info(f"formatted_step_4_prompt: {formatted_step_4_prompt}")
                contents_step4 = [
                    ContentMessage(role="user", parts=[step_3_prompt]),
                    ContentMessage(role="model", parts=[story_telling]),
                    ContentMessage(role="user", parts=[formatted_step_4_prompt]),
                ]

                req = ContentRequest(content=contents_step4)
                model = _pick_model(req, llm_model)
                if not model:
                    raise RuntimeError("No LLM model specified for step 4")
                fact_checked_text = await generate_text_with_retry(
                    content_generate_service, model, req.content
                )
                step_log[pid] = f"fact_checked_text_len={len(fact_checked_text)}"
                logger.info(f"fact_checked_text: {fact_checked_text}")

            elif pid == "15":
                step_5_prompt = tmpl
                # 5) 팩트체크 & 출처 자동 삽입
                if not fact_checked_text:
                    raise RuntimeError("fact_checked_text is empty")
                # Prompt5 Content Parameter 생성
                formatted_step_5_prompt = step_5_prompt.format(previous_step_output=fact_checked_text)
                logger.info(f"formatted_step_5_prompt: {formatted_step_5_prompt}")
                contents_step5 = [
                    ContentMessage(role="user", parts=[step_4_prompt]),
                    ContentMessage(role="model", parts=[fact_checked_text]),
                    ContentMessage(role="user", parts=[formatted_step_5_prompt]),
                ]

                req = ContentRequest(content=contents_step5)
                model = _pick_model(req, llm_model)
                if not model:
                    raise RuntimeError("No LLM model specified for step 5")
                fact_checked_text_with_ref = await generate_text_with_retry(
                    content_generate_service, model, req.content
                )
                step_log[pid] = f"fact_checked_text_with_ref_len={len(fact_checked_text_with_ref)}"
                logger.info(f"fact_checked_text_with_ref: {fact_checked_text_with_ref}")

            elif pid == "16":
                step_6_prompt = tmpl
                # 6) 가독성 & 톤 조정 (독자 맞춤)
                if not fact_checked_text_with_ref:
                    raise RuntimeError("fact_checked_text_with_ref is empty")
                # Prompt6 Content Parameter 생성
                formatted_step_6_prompt = step_6_prompt.format(audience_type=audience_type, previous_step_output=fact_checked_text_with_ref)
                logger.info(f"formatted_step_6_prompt: {formatted_step_6_prompt}")
                contents_step6 = [
                    ContentMessage(role="user", parts=[step_5_prompt]),
                    ContentMessage(role="model", parts=[fact_checked_text_with_ref]),
                    ContentMessage(role="user", parts=[formatted_step_6_prompt]),
                ]

                req = ContentRequest(content=contents_step6)
                model = _pick_model(req, llm_model)
                if not model:
                    raise RuntimeError("No LLM model specified for step 6")
                tuned_text = await generate_text_with_retry(
                    content_generate_service, model, req.content
                )
                step_log[pid] = f"tuned_text_len={len(tuned_text)}"
                logger.info(f"tuned_text: {tuned_text}")

            elif pid == "17":
                step_7_prompt = tmpl
                # 7) 시각화 요소 설계 (텍스트+이미지)
                if not tuned_text:
                    raise RuntimeError("tuned_text is empty")
                # Prompt7 Content Parameter 생성
                formatted_step_7_prompt = step_7_prompt.format(n=visual_component_count, previous_step_output=tuned_text)
                logger.info(f"formatted_step_6_prompt: {formatted_step_7_prompt}")
                contents_step7 = [
                    ContentMessage(role="user", parts=[step_6_prompt]),
                    ContentMessage(role="model", parts=[tuned_text]),
                    ContentMessage(role="user", parts=[formatted_step_7_prompt]),
                ]

                req = ContentRequest(content=contents_step7)
                model = _pick_model(req, llm_model)
                if not model:
                    raise RuntimeError("No LLM model specified for step 7")
                visual_components = await generate_text_with_retry(
                    content_generate_service, model, req.content
                )
                step_log[pid] = f"visual_components_len={len(visual_components)}"
                logger.info(f"visual_components: {visual_components}")

                upload_url = f"{settings.wordpress_base}/posts/upload-image/"

                visual_aids_result, first_id = await process_visual_components_from_str(
                    raw_json=visual_components,
                    content_generate_service=content_generate_service,
                    upload_url=upload_url,
                    use_first_image_only=False
                )
                step_log[pid] = f"visual_aids_result_len={len(visual_aids_result)}"
                logger.info(f"visual_aids_result: {visual_aids_result} / first_id: {first_id}")

            elif pid == "18":
                step_8_prompt = tmpl
                # 8) HTML 변환 + 디자인 가이드
                if not visual_aids_result:
                    raise RuntimeError("visual_aids_result is empty")
                # Prompt8 Content Parameter 생성
                formatted_step_8_prompt = step_8_prompt.format(previous_step_output_6=tuned_text, previous_step_output_7=visual_aids_result)
                logger.info(f"formatted_step_8_prompt: {formatted_step_8_prompt}")
                contents_step8 = [
                    ContentMessage(role="user", parts=[step_6_prompt]),
                    ContentMessage(role="model", parts=[tuned_text]),
                    ContentMessage(role="user", parts=[step_7_prompt]),
                    ContentMessage(role="model", parts=[json.dumps(visual_aids_result, ensure_ascii=False)]),
                    ContentMessage(role="user", parts=[formatted_step_8_prompt]),
                ]

                req = ContentRequest(content=contents_step8)
                model = _pick_model(req, llm_model)
                if not model:
                    raise RuntimeError("No LLM model specified for step 8")
                designed_text = await generate_text_with_retry(
                    content_generate_service, model, req.content
                )
                step_log[pid] = f"designed_text_len={len(designed_text)}"
                logger.info(f"designed_text: {designed_text}")

                # upload_content = extract_html_from_finalized_content(designed_text)
                # if upload_content is None:
                #     raise ValueError("HTML 코드 블록을 찾지 못했습니다.")
                upload_content = extract_inner_if_fenced(designed_text)

                post_data = {
                    "title": title,
                    "content": upload_content,
                    "categories": categories,
                    "tags": tags,
                    "image_id": first_id,
                }
                create_url = f"{settings.wordpress_base}/posts/create-post/"
                post_resp = await robust_post_form(create_url, post_data)
                step_log[pid] = "post_done"

            else:
                step_log[pid] = "unknown_step_skipped"

        except Exception as e:
            logger.exception("[step %s] failed: %s", pid, e)
            step_log[pid] = f"error:{e}"
            # 필요시 raise로 전체 중단하도록 변경 가능

    safe_post_summary = None
    if isinstance(post_resp, dict):
        safe_post_summary = {
            k: post_resp.get(k) for k in ("id", "link", "slug", "status") if k in post_resp
        }

    return {
        "pipeline_id": pipeline_id,
        "topic": topic,
        "visual_component_count": visual_component_count,
        "llm_model": llm_model,
        "steps": step_log,
        "tags": tags,
        "categories": categories,
        "uploaded_images": len(uploaded_results),
        "post": safe_post_summary,
    }


# ──────────────────────────────────────────────────────────────────────────────
# CLI 용 래퍼(옵션): 동일 로직 재사용
# ──────────────────────────────────────────────────────────────────────────────
async def run_post_content(
    *, topic: str, visual_component_count: int = 3, llm_model: Optional[str] = None
) -> Dict[str, Any]:
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        return await run_post_content_with_db(
            db, topic=topic, visual_component_count=visual_component_count, llm_model=llm_model
        )
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    # parser.add_argument("--topic", required=True)
    parser.add_argument("--topic", type=str, default="Affordable housing developer sues City of Sioux Falls")
    parser.add_argument("--visual-component-count", type=int, default=3)
    parser.add_argument("--llm-model", type=str, default=None)
    parser.add_argument("--pipeline-id", type=int, default=2)
    parser.add_argument("--target-chars", type=int, default=None)
    args = parser.parse_args()

    asyncio.run(
        run_post_content_with_db(
            db=next(get_db()),
            topic=args.topic,
            visual_component_count=args.visual_component_count,
            llm_model=args.llm_model,
            pipeline_id=args.pipeline_id,
            target_chars=args.target_chars,
        )
    )