"""Regression test for Phase 2 post image front matter."""

import frontmatter

from agents.publisher_image_bridge import install
from agents import github_publisher as gp


def main() -> None:
    install()
    post = {
        "title": "AGV·AMR 도입 전 설계 기준 | 아진네트웍스",
        "content": "# 테스트\n\n본문",
        "category": "물류자동화",
        "tags": ["AGV", "AMR", "물류자동화"],
        "meta_description": "AGV와 AMR 도입 전 동선, 충전, 교통제어를 검토하는 기술 기준을 정리한 테스트 설명입니다.",
        "seo_keywords": ["AGV", "AMR", "물류자동화"],
        "image": "/assets/img/hero/logistics.jpg",
        "image_alt": "AGV AMR 물류자동화 설계 대표 이미지",
        "og_image": "/assets/img/hero/logistics.jpg",
        "review_result": {"pass": True, "total_score": 90},
    }
    _, markdown = gp.post_to_jekyll_markdown(post)
    parsed = frontmatter.loads(markdown)
    assert parsed.get("image") == post["image"]
    assert parsed.get("og_image") == post["og_image"]
    assert parsed.get("image_alt") == post["image_alt"]
    assert parsed.get("image_strategy")
    print("PHASE 2 IMAGE FRONT MATTER TESTS: PASS")
    print(f"image={parsed.get('image')}")
    print(f"og_image={parsed.get('og_image')}")
    print(f"image_alt={parsed.get('image_alt')}")


if __name__ == "__main__":
    main()
