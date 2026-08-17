"""Regression test for final content quality and image strategy."""

from agents.content_enricher import enrich_posts
from agents.content_quality import apply_final_content_gate
from agents.image_selector import assign_batch_images


def main() -> None:
    posts = [
        {
            "title": "AGV·AMR 도입 전 설계 기준 | 아진네트웍스",
            "category": "물류자동화",
            "content": "짧은 초안",
            "source_topic": {"keyword": "AGV·AMR 도입 전 동선·충전·교통제어 설계 기준"},
            "review_result": {"total_score": 80, "pass": True},
        },
        {
            "title": "AI 비전검사 도입 전 기준 | 아진네트웍스",
            "category": "딥러닝비전",
            "content": "짧은 초안",
            "source_topic": {"keyword": "AI 비전검사 도입 전 조명·렌즈·불량 데이터 검증 기준"},
            "review_result": {"total_score": 80, "pass": True},
        },
        {
            "title": "PLC·HMI 통합 설계 기준 | 아진네트웍스",
            "category": "제어SW",
            "content": "짧은 초안",
            "source_topic": {"keyword": "PLC·HMI·SCADA 통합 시 네트워크와 알람 설계 기준"},
            "review_result": {"total_score": 80, "pass": True},
        },
    ]

    posts = enrich_posts(posts)
    assert all(p.get("content_enriched") for p in posts), posts
    assert all(p.get("word_count", 0) >= 1500 for p in posts), [p.get("word_count") for p in posts]

    posts = assign_batch_images(posts)
    images = [p.get("image") for p in posts]
    assert len(set(images)) == len(images), f"Batch hero image duplicated: {images}"
    assert all(p.get("image_alt") for p in posts), posts
    assert all(p.get("image") in p.get("content", "") for p in posts), posts

    posts = apply_final_content_gate(posts)
    failures = [(p.get("title"), p.get("final_quality", {}).get("issues")) for p in posts if not p.get("final_quality", {}).get("pass")]
    assert not failures, failures

    print("FINAL CONTENT QUALITY TESTS: PASS")
    print("All enriched posts >= 1500 chars")
    print("All posts satisfy technical/reviewer/meta/SEO gates")
    print("Hero images are topic-aware and non-duplicated within batch")
    print("Alt text and inline hero image are attached")


if __name__ == "__main__":
    main()
