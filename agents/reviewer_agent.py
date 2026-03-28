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

import google.generativeai as genai
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


# 모델 우선순위 (한도 초과 시 자동 전환)
GEMINI_MODELS = [
    "gemini-1.5-flash",     # 1순위
    "gemini-2.0-flash",     # 2순위
    "gemini-1.5-flash-8b",  # 3순위 (경량)
]


def get_gemini_response(prompt: str) -> str:
    """GEMINI_MODELS 순서대로 시도, 429 시 다음 모델로 전환."""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            logger.info(f"[MODEL] {model_name} 사용")
            return response.text.strip()
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "ResourceExhausted" in type(e).__name__:
                logger.warning(f"[WARN] {model_name} 한도 초과 → 다음 모델 시도")
                continue
            raise
    raise RuntimeError("모든 Gemini 모델 한도 초과")


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_reviewer_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "reviewer_prompt.md"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


@retry_on_rate_limit(max_retries=3, wait_seconds=60)
def review_post(post: dict) -> dict:
    """
    단일 포스트 검수.
    Returns: review_result dict { total_score, breakdown, issues, pass, revision_notes }
    """
    config = load_config()
    system_prompt = load_reviewer_prompt()
    min_score = config["reviewer"]["min_score"]

    # content가 문자열이 아닌 경우 안전하게 변환
    content_raw = post.get('content', '')
    if isinstance(content_raw, list):
        content_str = ' '.join(str(c) for c in content_raw)
    elif isinstance(content_raw, dict):
        content_str = str(content_raw)
    else:
        content_str = str(content_raw)

    user_prompt = f"""{system_prompt}

아래 블로그 포스트를 검수하세요.

제목: {post.get('title', '')}
메타 설명: {post.get('meta_description', '')}
태그: {post.get('tags', [])}
SEO 키워드: {post.get('seo_keywords', [])}
본문 (앞 500자):
{content_str[:500]}...

합격 기준: {min_score}점 이상
JSON만 반환:
"""

    raw = get_gemini_response(user_prompt)
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
        review = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"검수 결과 JSON 파싱 실패: {e}")
        review = {
            "total_score": 0,
            "breakdown": {},
            "issues": [{"severity": "high", "description": f"파싱 실패: {e}"}],
            "pass": False,
            "revision_required": True,
            "revision_notes": "검수 에이전트 오류 — 수동 확인 필요",
        }

    passed = review.get("total_score", 0) >= min_score
    review["pass"] = passed
    review["min_score"] = min_score

    status = "✅ 합격" if passed else "❌ 불합격"
    logger.info(
        f"검수 결과: {status} | 점수: {review.get('total_score')}/{min_score} | "
        f"이슈: {len(review.get('issues', []))}개"
    )
    return review


def revise_post(post: dict, review: dict) -> dict:
    """
    검수 불합격 시 개선 지시를 바탕으로 포스트 재작성.
    최대 2회 재시도 (무한 루프 방지).
    """
    config = load_config()

    issues_text = "\n".join(
        [f"- [{i['severity']}] {i['description']}"
         for i in review.get("issues", [])]
    )

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
        revised["revised"] = True
        logger.info("재작성 완료")
        return revised
    except json.JSONDecodeError:
        logger.error("재작성 결과 파싱 실패 — 원본 유지")
        return post


def run_reviewer_agent(posts: list[dict], max_revisions: int = 2) -> list[dict]:
    """
    포스트 리스트 전체 검수. 불합격 시 재작성 루프 실행.
    Returns: 검수 완료된 포스트 리스트 (review_result 포함)
    """
    logger.info(f"=== Reviewer Agent 시작: {len(posts)}개 포스트 ===")
    reviewed_posts = []

    for post in posts:
        if post.get("error"):
            logger.warning(f"오류 포스트 스킵: {post.get('title')}")
            reviewed_posts.append(post)
            continue

        current_post = post
        for attempt in range(1, max_revisions + 2):  # +2: 초기 검수 포함
            review = review_post(current_post)
            current_post["review_result"] = review

            if review["pass"]:
                logger.info(f"'{current_post.get('title')}' 검수 합격 (시도 {attempt})")
                break

            if attempt <= max_revisions:
                logger.info(f"재작성 시도 {attempt}/{max_revisions}")
                current_post = revise_post(current_post, review)
            else:
                logger.warning(
                    f"최대 재시도 초과 — '{current_post.get('title')}' 강제 통과"
                )
                current_post["review_result"]["forced_pass"] = True
                break

        reviewed_posts.append(current_post)

    passed = sum(1 for p in reviewed_posts if p.get("review_result", {}).get("pass"))
    logger.info(f"검수 완료: {passed}/{len(reviewed_posts)}개 합격")
    return reviewed_posts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Reviewer Agent — 단독 실행은 run_agent.py를 통해 사용하세요.")
