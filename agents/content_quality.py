"""Final content quality gate for Ajin Networks blog posts."""

import re

MIN_CONTENT_CHARS = 1200
MIN_DETERMINISTIC_CHARS = 1500
MIN_REVIEW_SCORE = 80

TECH_TERMS = [
    "PLC", "로봇", "Robot", "비전", "Vision", "Cycle Time", "사이클타임",
    "인터록", "안전", "PoC", "ROI", "생산성", "기구", "제어", "OEE",
]

UNSUPPORTED_NUMBER_PATTERNS = [
    re.compile(r"\b\d{1,3}%\s*(?:향상|개선|절감|감소|증가)"),
    re.compile(r"\b\d+(?:\.\d+)?배\s*(?:향상|증가|개선)"),
]


def _content_text(post: dict) -> str:
    raw = post.get("content", "")
    if isinstance(raw, list):
        return "\n".join(str(x) for x in raw)
    return str(raw or "")


def _provider(post: dict) -> str:
    return str(post.get("generation_provider") or post.get("provider") or "unknown")


def evaluate_content_quality(post: dict) -> dict:
    content = _content_text(post)
    compact_len = len(re.sub(r"\s+", "", content))
    provider = _provider(post)
    min_chars = MIN_DETERMINISTIC_CHARS if provider == "deterministic" else MIN_CONTENT_CHARS

    sections = len(re.findall(r"^##\s+", content, flags=re.MULTILINE))
    technical_hits = sorted({term for term in TECH_TERMS if term.lower() in content.lower()})
    review_score = int(post.get("review_result", {}).get("total_score") or 0)
    title = str(post.get("title") or "")
    meta = str(post.get("meta_description") or "")
    seo_keywords = post.get("seo_keywords") or []

    issues = []
    if compact_len < min_chars:
        issues.append(f"본문 길이 부족: {compact_len}자 < {min_chars}자")
    if len(title) == 0 or len(title) > 40:
        issues.append(f"제목 길이 부적합: {len(title)}자")
    if sections < 4:
        issues.append(f"기술 섹션 부족: {sections}개 < 4개")
    if len(technical_hits) < 4:
        issues.append(f"기술 깊이 부족: 핵심 기술어 {len(technical_hits)}개 < 4개")
    if review_score < MIN_REVIEW_SCORE:
        issues.append(f"Reviewer 점수 부족: {review_score} < {MIN_REVIEW_SCORE}")
    if not (80 <= len(meta) <= 160):
        issues.append(f"메타 설명 길이 부적합: {len(meta)}자 (권장 80~160자)")
    if not (3 <= len(seo_keywords) <= 8):
        issues.append(f"SEO 키워드 개수 부적합: {len(seo_keywords)}개 (권장 3~8개)")

    for pattern in UNSUPPORTED_NUMBER_PATTERNS:
        for match in pattern.findall(content):
            if "추측입니다" not in content[max(0, content.find(str(match)) - 80): content.find(str(match)) + 120]:
                issues.append(f"근거/추정 표기 없는 정량 표현 의심: {match}")

    return {
        "pass": not issues,
        "provider": provider,
        "content_chars": compact_len,
        "min_chars": min_chars,
        "sections": sections,
        "technical_hits": technical_hits,
        "review_score": review_score,
        "issues": issues,
    }


def apply_final_content_gate(posts: list[dict]) -> list[dict]:
    for post in posts:
        if post.get("error"):
            post["final_quality"] = {"pass": False, "issues": [post.get("error")]}
            continue
        post["final_quality"] = evaluate_content_quality(post)
    return posts
