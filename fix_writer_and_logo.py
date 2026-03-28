import os
import io
import re
from PIL import Image
from github import Auth, Github
from dotenv import load_dotenv

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

# ════════════════════════════════════════════
# 1. 로고 배경 제거 (흰색 -> 투명)
# ════════════════════════════════════════════
logo_path = r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\ajin_logo.png'
img = Image.open(logo_path).convert('RGBA')

data = img.getdata()
new_data = []
for r, g_ch, b, a in data:
    # 흰색 계열(230 이상) -> 투명 처리
    if r > 230 and g_ch > 230 and b > 230:
        new_data.append((255, 255, 255, 0))
    else:
        new_data.append((r, g_ch, b, a))

img.putdata(new_data)

# 리사이즈 (높이 80px 기준)
MAX_HEIGHT = 80
ratio = MAX_HEIGHT / img.height
new_w = int(img.width * ratio)
img = img.resize((new_w, MAX_HEIGHT), Image.LANCZOS)

buffer = io.BytesIO()
img.save(buffer, format='PNG', optimize=True, compress_level=9)
logo_data = buffer.getvalue()

original_kb = os.path.getsize(logo_path) // 1024
compressed_kb = len(logo_data) // 1024
print(f'로고 배경 제거 완료: {original_kb}KB -> {compressed_kb}KB ({new_w}x{MAX_HEIGHT}px)')

# GitHub 업로드
try:
    existing = repo.get_contents('assets/ajin_logo.png', ref='main')
    repo.update_file(
        'assets/ajin_logo.png',
        'fix: remove white background from logo',
        logo_data,
        existing.sha,
        branch='main'
    )
    print('로고 업데이트 완료: assets/ajin_logo.png')
except Exception as e:
    repo.create_file(
        'assets/ajin_logo.png',
        'fix: remove white background from logo',
        logo_data,
        branch='main'
    )
    print('로고 업로드 완료: assets/ajin_logo.png')

# ════════════════════════════════════════════
# 2. writer_agent.py 카테고리 강제 분류 수정
# ════════════════════════════════════════════
new_writer = '''"""
writer_agent.py - 블로그 본문 작성 에이전트
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

# 허용 카테고리 (우선순위 순)
ALLOWED_CATEGORIES = [
    "물류자동화",
    "공장자동화",
    "딥러닝비전",
    "스마트팩토리",
    "제어SW",
]

# 카테고리 분류 키워드 매핑 (우선순위 높은 순)
CATEGORY_KEYWORDS = {
    "물류자동화": ["물류", "AGV", "AMR", "WMS", "창고", "배송", "SCM", "재고"],
    "공장자동화": ["공장", "CNC", "로봇", "가공", "조립", "용접", "생산라인", "자동화"],
    "딥러닝비전": ["딥러닝", "비전", "AI", "머신러닝", "불량검사", "영상처리", "카메라"],
    "스마트팩토리": ["스마트팩토리", "MES", "ERP", "IoT", "디지털전환", "데이터"],
    "제어SW": ["PLC", "제어", "SCADA", "HMI", "프로그램", "소프트웨어", "알고리즘"],
}


def classify_category(keyword: str, angle: str) -> str:
    """키워드/각도 기반 카테고리 자동 분류. 복합 주제는 물류자동화 우선."""
    text = f"{keyword} {angle}".lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                return cat
    return "공장자동화"  # 기본값


def validate_category(category: str) -> str:
    """반환된 카테고리가 허용 목록에 없으면 키워드 기반 재분류."""
    if category in ALLOWED_CATEGORIES:
        return category
    # 부분 매칭 시도
    for allowed in ALLOWED_CATEGORIES:
        if allowed in category or category in allowed:
            return allowed
    return "공장자동화"


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

    # 사전 분류 (AI 반환값 검증용)
    pre_category = classify_category(topic["keyword"], topic.get("angle", ""))

    writer_config = config["writer"]
    user_prompt = f"""
다음 주제로 블로그 포스트를 작성하세요.

키워드: {topic["keyword"]}
접근 각도: {topic.get("angle", "")}
선정 이유: {topic.get("reason", "")}

작성 요건:
- 최소 {writer_config["min_words"]}자, 최대 {writer_config["max_words"]}자
- 섹션 구조: {" -> ".join(writer_config["sections"])}
- 언어: 한국어
- SEO 타겟 키워드를 자연스럽게 포함
- 불확실한 수치/사실에는 반드시 "(추측입니다)" 표기

카테고리 규칙 (중요):
- 반드시 아래 5개 중 하나만 선택하세요
- 허용 카테고리: 물류자동화 / 공장자동화 / 딥러닝비전 / 스마트팩토리 / 제어SW
- AI+물류 복합 주제는 반드시 "물류자동화" 선택
- 권장 카테고리: {pre_category}

반드시 JSON 형식만 반환. 마크다운 코드블록 없이 순수 JSON만:
{{
  "title": "제목",
  "meta_description": "메타설명 (150자 이내)",
  "category": "위 5개 중 하나",
  "tags": ["태그1", "태그2"],
  "content": "본문 마크다운",
  "seo_keywords": ["키워드1"],
  "estimated_read_time": 5
}}
"""

    logger.info(f"Writer Agent: '{topic['keyword']}' 작성 시작 (예상 카테고리: {pre_category})")

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
        logger.error(f"JSON 파싱 실패: {e}")
        post = {
            "title": topic["keyword"],
            "meta_description": topic.get("angle", ""),
            "tags": [topic["keyword"]],
            "category": pre_category,
            "content": raw,
            "seo_keywords": [topic["keyword"]],
            "estimated_read_time": 5,
        }

    # 카테고리 검증 및 보정
    raw_cat = post.get("category", "")
    validated_cat = validate_category(raw_cat)
    if raw_cat != validated_cat:
        logger.warning(f"카테고리 보정: '{raw_cat}' -> '{validated_cat}'")
    post["category"] = validated_cat

    # 메타데이터 추가
    post["source_topic"] = topic
    post["generated_at"] = datetime.now().isoformat()
    post["word_count"] = len(post.get("content", "").replace(" ", ""))

    logger.info(f"작성 완료: '{post.get('title', 'N/A')}' | 카테고리: {post['category']} | {post['word_count']}자")
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

    md_path = draft_dir / f"{base_name}.md"
    md_content = f"""---
title: {post.get("title", "")}
meta_description: {post.get("meta_description", "")}
tags: {post.get("tags", [])}
category: {post.get("category", "")}
generated_at: {post.get("generated_at", "")}
word_count: {post.get("word_count", 0)}
---

{post.get("content", "")}
"""
    md_path.write_text(md_content, encoding="utf-8")

    json_path = draft_dir / f"{base_name}.json"
    json_path.write_text(
        json.dumps(post, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    logger.info(f"초안 저장: {md_path}")
    return str(md_path)


def run_writer_agent(topics: list[dict]) -> list[dict]:
    """복수 주제에 대해 순차적으로 포스트 생성."""
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
    test_topics = [
        {
            "keyword": "AI 물류 자동화 2025",
            "angle": "현장 적용 사례 중심으로 최신 트렌드 분석",
            "reason": "검색량 급증 키워드",
            "estimated_search_volume": "high",
        }
    ]
    posts = run_writer_agent(test_topics)
    print(json.dumps([{"title": p.get("title"), "category": p.get("category")} for p in posts], ensure_ascii=False, indent=2))
'''

# GitHub에 writer_agent.py 업데이트
try:
    f = repo.get_contents('agents/writer_agent.py', ref='main')
    repo.update_file(
        'agents/writer_agent.py',
        'feat: enforce 5-category classification in writer agent',
        new_writer,
        f.sha,
        branch='main'
    )
    print('writer_agent.py 업데이트 완료')
except Exception as e:
    print(f'GitHub 업데이트 실패: {e}')
    # 로컬 저장
    local_path = r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\agents\writer_agent.py'
    with open(local_path, 'w', encoding='utf-8') as out:
        out.write(new_writer)
    print(f'로컬 저장 완료: {local_path}')

print('\n모든 작업 완료')
