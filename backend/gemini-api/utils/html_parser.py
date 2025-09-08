from typing import Tuple, Any
import re
from bs4 import BeautifulSoup
import bleach

class HtmlParser:

    ALLOWED_TAGS = [
        "p","h2","h3","h4","h5","h6",
        "ul","ol","li",
        "strong","em","b","i","u",
        "blockquote","hr","br",
        "a","img",
        "figure","figcaption",
        "pre","code",
        "table","thead","tbody","tr","th","td",
        "div","span"
    ]
    ALLOWED_ATTRS = {
        "*": ["class"],
        "a": ["href","title","target","rel"],
        "img": ["src","alt","title","width","height"]
    }
    ALLOWED_PROTOCOLS = ["http","https","mailto"]

    # --------------------------
    # 공통: 어떤 SDK 응답이든 문자열로 정규화
    # --------------------------
    def _to_text(self, raw: Any) -> str:
        if raw is None:
            return ""

        if isinstance(raw, str):
            return raw

        if isinstance(raw, bytes):
            try:
                return raw.decode("utf-8", errors="ignore")
            except Exception:
                return str(raw)

        # Gemini 스타일 (google-generativeai)
        # - resp.text
        if hasattr(raw, "text") and isinstance(getattr(raw, "text"), str):
            return raw.text

        # - resp.candidates[0].content.parts[*].text
        try:
            candidates = getattr(raw, "candidates", None)
            if candidates:
                texts = []
                for c in candidates:
                    content = getattr(c, "content", None)
                    if content:
                        parts = getattr(content, "parts", None)
                        if parts:
                            for p in parts:
                                t = getattr(p, "text", None)
                                if isinstance(t, str):
                                    texts.append(t)
                if texts:
                    return "\n\n".join(texts)
        except Exception:
            pass

        # OpenAI 스타일 (responses API 혹은 chat.completions)
        # - resp.choices[0].message.content or .text
        try:
            choices = getattr(raw, "choices", None)
            if choices:
                ch0 = choices[0]
                msg = getattr(ch0, "message", None)
                if msg and isinstance(getattr(msg, "content", None), str):
                    return msg.content
                if isinstance(getattr(ch0, "text", None), str):
                    return ch0.text
        except Exception:
            pass

        # 마지막 수단
        return str(raw)

    def _extract_html_block(self, raw_text_like: Any) -> str:
        """
        SDK 응답(객체/문자열)을 받아서 <html>...</html> 블록만 추출.
        없으면 원문 전체를 반환.
        """
        text = self._to_text(raw_text_like)

        # 가장 먼저 진짜 HTML 루트 요소를 찾음
        m = re.search(r"<html[\s\S]*?</html>", text, re.IGNORECASE)
        if m:
            return m.group(0).strip()

        # 과거 정규식 호환(느슨한 패턴): 'html' 이후 전체
        m2 = re.search(r"html(.*?)", text, re.DOTALL | re.IGNORECASE)
        if m2:
            return m2.group(1).strip()

        # 아무 매치가 없으면 전체 반환
        return text

    def _sanitize_for_wp(self, html_fragment: str) -> str:
        """
        워드프레스 업로드용으로 보수적으로 정화.
        - 허용 태그/속성만 유지
        - 링크 target 있으면 rel 보강
        - img 인라인 style 제거
        """
        cleaned = bleach.clean(
            html_fragment,
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRS,
            protocols=self.ALLOWED_PROTOCOLS,
            strip=True
        )

        # 파서는 lxml 우선, 실패 시 기본 파서로 폴백
        try:
            soup = BeautifulSoup(cleaned, "lxml")
        except Exception:
            soup = BeautifulSoup(cleaned, "html.parser")

        # 링크 보강: target이 있는데 rel 없으면 보안 속성 추가
        for a in soup.find_all("a"):
            if a.get("target") and not a.get("rel"):
                a["rel"] = "noopener noreferrer"

        # 이미지 인라인 스타일 제거(테마에 맡김)
        for img in soup.find_all("img"):
            if "style" in img.attrs:
                del img["style"]

        return str(soup)

    def parse_for_wp_content(
        self,
        raw_sdk_text: Any,
        remove_first_heading_in_body: bool = True,
        do_sanitize: bool = True
    ) -> Tuple[str, str]:
        """
        입력: SDK 응답 전체(객체/문자열 모두 허용)
        출력: (title, content_html)
        - title: <title> 또는 본문 첫 h1/h2(타이틀 비었거나 짧으면 대체)
        - content_html: <body> 내부(innerHTML)만, 필요 시 sanitize 적용
        """
        html = self._extract_html_block(raw_sdk_text)

        # 파서는 lxml 우선, 실패 시 기본 파서로 폴백
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")

        # 스크립트/스타일 제거
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # 제목 후보: <title>
        title_text = (soup.title.get_text(strip=True) if soup.title else "").strip()

        # body 기준으로 추출(없으면 문서 전체 사용)
        body = soup.body or soup

        # 본문 첫 h1/h2를 제목 대체 후보로 사용
        first_heading = body.find(["h1", "h2"])
        if first_heading:
            heading_text = first_heading.get_text(strip=True)
            if not title_text or len(title_text) < 5:
                title_text = heading_text
            if remove_first_heading_in_body:
                first_heading.decompose()  # 본문 중복 방지

        # 최종 본문(innerHTML)
        body_inner_html = body.decode_contents()

        # 타이틀 백업
        if not title_text:
            fallback_text = soup.get_text(separator=" ", strip=True)
            title_text = (fallback_text[:60] + "…") if len(fallback_text) > 60 else (fallback_text or "Untitled")

        # 정화 옵션
        if do_sanitize:
            body_inner_html = self._sanitize_for_wp(body_inner_html)

        return title_text, body_inner_html
