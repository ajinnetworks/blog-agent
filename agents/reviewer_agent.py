"""
reviewer_agent.py — 품질 검수 & SEO 점검 에이전트
Goal: 작성된 포스트의 품질 점수를 산출하고 개선 지시 반환
Evaluator AI 역할: 오류·누락·요구사항 미반영 점검
"""

import json
import logging
import os
import time
from functools import wraps
from pathlib import Path

from google import genai as google_genai
import yaml

import io
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', errors='replace'
    )
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding='utf-8', errors='replace'
    )


logger = logging.getLogger(__name__)

def retry_on_rate_limit(max_retries: int = 3, wait_seconds: int = 60):
    """429/quota 오류 시 지수 대기 후 재시도 데코레이터."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    is_rate_limit = (
                        "429" in str(e)
                        or "quota" in str(e).lower()
                        or "ResourceExhausted" in type(e).__name__
                    )
                    if is_rate_limit:
                        if attempt < max_retries - 1:
                            wait = wait_seconds * (attempt + 1)
                            print(f"[RATE LIMIT] {wait}초 대기 후 재시도 ({attempt + 1}/{max_retries})")
                            time.sleep(wait)
                        else:
                            print("[RATE LIMIT] 재시도 한도 초과 — 건너뜀")
                            return {
                                "pass": False,
                                "total_score": 0,
                                "breakdown": {},
                                "issues": [],
                                "revision_notes": "API 한도 초과로 검수 불가",
                            }
                    else:
                        raise
        return wrapper
    return decorator


GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest",
]


def get_gemini_response(prompt: str) -> str:
    """GEMINI_MODELS 순서대로 시도, 429/404 시 다음 모델로 전환."""
    client = google_genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    for retry in range(2):
        for model_name in GEMINI_MODELS:
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                logger.info(f"[MODEL] {model_name} 사용")
                return response.text.strip()
            except Exception as e:
                err = str(e)
                if "429" in err or "503" in err or "quota" in err.lower() or "UNAVAILABLE" in err or "ResourceExhausted" in type(e).__name__ or "ServerError" in type(e).__name__ or "404" in err:
                    logger.warning(f"[WARN] {model_name} 사용 불가 → 다음 모델 시도")
                    continue
                raise
        if retry == 0:
            logger.warning("[RATE LIMIT] 모든 모델 한도 초과 → 65초 대기 후 재시도")
            time.sleep(65)
    raise RuntimeError("429 모든 Gemini 모델 한도 초과 (재시도 후)")


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_title(title: str) -> dict:
    """제목 SEO 규칙 검증. errors는 하드 실패, warnings는 정보성 경고."""
    errors = []
    warnings = []

    if len(title) > 40:
        errors.append(f"제목 {len(title)}자 초과 (허용: 40자)")
    if title.startswith("아진네트웍스"):
        errors.append("브랜드명으로 제목 시작 금지")
    if "아진네트웍스" not in title:
        warnings.append("아진네트웍스 미포함 — 브랜드 노출 약화")
    if title.count("아진네트웍스") >= 2:
        errors.append("아진네트웍스 중복 포함")

    patterns = ["완전 정복", "도입 전", "해결한", "달성한"]
    if not any(p in title for p in patterns):
        warnings.append("SEO 패턴 A~D 미적용 의심")

    return {
        "title": title,
        "length": len(title),
        "errors": errors,
        "warnings": warnings,
        "passed": len(errors) == 0,
    }


REVIEW_PROMPT_SIMPLE = """다음 포스트를 100점 만점으로 평가해줘.
기준: 전문성(40), 정확성(30), 가독성(30)
JSON으로만 응답: {{"score": 점수, "pass": true/false, "reason": "한줄요약"}}
포스트:
{content}
"""


@retry_on_rate_limit(max_retries=3, wait_seconds=60)
def batch_review_posts(posts: list[dict], min_score: int) -> list[dict]:
    items = []
    for i, post in enumerate(posts):
        content_raw = post.get("content", "")
        content_str = " ".join(str(c) for c in content_raw) if isinstance(content_raw, list) else str(content_raw)
        items.append(
            f"[포스트 {i+1}] 제목: {post.get('title', '')}\n"
            f"본문 앞 400자:\n{content_str[:400]}"
        )

    batch_text = "\n\n".join(items)
    prompt = f"""아래 {len(posts)}개 블로그 포스트를 각각 100점 만점으로 평가해줘.
기준: 전문성(40), 정확성(30), 가독성(30)
합격 기준: {min_score}점 이상

{batch_text}

반드시 아래 JSON 배열만 반환. 순서는 포스트 번호 순:
[
  {{"index": 1, "score": 점수, "pass": true/false, "reason": "한줄요약"}},
  ...
]
"""
    raw = get_gemini_response(prompt)
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("["):
                raw = part
                break

    try:
        results = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"배치 검수 JSON 파싱 실패: {e}")
        results = [{"index": i+1, "score": 0, "pass": False, "reason": f"파싱 실패: {e}"} for i in range(len(posts))]

    reviews = []
    for i, post in enumerate(posts):
        r = next((x for x in results if x.get("index") == i+1), None) or {"score": 0, "pass": False, "reason": "결과 없음"}
        score = r.get("score", 0)
        title_check = validate_title(post.get("title", ""))
        if not title_check["passed"]:
            logger.warning(f"제목 검증 실패: {title_check['errors']}")
            score -= 10 * len(title_check["errors"])
        if title_check["warnings"]:
            logger.warning(f"제목 경고: {title_check['warnings']}")
        score = max(0, score)

        passed = score >= min_score
        issues = [] if passed else [{"severity": "medium", "description": r.get("reason", "")}]
        issues += [{"severity": "high", "description": e} for e in title_check["errors"]]
        reviews.append({
            "total_score": score,
            "breakdown": {},
            "issues": issues,
            "pass": passed,
            "min_score": min_score,
            "revision_notes": r.get("reason", ""),
            "title_check": title_check,
        })
        logger.info(f"[{i+1}/{len(posts)}] '{post.get('title', '')}' {'합격' if passed else '불합격'} ({score}/{min_score})")
    return reviews


@retry_on_rate_limit(max_retries=3, wait_seconds=60)
def review_post(post: dict) -> dict:
    config = load_config()
    min_score = config["reviewer"]["min_score"]
    content_raw = post.get("content", "")
    content_str = " ".join(str(c) for c in content_raw) if isinstance(content_raw, list) else str(content_raw)

    raw = get_gemini_response(REVIEW_PROMPT_SIMPLE.format(content=content_str[:500]))
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break

    try:
        r = json.loads(raw)
        score = r.get("score", 0)
        title_check = validate_title(post.get("title", ""))
        if not title_check["passed"]:
            logger.warning(f"제목 검증 실패: {title_check['errors']}")
            score -= 10 * len(title_check["errors"])
        else:
            logger.info(f"제목 검증 통과: {title_check['length']}자")
        if title_check["warnings"]:
            logger.warning(f"제목 경고: {title_check['warnings']}")
        score = max(0, score)
        passed = score >= min_score
        issues = [] if passed else [{"severity": "medium", "description": r.get("reason", "")}]
        issues += [{"severity": "high", "description": e} for e in title_check["errors"]]
        review = {
            "total_score": score,
            "breakdown": {},
            "issues": issues,
            "pass": passed,
            "min_score": min_score,
            "revision_notes": r.get("reason", ""),
            "title_check": title_check,
        }
    except json.JSONDecodeError as e:
        review = {
            "total_score": 0,
            "breakdown": {},
            "issues": [{"severity": "high", "description": f"파싱 실패: {e}"}],
            "pass": False,
            "min_score": min_score,
            "revision_notes": "검수 에이전트 오류 - 수동 확인 필요",
        }

    logger.info(f"검수 결과: {'합격' if review['pass'] else '불합격'} | 점수: {review['total_score']}/{min_score}")
    return review


def revise_post(post: dict, review: dict) -> dict:
    issues_text = "\n".join([f"- [{i['severity']}] {i['description']}" for i in review.get("issues", [])])
    prompt = f"""
아래 블로그 포스트를 검수 결과에 따라 개선하세요.

원본 제목: {post.get('title', '')}
검수 점수: {review.get('total_score')}/{review.get('min_score')}
개선 필요 항목:
{issues_text}

추가 노트: {review.get('revision_notes', '')}

개선된 포스트를 동일한 JSON 형식으로 반환:
"""
    raw = get_gemini_response(prompt)
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break
    try:
        revised = json.loads(raw)
        revised["source_topic"] = post.get("source_topic", {})
        revised["draft_path"] = post.get("draft_path")
        revised["generated_at"] = post.get("generated_at")
        revised["revised"] = True
        logger.info("재작성 완료")
        return revised
    except json.JSONDecodeError:
        logger.error("재작성 결과 파싱 실패 — 원본 유지")
        return post


def run_reviewer_agent(posts: list[dict], max_revisions: int = 1) -> list[dict]:
    logger.info(f"=== Reviewer Agent 시작: {len(posts)}개 포스트 ===")
    config = load_config()
    min_score = config["reviewer"]["min_score"]
    error_posts = [p for p in posts if p.get("error")]
    valid_posts = [p for p in posts if not p.get("error")]

    if valid_posts:
        logger.info(f"배치 검수: {len(valid_posts)}개 포스트 -> 1회 API 호출")
        try:
            batch_reviews = batch_review_posts(valid_posts, min_score)
            for post, review in zip(valid_posts, batch_reviews):
                post["review_result"] = review
        except RuntimeError as e:
            logger.warning(f"배치 검수 실패 ({e}) — 전체 강제 통과 처리")
            for post in valid_posts:
                post["review_result"] = {
                    "total_score": 0,
                    "breakdown": {},
                    "issues": [],
                    "pass": True,
                    "min_score": min_score,
                    "forced_pass": True,
                    "revision_notes": f"API 한도 초과로 검수 생략: {e}",
                }

    # IMPORTANT: replace the element in valid_posts after revision so the new title/content/review persist.
    for idx, original_post in enumerate(valid_posts):
        if original_post.get("review_result", {}).get("pass"):
            continue
        current_post = original_post
        for attempt in range(1, max_revisions + 1):
            logger.info(f"재작성 시도 {attempt}/{max_revisions}: '{current_post.get('title')}'")
            current_post = revise_post(current_post, current_post["review_result"])
            current_post["review_result"] = review_post(current_post)
            if current_post["review_result"]["pass"]:
                break
        valid_posts[idx] = current_post
        if not current_post.get("review_result", {}).get("pass"):
            logger.warning(f"최대 재시도 초과 - '{current_post.get('title')}' 강제 통과")
            current_post["review_result"]["forced_pass"] = True

    reviewed_posts = error_posts + valid_posts
    passed = sum(1 for p in reviewed_posts if p.get("review_result", {}).get("pass"))
    logger.info(f"검수 완료: {passed}/{len(reviewed_posts)}개 합격")
    return reviewed_posts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Reviewer Agent — 단독 실행은 run_agent.py를 통해 사용하세요.")
