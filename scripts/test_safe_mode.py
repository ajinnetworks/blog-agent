"""Regression tests for Ajin Networks industrial safe-mode and reviewer persistence."""

from unittest.mock import patch

from agents.llm_fallback import (
    _industrial_score,
    _select_industrial_topics,
    validate_selected_topics,
    NON_INDUSTRIAL_BLOCKLIST,
    SAFE_TOPIC_POOL,
    _short_safe_title,
)
from agents.writer_agent import _normalize_title
from agents import reviewer_agent


def assert_rejected(topic: str) -> None:
    score, category = _industrial_score(topic)
    assert score < 2 or category is None, f"Non-industrial topic leaked: {topic} score={score} category={category}"


def assert_accepted(topic: str) -> None:
    score, category = _industrial_score(topic)
    assert score >= 2 and category, f"Industrial topic rejected: {topic} score={score} category={category}"


def test_reviewer_revision_persistence() -> None:
    original = {
        "title": "예지보전 센서 데이터 수집과 PLC·MES 연계",
        "content": "원본 본문",
        "category": "스마트팩토리",
        "source_topic": {"keyword": "예지보전"},
        "draft_path": "draft.md",
    }
    initial_review = {
        "total_score": 70,
        "pass": False,
        "min_score": 75,
        "issues": [{"severity": "medium", "description": "SEO 보완"}],
        "revision_notes": "SEO 보완",
    }
    revised = {
        "title": "예지보전 데이터 연계 도입 전 체크리스트",
        "content": "개선 본문",
        "category": "스마트팩토리",
        "source_topic": original["source_topic"],
        "draft_path": original["draft_path"],
        "revised": True,
    }
    passed_review = {
        "total_score": 90,
        "pass": True,
        "min_score": 75,
        "issues": [],
        "revision_notes": "통과",
    }

    with patch.object(reviewer_agent, "load_config", return_value={"reviewer": {"min_score": 75}}), \
         patch.object(reviewer_agent, "batch_review_posts", return_value=[initial_review]), \
         patch.object(reviewer_agent, "revise_post", return_value=revised), \
         patch.object(reviewer_agent, "review_post", return_value=passed_review):
        result = reviewer_agent.run_reviewer_agent([original], max_revisions=1)

    assert len(result) == 1
    assert result[0]["title"] == revised["title"], result[0]
    assert result[0]["content"] == revised["content"], result[0]
    assert result[0]["review_result"]["pass"] is True, result[0]
    assert result[0]["review_result"]["total_score"] == 90, result[0]


def main() -> None:
    for topic in ["정년", "최애의 사원", "퇴직", "연예인 콘서트", "주식 전망", "여행 맛집"]:
        assert_rejected(topic)

    for topic in [
        "AGV AMR 물류자동화",
        "AI 비전검사 불량검출",
        "산업용 로봇 자동화 설비",
        "PLC HMI SCADA 제어",
        "자동차 열처리 로봇 핸들링",
        "의료기기 카테터 파우치 포장자동화",
    ]:
        assert_accepted(topic)

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

    contaminated = [
        {"keyword": "정년 퇴직 육안검사 딥러닝 비전 전환", "category": "딥러닝비전"},
        {"keyword": "AMR 비전 기반 안전 구역 인식", "category": "물류자동화"},
        {"keyword": "비정형 불량검출 딥러닝 비전 AI 솔루션", "category": "딥러닝비전"},
    ]
    cleaned = validate_selected_topics(contaminated, priority="딥러닝비전", top_n=3)
    assert len(cleaned) == 3, cleaned
    assert all("정년" not in x["keyword"] and "퇴직" not in x["keyword"] for x in cleaned), cleaned
    for item in cleaned:
        score, category = _industrial_score(item["keyword"])
        assert score >= 2 and category, item

    for category, topics in SAFE_TOPIC_POOL.items():
        for topic in topics:
            score, detected = _industrial_score(topic)
            assert score >= 2 and detected, f"Seed failed gate: {category} / {topic} / {score} / {detected}"
            assert len(_short_safe_title(topic)) <= 40

    assert len(_normalize_title("산업용 로봇 자동화 도입 전 Cycle Time과 가동률 검토 방법 — 아진네트웍스 기술 가이드")) <= 40
    assert _normalize_title("")
    assert len(_normalize_title("")) <= 40

    test_reviewer_revision_persistence()

    print("SAFE-MODE REGRESSION TESTS: PASS")
    print("Blocked topics stay blocked even when LLM mixes them with industrial terms")
    print("All selected/fallback topics pass industrial gate")
    print("Writer titles are guaranteed <= 40 characters")
    print("Reviewer revised post and pass status persist into final output")


if __name__ == "__main__":
    main()
