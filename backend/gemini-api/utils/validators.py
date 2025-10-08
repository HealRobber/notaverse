import logging
from typing import Optional, Tuple
import re
from bs4 import BeautifulSoup
from utils.fallback_parser import naive_fallback

logger = logging.getLogger(__name__)

# --- 추가: 코드펜스 제거 ---
def _strip_code_fences(s: Optional[str]) -> str:
    if not s:
        return ""
    # 맨 앞의 ```lang 과 맨 끝의 ``` 를 1회씩 제거
    s = re.sub(r'^\s*```[a-zA-Z0-9_-]*\s*\n', '', s, count=1, flags=re.MULTILINE)
    s = re.sub(r'\n```[\s]*$', '', s, count=1, flags=re.MULTILINE)
    return s

def _strip_text(html_or_text: Optional[str]) -> str:
    if not html_or_text:
        return ""
    # 0) 코드펜스 언랩
    html_or_text = _strip_code_fences(html_or_text)
    # 1) HTML이면 태그 제거 후 공백 정리
    soup = BeautifulSoup(html_or_text, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())

def is_valid_title(title: Optional[str], min_len: int = 3) -> bool:
    t = _strip_text(title)
    return len(t) >= min_len

def is_valid_content(content: Optional[str], min_chars: int = 50) -> bool:
    # 본문은 태그 제거 후 최소 글자수로 간단하게 검증
    c = _strip_text(content)
    return len(c) >= min_chars

def validate_parsed(title: Optional[str], content: Optional[str],
                    min_title_len: int = 3, min_content_chars: int = 50) -> Tuple[bool, str]:
    if not is_valid_title(title, min_title_len):
        return False, f"invalid_title(len<{min_title_len})"
    if not is_valid_content(content, min_content_chars):
        return False, f"invalid_content(chars<{min_content_chars})"
    return True, "ok"

def safe_parse_and_validate(html_result_text: str, parser) -> Optional[Tuple[str, str]]:
    try:
        title, content = parser.parse_for_wp_content(html_result_text)
    except Exception as e:
        logger.exception("primary parse failed: %s", e)
        title, content = None, None

    ok, reason = validate_parsed(title, content)
    if not ok:
        # 폴백 시도
        fb_title, fb_content = naive_fallback(html_result_text)
        title = title or fb_title
        content = content or fb_content

    ok, reason = validate_parsed(title, content)
    if not ok:
        # 디버그: 길이/샘플 로그 (필요 시 on/off)
        raw_len = len(html_result_text or "")
        stripped_len = len(_strip_code_fences(html_result_text or ""))
        text_len = len(_strip_text(content or ""))
        logger.warning(
            "skip posting after fallback: %s (raw=%s, stripped=%s, text=%s)",
            reason, raw_len, stripped_len, text_len
        )
        return None

    return title, content
