"""
writer_agent.py - 블로그 본문 작성 에이전트
Goal: 선정된 주제로 SEO 최적화된 블로그 포스트 초안 생성
Worker AI 역할: 실제 콘텐츠 생성 실행
"""

import io
import json
import logging
import os
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', errors='replace'
    )
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding='utf-8', errors='replace'
    )

from datetime import datetime
from pathlib import Path

from google import genai as google_genai
import yaml

logger = logging.getLogger(__name__)

# 모델 우선순위 (한도 초과 시 자동 전환)
GEMINI_MODELS = [
    "gemini-2.0-flash",       # 1순위
    "gemini-2.0-flash-lite",  # 2순위 (경량, 429 대비)
    "gemini-flash-latest",    # 3순위 (최신 alias)
]


def get_gemini_response(prompt: str) -> str:
    """GEMINI_MODELS 순서대로 시도, 429/404 시 다음 모델로 전환. 전체 실패 시 60초 대기 후 1회 재시도."""
    import time
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

BLOG_CATEGORIES = [
    {
        "name": "포장자동화",
        "keywords": [
            "박스 포장", "테이핑", "라벨링", "팔레타이징", "슈링크 포장", "진공포장",
            "카토닝", "스트레치 포장", "포장 검사", "포장재 공급", "제함기", "봉함기",
            "포장 불량 검출", "포장 자동화 라인", "포장 로봇",
        ]
    },
    {
        "name": "자동차자동화",
        "keywords": [
            "차체 용접", "도장 자동화", "EV 배터리 조립", "타이어 조립", "의장라인",
            "스폿 용접", "아크 용접 자동화", "차체 조립 지그", "도어 조립", "엔진 조립",
            "배터리 팩 자동화", "전기차 생산라인", "차량 검사 자동화", "토크 관리",
        ]
    },
    {
        "name": "반도체자동화",
        "keywords": [
            "웨이퍼 핸들링", "클린룸 자동화", "AOI 검사", "다이 본딩", "와이어 본딩",
            "포토리소그래피", "CMP 공정", "에칭 자동화", "반도체 패키징", "칩 검사",
            "FOUP 이송", "인라인 계측", "수율 관리", "반도체 트레이 핸들링",
        ]
    },
    {
        "name": "디스플레이자동화",
        "keywords": [
            "OLED 검사", "LCD 패널", "본딩 자동화", "편광필름", "FOG 공정",
            "셀 조립 자동화", "유리 기판 이송", "패널 결함 검출", "ACF 본딩",
            "모듈 조립 자동화", "디스플레이 AOI", "백라이트 조립", "터치 패널 검사",
        ]
    },
    {
        "name": "물류자동화",
        "keywords": [
            "AGV", "AMR", "소터", "컨베이어", "WMS", "자동창고", "피킹시스템",
            "AS/RS", "DPS", "GTP", "팔레트 자동화", "입출고 자동화", "물류 로봇",
            "자동 분류", "재고 추적", "RFID 물류", "박스 자동 이송",
        ]
    },
    {
        "name": "로봇자동화",
        "keywords": [
            "협동로봇", "산업용 로봇", "델타로봇", "SCARA", "로봇 그리퍼", "로봇 비전",
            "6축 로봇", "로봇 용접", "로봇 핸들링", "로봇 조립", "로봇 팔레타이징",
            "엔드이펙터", "로봇 캘리브레이션", "로봇 경로 계획", "로봇 티칭",
        ]
    },
    {
        "name": "부품정보",
        "keywords": [
            "서보모터", "리니어가이드", "센서", "액추에이터", "그리퍼", "볼스크류",
            "감속기", "리니어모터", "공압 실린더", "전자 클러치", "인코더",
            "레이저 변위 센서", "비전 카메라", "포스 센서", "토크 센서",
        ]
    },
    {
        "name": "PLC제어",
        "keywords": [
            "Siemens PLC", "Mitsubishi PLC", "LS PLC", "HMI", "SCADA", "필드버스",
            "TIA Portal", "GX Works", "래더 프로그래밍", "인버터 제어",
            "Profinet", "EtherCAT", "Modbus", "OPC-UA", "모션 컨트롤러",
        ]
    },
    {
        "name": "비전검사",
        "keywords": [
            "딥러닝 비전", "패턴매칭", "결함검출", "3D비전", "머신비전", "OCR검사",
            "이물 검사", "치수 측정", "표면 검사", "용접 비드 검사",
            "Blob 분석", "엣지 검출", "비전 조명", "카메라 캘리브레이션",
            "AI 불량 판정", "인라인 비전", "비전 센서",
        ]
    },
    {
        "name": "스마트팩토리",
        "keywords": [
            "FEMS", "MES", "OEE", "예지보전", "디지털트윈", "엣지AI", "제조 데이터",
            "생산 최적화", "불량 감지", "공정 자동화", "설비 모니터링",
            "IIoT", "제조 AI", "CPM", "공정 분석", "생산성 향상",
            "에너지 절감", "탄소 저감", "스마트 센서", "실시간 대시보드",
        ]
    },
]

# 완전 제외 키워드
EXCLUDE_KEYWORDS = [
    # 금융 관련
    "금융", "카드결제", "핀테크", "은행", "주식",
    "암호화폐", "보험", "대출", "신용카드", "페이먼트",
    # 비제조업/식품/서비스업
    "푸드테크", "외식", "식품", "음식점", "프랜차이즈",
    "배달", "요식업", "카페", "레스토랑", "조리",
    # 소비재/유통
    "패션", "의류", "화장품", "뷰티", "쇼핑몰",
    "이커머스", "온라인쇼핑",
]

ALLOWED_CATEGORIES = [cat["name"] for cat in BLOG_CATEGORIES]
CATEGORY_KEYWORDS = {cat["name"]: cat["keywords"] for cat in BLOG_CATEGORIES}


def classify_category(keyword: str, angle: str) -> str:
    text = f"{keyword} {angle}".lower()
    for cat in BLOG_CATEGORIES:
        for kw in cat["keywords"]:
            if kw.lower() in text:
                return cat["name"]
    return "스마트팩토리"


def validate_category(category: str) -> str:
    if category in ALLOWED_CATEGORIES:
        return category
    for allowed in ALLOWED_CATEGORIES:
        if allowed in category or category in allowed:
            return allowed
    return "스마트팩토리"


def is_valid_topic(topic: str) -> bool:
    for kw in EXCLUDE_KEYWORDS:
        if kw in topic:
            return False
    return True


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_writer_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "writer_prompt.md"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def generate_post(topic: dict) -> dict:
    config = load_config()
    system_prompt = load_writer_prompt()

    pre_category = classify_category(topic["keyword"], topic.get("angle", ""))

    writer_config = config["writer"]
    user_prompt = f"""{system_prompt}

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

카테고리 규칙 (반드시 준수):
- 아래 5개 중 하나만 선택
- 물류자동화 / 공장자동화 / 딥러닝비전 / 스마트팩토리 / 제어SW
- AI+물류 복합 주제는 반드시 "물류자동화" 선택
- 권장 카테고리: {pre_category}

반드시 JSON 형식만 반환. 마크다운 코드블록 없이 순수 JSON만:
{{
  "title": "아래 패턴 중 가장 자연스러운 하나를 선택해 작성 (40자 이내): 패턴A: [설비/기술명] 전문기업 아진네트웍스가 설명하는 [핵심 주제] / 패턴B: [문제 상황]? 아진네트웍스 [솔루션명]으로 해결하는 법 / 패턴C: [키워드] 도입 사례 — 아진네트웍스 실적 기반 분석 / 규칙: 반드시 SEO 타겟 키워드를 제목 앞 20자 안에 포함할 것",
  "meta_description": "메타설명 (150자 이내)",
  "category": "위 5개 중 하나",
  "tags": ["태그1", "태그2"],
  "content": "본문 마크다운",
  "seo_keywords": ["키워드1"],
  "estimated_read_time": 5
}}
"""

    logger.info(f"Writer Agent: '{topic['keyword']}' 작성 시작 (예상 카테고리: {pre_category})")

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

    raw_cat = post.get("category", "")
    validated_cat = validate_category(raw_cat)
    if raw_cat != validated_cat:
        logger.warning(f"카테고리 보정: '{raw_cat}' -> '{validated_cat}'")
    post["category"] = validated_cat

    post["source_topic"] = topic
    post["generated_at"] = datetime.now().isoformat()
    post["word_count"] = len(post.get("content", "").replace(" ", ""))

    logger.info(f"작성 완료: '{post.get('title', 'N/A')}' | 카테고리: {post['category']} | {post['word_count']}자")
    return post


def save_draft(post: dict) -> str:
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
title: {post.get("title", "") or self._generate_title(post.get("content",""), post.get("category",""))}
meta_description: {post.get("meta_description", "")}
tags: {post.get("tags", [])}
category: {post.get("category", "")}
generated_at: {post.get("generated_at", "")}
word_count: {post.get("word_count", 0)}
image: /assets/img/og-default.png
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
    import time
    logger.info(f"=== Writer Agent 시작: {len(topics)}개 주제 ===")
    posts = []

    for i, topic in enumerate(topics, 1):
        if not is_valid_topic(topic.get("keyword", "")):
            logger.warning(f"[{i}/{len(topics)}] 제외 키워드 포함 — 스킵: {topic['keyword']}")
            continue
        if i > 1:
            logger.info("[RPM 보호] 5초 대기 중...")
            time.sleep(5)
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
    print(json.dumps(
        [{"title": p.get("title"), "category": p.get("category")} for p in posts],
        ensure_ascii=False, indent=2
    ))
