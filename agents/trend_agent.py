"""
trend_agent.py — 트렌드 크롤링 & 주제 선정 에이전트
Goal: 실시간 트렌드에서 블로그 포스팅 키워드 3개 선정
"""

import json
import logging
import os
import random
from datetime import datetime
from typing import Optional

from google import genai as google_genai
import requests
import yaml

GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest",
]

import io
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from agents.writer_agent import is_valid_topic
from agents.llm_fallback import validate_selected_topics

logger = logging.getLogger(__name__)

CATEGORY_WEIGHTS = {
    "물류자동화": 0.35,
    "딥러닝비전": 0.30,
    "공장자동화": 0.15,
    "스마트팩토리": 0.12,
    "제어SW": 0.08,
}

CATEGORY_KEYWORDS = {
    "물류자동화": ["AGV", "AMR", "컨베이어", "소터", "WMS", "물류자동화", "자동창고", "피킹", "팔레타이징", "물류로봇", "배송자동화"],
    "딥러닝비전": ["딥러닝 비전", "머신비전", "비전검사", "불량검출", "AI 검사", "결함검출", "OCR", "3D비전", "외관검사", "반도체 검사", "웨이퍼", "AOI", "클린룸", "OLED 검사", "LCD 패널", "디스플레이 검사"],
    "공장자동화": ["공장자동화", "로봇자동화", "CNC", "픽앤플레이스", "포장자동화", "용접자동화", "조립자동화", "박스포장", "테이핑", "라벨링", "슈링크포장", "차체용접", "도장자동화", "EV배터리조립", "의장라인"],
    "스마트팩토리": ["스마트팩토리", "MES", "디지털트윈", "OEE", "예지보전", "IoT", "엣지AI", "스마트센서", "서보모터", "리니어가이드", "그리퍼", "액추에이터"],
    "제어SW": ["PLC", "SCADA", "HMI", "Siemens", "Mitsubishi", "LS산전", "필드버스", "모션제어"],
}

INDUSTRY_TO_CATEGORY = {"반도체": "딥러닝비전", "디스플레이": "딥러닝비전", "포장": "공장자동화", "자동차": "공장자동화", "부품": "스마트팩토리"}


def get_today_category() -> str:
    weekday = datetime.now().weekday()
    rotation_map = {1: "물류자동화", 3: "딥러닝비전", 5: "공장자동화"}
    cats = list(CATEGORY_WEIGHTS.keys())
    weights = list(CATEGORY_WEIGHTS.values())
    return rotation_map.get(weekday, random.choices(cats, weights=weights, k=1)[0])


def map_industry_to_category(keyword: str) -> str:
    for industry, category in INDUSTRY_TO_CATEGORY.items():
        if industry in keyword:
            return category
    return get_today_category()


def get_gemini_response(prompt: str) -> str:
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
    url = "https://trends.google.com/trending/rss?geo=KR"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.content)
        trends = []
        for item in root.findall(".//item")[:20]:
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                trends.append({"keyword": title_el.text, "source": "google_trends"})
        logger.info(f"Google Trends: {len(trends)}개 키워드 수집")
        return trends
    except Exception as e:
        logger.warning(f"Google Trends 수집 실패 (무시하고 계속): {e}")
        return []


def fetch_naver_datalab_trends() -> list[dict]:
    url = "https://www.naver.com/rss/trending"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.content)
        trends = []
        for item in root.findall(".//item")[:20]:
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                trends.append({"keyword": title_el.text, "source": "naver"})
        logger.info(f"Naver Trends: {len(trends)}개 키워드 수집")
        return trends
    except Exception as e:
        logger.warning(f"Naver Trends 수집 실패 (무시하고 계속): {e}")
        return []


def fetch_reddit_kr_trends() -> list[dict]:
    url = "https://www.reddit.com/r/korea/hot.json?limit=20"
    headers = {"User-Agent": "BlogAgent/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        trends = []
        for post in data.get("data", {}).get("children", []):
            title = post.get("data", {}).get("title", "")
            if title:
                trends.append({"keyword": title[:50], "source": "reddit_kr"})
        logger.info(f"Reddit KR: {len(trends)}개 키워드 수집")
        return trends
    except Exception as e:
        logger.warning(f"Reddit KR 수집 실패 (무시하고 계속): {e}")
        return []


def select_topics_via_gemini(raw_trends: list[dict], blog_domain: str, top_n: int = 3) -> list[dict]:
    trends_text = "\n".join([f"- [{t['source']}] {t['keyword']}" for t in raw_trends[:50]])
    priority_cat = get_today_category()
    cat_kw_text = "\n".join(f"  {cat}({int(w*100)}%): {', '.join(CATEGORY_KEYWORDS[cat][:5])}" for cat, w in CATEGORY_WEIGHTS.items())

    prompt = f"""
당신은 공장자동화·물류자동화·딥러닝비전 전문 블로그의 주제 선정 전문가입니다.
블로그 도메인: {blog_domain}
오늘 우선 카테고리: {priority_cat}
카테고리 우선순위 및 핵심 키워드:
{cat_kw_text}
현재 트렌드 목록:
{trends_text}
규칙:
1. 선정 주제 {top_n}개 중 최소 2개는 우선 카테고리({priority_cat}) 또는 물류자동화/딥러닝비전에 연결 가능한 주제여야 함
2. 트렌드를 제조·자동화 관점으로 재해석하되 원래의 비산업 사건/연예/인사/금융 맥락을 제목에 남기지 말 것
3. 정년/퇴직/사원/연예/금융/식품/소비재/패션/여행 주제는 절대 선정 금지
출력은 반드시 JSON 형식만 반환:
{{"selected_topics":[{{"keyword":"선정 키워드","angle":"포스트 접근 각도","reason":"선정 이유","category":"물류자동화|딥러닝비전|공장자동화|스마트팩토리|제어SW","estimated_search_volume":"high|medium|low"}}]}}
"""
    raw = get_gemini_response(prompt)
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break
    result = json.loads(raw.strip())
    proposed = result.get("selected_topics", [])
    validated = validate_selected_topics(proposed, priority=priority_cat, top_n=top_n)
    rejected_count = max(0, len(proposed) - len([p for p in proposed if any(v.get("keyword") == p.get("keyword") for v in validated)]))
    logger.info(f"LLM 주제 후검증 완료: 제안 {len(proposed)}개 / 최종 {len(validated)}개 / 대체·제거 {rejected_count}개")
    return validated


def run_trend_agent(blog_domain: Optional[str] = None) -> list[dict]:
    config = load_config()
    domain = blog_domain or config["blog"]["default_category"]
    logger.info("=== Trend Agent 시작 ===")

    all_trends = []
    all_trends.extend(fetch_google_trends_rss())
    all_trends.extend(fetch_naver_datalab_trends())
    all_trends.extend(fetch_reddit_kr_trends())

    if not all_trends:
        logger.warning("모든 트렌드 소스 실패 — 산업 폴백 키워드 사용")
        all_trends = [
            {"keyword": "AGV AMR 물류자동화", "source": "fallback"},
            {"keyword": "AI 비전검사 불량검출", "source": "fallback"},
            {"keyword": "산업용 로봇 자동화 설비", "source": "fallback"},
        ]

    filtered_trends = [t for t in all_trends if is_valid_topic(t["keyword"])]
    excluded_count = len(all_trends) - len(filtered_trends)
    if excluded_count:
        logger.info(f"기본 제외 키워드 필터: {excluded_count}개 제거됨")
    logger.info(f"총 {len(filtered_trends)}개 트렌드 키워드 LLM 전달")

    selected = select_topics_via_gemini(raw_trends=filtered_trends, blog_domain=domain, top_n=config["trend"]["top_select"])
    # Last line of defense: validate again after all parsing/transforms.
    selected = validate_selected_topics(selected, priority=get_today_category(), top_n=config["trend"]["top_select"])

    log_path = os.path.join(os.path.dirname(__file__), "..", "output", "logs", f"trend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "raw_count": len(all_trends), "selected": selected}, f, ensure_ascii=False, indent=2)

    logger.info(f"트렌드 에이전트 완료 → {log_path}")
    return selected


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    topics = run_trend_agent()
    print(json.dumps(topics, ensure_ascii=False, indent=2))
