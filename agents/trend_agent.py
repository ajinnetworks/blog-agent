"""
trend_agent.py — 트렌드 크롤링 & 주제 선정 에이전트
Goal: 실시간 트렌드에서 블로그 포스팅 키워드 3개 선정
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

import anthropic
import requests
import yaml

logger = logging.getLogger(__name__)


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


def select_topics_via_claude(
    raw_trends: list[dict],
    blog_domain: str,
    top_n: int = 3,
) -> list[dict]:
    """
    Claude API를 통해 수집된 트렌드 중 블로그 도메인에 적합한 주제 top_n개 선정.
    Manager AI 역할: 전략적 주제 선정.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    trends_text = "\n".join(
        [f"- [{t['source']}] {t['keyword']}" for t in raw_trends[:50]]
    )

    prompt = f"""
당신은 블로그 주제 선정 전문가입니다.

블로그 도메인: {blog_domain}
현재 트렌드 목록:
{trends_text}

위 트렌드 중에서 블로그 도메인과 연관성이 높고,
검색 유입이 기대되는 주제를 {top_n}개 선정하세요.

출력은 반드시 아래 JSON 형식만 반환하세요. 설명 없이 JSON만 출력:
{{
  "selected_topics": [
    {{
      "keyword": "선정 키워드",
      "angle": "포스트 접근 각도 (한 문장)",
      "reason": "선정 이유 (한 문장)",
      "estimated_search_volume": "high|medium|low"
    }}
  ]
}}
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # JSON 펜스 제거
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    result = json.loads(raw.strip())
    logger.info(f"Claude가 {len(result['selected_topics'])}개 주제 선정 완료")
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

    logger.info(f"총 {len(all_trends)}개 트렌드 키워드 수집됨")

    selected = select_topics_via_claude(
        raw_trends=all_trends,
        blog_domain=domain,
        top_n=config["trend"]["top_select"],
    )

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
