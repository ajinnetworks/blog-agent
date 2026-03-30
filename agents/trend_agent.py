"""
trend_agent.py — 트렌드 크롤링 & 주제 선정 에이전트
Goal: 실시간 트렌드에서 블로그 포스팅 키워드 3개 선정
"""

import datetime
import json
import logging
import os
import random
from datetime import datetime
from typing import Optional

from google import genai as google_genai
import requests
import yaml

# 모델 우선순위 (한도 초과 시 자동 전환)
GEMINI_MODELS = [
    "gemini-2.0-flash",       # 1순위
    "gemini-2.0-flash-lite",  # 2순위 (경량, 429 대비)
    "gemini-flash-latest",    # 3순위 (최신 alias)
]

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


from agents.writer_agent import is_valid_topic, EXCLUDE_KEYWORDS

logger = logging.getLogger(__name__)

# ── 카테고리 가중치 (주제 선정 시 우선순위) ──────────────────────────
CATEGORY_WEIGHTS = {
    "물류자동화":   0.35,   # 최우선 — AGV/AMR/컨베이어/소터
    "딥러닝비전":   0.30,   # 최우선 — 비전검사/불량검출/머신비전
    "공장자동화":   0.15,
    "스마트팩토리": 0.12,
    "제어SW":      0.08,
}

CATEGORY_KEYWORDS = {
    "물류자동화": [
        "AGV", "AMR", "컨베이어", "소터", "WMS", "물류자동화",
        "자동창고", "피킹", "팔레타이징", "물류로봇", "배송자동화"
    ],
    "딥러닝비전": [
        "딥러닝 비전", "머신비전", "비전검사", "불량검출",
        "AI 검사", "이미지 인식", "결함검출", "OCR", "3D비전",
        "외관검사", "반도체 검사", "OLED 검사"
    ],
    "공장자동화": [
        "공장자동화", "로봇자동화", "CNC", "픽앤플레이스",
        "포장자동화", "용접자동화", "조립자동화",
        "박스포장", "테이핑", "라벨링", "팔레타이징",
        "차체용접", "도장자동화", "EV배터리조립"
    ],
    "스마트팩토리": [
        "스마트팩토리", "MES", "디지털트윈", "OEE",
        "예지보전", "IoT", "엣지AI"
    ],
    "제어SW": [
        "PLC", "SCADA", "HMI", "Siemens", "Mitsubishi",
        "LS산전", "필드버스", "모션제어"
    ],
}

INDUSTRY_KEYWORDS = {
    "반도체":    ["웨이퍼핸들링", "클린룸자동화", "AOI검사", "다이본딩", "와이어본딩"],
    "디스플레이": ["OLED검사", "LCD패널", "본딩자동화", "편광필름", "FOG공정"],
    "포장":      ["박스포장", "테이핑", "라벨링", "슈링크포장", "진공포장"],
    "자동차":    ["차체용접", "도장자동화", "EV배터리조립", "타이어조립", "의장라인"],
    "부품":      ["서보모터", "리니어가이드", "그리퍼", "볼스크류", "액추에이터"],
}

# 화/목/토 스케줄 순환
SCHEDULE_ROTATION = [
    "물류자동화",   # 화요일
    "딥러닝비전",   # 목요일
    "공장자동화",   # 토요일
]


def get_today_category() -> str:
    """오늘 요일 기반 카테고리 반환. 화/목/토는 고정 순환, 그 외는 가중치 랜덤."""
    weekday = datetime.datetime.now().weekday()  # 0=월 … 6=일
    rotation_map = {1: "물류자동화", 3: "딥러닝비전", 5: "공장자동화"}
    cats = list(CATEGORY_WEIGHTS.keys())
    weights = list(CATEGORY_WEIGHTS.values())
    return rotation_map.get(weekday, random.choices(cats, weights=weights, k=1)[0])


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
                    logger.warning(f"[WARN] {model_name} 사용 불가 -> 다음 모델 시도")
                    continue
                raise
        if retry == 0:
            logger.warning("[RATE LIMIT] 모든 모델 한도 초과 -> 65초 대기 후 재시도")
            time.sleep(65)
    raise RuntimeError("429 모든 Gemini 모델 한도 초과 (재시도 후)")


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_google_trends_rss() -> list[dict]:
    """
    Google 트렌드 RSS에서 현재 인기 검색어를 가져옵니다.
    RSS 주소는 공개 엔드포인트 사용 (확실하지 않음 — 변경될 수 있음).
    """
    url = "https://trends.google.com/trending/rss?geo=KR"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        # 간단한 XML 파싱 (추가 의존성 없이)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        trends = []
        for item in items[:20]:
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                trends.append({"keyword": title_el.text, "source": "google_trends"})
        logger.info(f"Google Trends: {len(trends)}개 키워드 수집")
        return trends
    except Exception as e:
        logger.warning(f"Google Trends 수집 실패 (무시하고 계속): {e}")
        return []


def fetch_naver_datalab_trends() -> list[dict]:
    """
    네이버 데이터랩 트렌드 수집.
    주의: 공식 API가 아닌 검색 RSS 활용 — 정식 지원 여부 확실하지 않음.
    """
    url = "https://www.naver.com/rss/trending"  # 추측입니다 — 실제 URL 확인 필요
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        trends = []
        for item in items[:20]:
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                trends.append({"keyword": title_el.text, "source": "naver"})
        logger.info(f"Naver Trends: {len(trends)}개 키워드 수집")
        return trends
    except Exception as e:
        logger.warning(f"Naver Trends 수집 실패 (무시하고 계속): {e}")
        return []


def fetch_reddit_kr_trends() -> list[dict]:
    """Reddit r/korea 최신 인기 포스트 제목 수집."""
    url = "https://www.reddit.com/r/korea/hot.json?limit=20"
    headers = {"User-Agent": "BlogAgent/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        posts = data.get("data", {}).get("children", [])
        trends = []
        for post in posts:
            title = post.get("data", {}).get("title", "")
            if title:
                trends.append({"keyword": title[:50], "source": "reddit_kr"})
        logger.info(f"Reddit KR: {len(trends)}개 키워드 수집")
        return trends
    except Exception as e:
        logger.warning(f"Reddit KR 수집 실패 (무시하고 계속): {e}")
        return []


def select_topics_via_gemini(
    raw_trends: list[dict],
    blog_domain: str,
    top_n: int = 3,
) -> list[dict]:
    """
    Gemini API를 통해 수집된 트렌드 중 블로그 도메인에 적합한 주제 top_n개 선정.
    Manager AI 역할: 전략적 주제 선정.
    """
    trends_text = "\n".join(
        [f"- [{t['source']}] {t['keyword']}" for t in raw_trends[:50]]
    )

    priority_cat = get_today_category()
    cat_kw_text = "\n".join(
        f"  {cat}({int(w*100)}%): {', '.join(CATEGORY_KEYWORDS[cat][:5])}"
        for cat, w in CATEGORY_WEIGHTS.items()
    )

    prompt = f"""
당신은 공장자동화·물류자동화·딥러닝비전 전문 블로그의 주제 선정 전문가입니다.

블로그 도메인: {blog_domain}
오늘 우선 카테고리: {priority_cat}

카테고리 우선순위 및 핵심 키워드:
{cat_kw_text}

현재 트렌드 목록:
{trends_text}

규칙:
1. 선정 주제 {top_n}개 중 최소 2개는 우선 카테고리({priority_cat}) 또는
   물류자동화/딥러닝비전에 연결 가능한 주제여야 함
2. 트렌드 키워드를 제조·자동화 관점으로 재해석해 연결할 것
3. 금융/식품/소비재/패션 주제는 절대 선정 금지

출력은 반드시 아래 JSON 형식만 반환하세요. 설명 없이 JSON만 출력:
{{
  "selected_topics": [
    {{
      "keyword": "선정 키워드",
      "angle": "포스트 접근 각도 (한 문장)",
      "reason": "선정 이유 (한 문장)",
      "category": "물류자동화|딥러닝비전|공장자동화|스마트팩토리|제어SW",
      "estimated_search_volume": "high|medium|low"
    }}
  ]
}}
"""

    raw = get_gemini_response(prompt)
    # JSON 펜스 제거
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break
    result = json.loads(raw.strip())
    logger.info(f"Gemini가 {len(result['selected_topics'])}개 주제 선정 완료")
    return result["selected_topics"]


def run_trend_agent(blog_domain: Optional[str] = None) -> list[dict]:
    """
    트렌드 에이전트 메인 실행 함수.
    Returns: 선정된 주제 리스트
    """
    config = load_config()
    domain = blog_domain or config["blog"]["default_category"]

    logger.info("=== Trend Agent 시작 ===")

    # 병렬 수집 (순차 실행 — 추후 asyncio로 개선 가능)
    all_trends = []
    all_trends.extend(fetch_google_trends_rss())
    all_trends.extend(fetch_naver_datalab_trends())
    all_trends.extend(fetch_reddit_kr_trends())

    if not all_trends:
        # 폴백: 빈 트렌드일 때 기본 주제 세트 사용
        logger.warning("모든 트렌드 소스 실패 — 폴백 키워드 사용")
        all_trends = [
            {"keyword": "AI 자동화 2025", "source": "fallback"},
            {"keyword": "물류 로봇 최신 트렌드", "source": "fallback"},
            {"keyword": "딥러닝 실무 적용 사례", "source": "fallback"},
        ]

    # EXCLUDE_KEYWORDS 필터링 (Gemini 전달 전 원천 차단)
    filtered_trends = [t for t in all_trends if is_valid_topic(t["keyword"])]
    excluded_count = len(all_trends) - len(filtered_trends)
    if excluded_count:
        logger.info(f"제외 키워드 필터: {excluded_count}개 키워드 제거됨")
    logger.info(f"총 {len(filtered_trends)}개 트렌드 키워드 Gemini 전달")

    selected = select_topics_via_gemini(
        raw_trends=filtered_trends,
        blog_domain=domain,
        top_n=config["trend"]["top_select"],
    )

    # Gemini 결과도 이중 필터링
    selected = [t for t in selected if is_valid_topic(t["keyword"])]

    # 로그 저장
    log_path = os.path.join(
        os.path.dirname(__file__), "..", "output", "logs",
        f"trend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "raw_count": len(all_trends),
            "selected": selected
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"트렌드 에이전트 완료 → {log_path}")
    return selected


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    topics = run_trend_agent()
    print(json.dumps(topics, ensure_ascii=False, indent=2))
