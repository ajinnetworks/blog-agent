"""Regression tests for Safe Mode Content Engine V2."""

from agents.content_enricher import enrich_post
from agents.recent_topic_guard import PHASE3_TOPIC_POOL, refill_topics
from agents.safe_content_engine_v2 import CATEGORY_ORDER, DOMAIN_PROFILES, build_topic_pool


def main() -> None:
    pools = build_topic_pool()
    assert set(pools) == set(CATEGORY_ORDER), pools.keys()
    assert all(len(pools[c]) >= 20 for c in CATEGORY_ORDER), {c: len(pools[c]) for c in CATEGORY_ORDER}
    assert sum(len(v) for v in pools.values()) >= 180
    assert PHASE3_TOPIC_POOL == pools
    assert all(c in DOMAIN_PROFILES for c in CATEGORY_ORDER)

    # With no history, deterministic round-robin refill must still spread categories.
    topics = refill_topics([], [], target_count=3, threshold=0.62)
    assert len(topics) == 3, topics
    assert len({t["category"] for t in topics}) >= 2, topics

    samples = [
        ("물류자동화", "AMR Fleet 교차로·Deadlock 교통제어 설계 시 사전 검증 기준", "Fleet Manager", "물동량/시간"),
        ("딥러닝비전", "AI 비전검사 DOE·Golden Sample·조명조건 설계 시 사전 검증 기준", "Trigger", "검사 Sample"),
        ("자동차자동화", "중량부품 Gripper 안전율과 Fail-safe 설계 시 사전 검증 기준", "차종 Recipe", "부품도면/중량"),
        ("의료기기자동화", "카테터 권선 장력과 최소 굽힘반경 설계 시 사전 검증 기준", "Audit Trail", "제품 Sample/도면"),
        ("반도체자동화", "클린룸 로봇 Particle과 Cable Management 설계 시 사전 검증 기준", "SECS/GEM", "Wafer/FOUP 규격"),
    ]
    bodies = []
    for category, keyword, control_marker, rfq_marker in samples:
        post = enrich_post({
            "title": keyword,
            "category": category,
            "content": "짧은 초안",
            "source_topic": {"keyword": keyword, "category": category},
        })
        body = post["content"]
        assert post["generation_provider"] == "safe-mode-content-engine-v2"
        assert post["content_template"] == category
        assert post["word_count"] >= 1700, (category, post["word_count"])
        assert control_marker in body, (category, control_marker)
        assert rfq_marker in body, (category, rfq_marker)
        bodies.append(body)

    # Category-specific profiles must create materially different deterministic bodies.
    assert len(set(bodies)) == len(bodies)

    print("SAFE MODE CONTENT ENGINE V2 TESTS: PASS")
    print("Categories: 9 | minimum topics/category: 20 | total topics >= 180")
    print("Category-specific mechanism/control/validation/RFQ templates: PASS")


if __name__ == "__main__":
    main()
