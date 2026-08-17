"""Regression tests for Ajin Networks industrial safe-mode.

These tests intentionally include previously observed bad topics.
The workflow must fail before publishing if any unrelated topic leaks through.
"""

from agents.llm_fallback import (
    _industrial_score,
    _select_industrial_topics,
    NON_INDUSTRIAL_BLOCKLIST,
    SAFE_TOPIC_POOL,
)


def assert_rejected(topic: str) -> None:
    score, category = _industrial_score(topic)
    assert score < 2 or category is None, f"Non-industrial topic leaked: {topic} score={score} category={category}"


def assert_accepted(topic: str) -> None:
    score, category = _industrial_score(topic)
    assert score >= 2 and category, f"Industrial topic rejected: {topic} score={score} category={category}"


def main() -> None:
    # Actual bad topics observed in Run 32066326019.
    for topic in ["정년", "최애의 사원", "퇴직", "연예인 콘서트", "주식 전망", "여행 맛집"]:
        assert_rejected(topic)

    # Representative Ajin Networks industrial topics must remain accepted.
    for topic in [
        "AGV AMR 물류자동화",
        "AI 비전검사 불량검출",
        "산업용 로봇 자동화 설비",
        "PLC HMI SCADA 제어",
        "자동차 열처리 로봇 핸들링",
        "의료기기 카테터 파우치 포장자동화",
    ]:
        assert_accepted(topic)

    # Simulate an all-bad trend feed. Output must be replaced entirely by vetted industrial seeds.
    prompt = '''
오늘 우선 카테고리: 물류자동화
현재 트렌드 목록:
- [google_trends] 정년
- [google_trends] 최애의 사원
- [google_trends] 퇴직
출력은 반드시 아래 JSON 형식만 반환하세요.
{"selected_topics": []}
'''
    selected = _select_industrial_topics(prompt, top_n=3)
    assert len(selected) == 3, selected
    for item in selected:
        keyword = item["keyword"]
        score, category = _industrial_score(keyword)
        assert score >= 2 and category, f"Unsafe fallback topic: {item}"
        assert not any(blocked.lower() in keyword.lower() for blocked in NON_INDUSTRIAL_BLOCKLIST), item

    # Every vetted seed itself must satisfy the industrial gate.
    for category, topics in SAFE_TOPIC_POOL.items():
        for topic in topics:
            score, detected = _industrial_score(topic)
            assert score >= 2 and detected, f"Seed failed gate: {category} / {topic} / {score} / {detected}"

    print("SAFE-MODE REGRESSION TESTS: PASS")
    print("Rejected bad topics: 정년, 최애의 사원, 퇴직, entertainment/finance/travel examples")
    print("All-bad trend feed replaced with vetted Ajin industrial topics")


if __name__ == "__main__":
    main()
