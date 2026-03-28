"""
writer_agent.py — 블로그 본문 작성 에이전트
Goal: 선정된 주제로 SEO 최적화된 블로그 포스트 초안 생성
Worker AI 역할: 실제 콘텐츠 생성 실행
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import anthropic
import yaml

logger = logging.getLogger(__name__)


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_writer_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "writer_prompt.md"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def generate_post(topic: dict) -> dict:
    """
    단일 주제에 대한 블로그 포스트 생성.
    
    Args:
        topic: trend_agent에서 반환된 주제 dict
               { keyword, angle, reason, estimated_search_volume }
    Returns:
        포스트 dict { title, meta_description, tags, content, ... }
    """
    config = load_config()
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    system_prompt = load_writer_prompt()

    writer_config = config["writer"]
    user_prompt = f"""
다음 주제로 블로그 포스트를 작성하세요.

키워드: {topic['keyword']}
접근 각도: {topic['angle']}
선정 이유: {topic['reason']}

작성 요건:
- 최소 {writer_config['min_words']}자, 최대 {writer_config['max_words']}자
- 섹션 구조: {' → '.join(writer_config['sections'])}
- 언어: 한국어
- SEO 타겟 키워드를 자연스럽게 포함
- 불확실한 수치/사실에는 반드시 "(추측입니다)" 표기

반드시 JSON 형식만 반환. 마크다운 코드블록 없이 순수 JSON만:
"""

    logger.info(f"Writer Agent: '{topic['keyword']}' 작성 시작")

    message = client.messages.create(
        model=config["agent"]["model"],
        max_tokens=config["agent"]["max_tokens"],
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()

    # JSON 펜스 안전 제거
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
        post = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 실패: {e}\n원문: {raw[:200]}")
        # 폴백: 원문을 content로 저장
        post = {
            "title": topic["keyword"],
            "meta_description": topic["angle"],
            "tags": [topic["keyword"]],
            "category": "미분류",
            "content": raw,
            "seo_keywords": [topic["keyword"]],
            "estimated_read_time": 5,
        }

    # 메타데이터 추가
    post["source_topic"] = topic
    post["generated_at"] = datetime.now().isoformat()
    post["word_count"] = len(post.get("content", "").replace(" ", ""))

    logger.info(
        f"작성 완료: '{post.get('title', 'N/A')}' "
        f"({post['word_count']}자)"
    )
    return post


def save_draft(post: dict) -> str:
    """초안을 output/drafts/ 에 Markdown + JSON으로 저장."""
    draft_dir = Path(__file__).parent.parent / "output" / "drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(
        c if c.isalnum() or c in "_ " else "_"
        for c in post.get("title", "draft")
    )[:30]
    base_name = f"{timestamp}_{safe_title}"

    # Markdown 저장
    md_path = draft_dir / f"{base_name}.md"
    md_content = f"""---
title: {post.get('title', '')}
meta_description: {post.get('meta_description', '')}
tags: {post.get('tags', [])}
category: {post.get('category', '')}
generated_at: {post.get('generated_at', '')}
word_count: {post.get('word_count', 0)}
---

{post.get('content', '')}
"""
    md_path.write_text(md_content, encoding="utf-8")

    # JSON 메타데이터 저장
    json_path = draft_dir / f"{base_name}.json"
    json_path.write_text(
        json.dumps(post, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    logger.info(f"초안 저장: {md_path}")
    return str(md_path)


def run_writer_agent(topics: list[dict]) -> list[dict]:
    """
    복수 주제에 대해 순차적으로 포스트 생성.
    Returns: 생성된 포스트 리스트 (draft_path 포함)
    """
    logger.info(f"=== Writer Agent 시작: {len(topics)}개 주제 ===")
    posts = []

    for i, topic in enumerate(topics, 1):
        logger.info(f"[{i}/{len(topics)}] 작성 중: {topic['keyword']}")
        try:
            post = generate_post(topic)
            draft_path = save_draft(post)
            post["draft_path"] = draft_path
            posts.append(post)
        except Exception as e:
            logger.error(f"'{topic['keyword']}' 작성 실패: {e}")
            posts.append({
                "title": topic["keyword"],
                "error": str(e),
                "draft_path": None,
            })

    logger.info(f"Writer Agent 완료: {len(posts)}개 포스트 생성")
    return posts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # 테스트용 샘플 주제
    test_topics = [
        {
            "keyword": "AI 물류 자동화 2025",
            "angle": "현장 적용 사례 중심으로 최신 트렌드 분석",
            "reason": "검색량 급증 키워드",
            "estimated_search_volume": "high",
        }
    ]
    posts = run_writer_agent(test_topics)
    print(json.dumps([p.get("title") for p in posts], ensure_ascii=False))
