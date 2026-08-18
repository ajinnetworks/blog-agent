"""Regression tests for runtime title cleanup and semantic hero selection."""

from agents.image_selector import select_image
from agents.runtime_guard import make_safe_mode_seo_title


def main() -> None:
    semiconductor_post = {
        "title": "반도체 클린룸 로봇 적용 시 Particle과 Cable Management 기준",
        "category": "공장자동화",
        "source_topic": {
            "keyword": "반도체 클린룸 로봇 적용 시 Particle과 Cable Management 기준",
            "angle": "반도체 클린룸 로봇의 Particle과 Cable Management 설계 기준",
        },
        "tags": ["반도체", "클린룸", "로봇자동화"],
        "seo_keywords": ["클린룸 로봇", "Particle", "Cable Management"],
    }
    image, _, _ = select_image(semiconductor_post)
    assert image == "/assets/img/hero-v2/robot-eoat.svg", image

    title = make_safe_mode_seo_title(
        "반도체 클린룸 로봇 적용 시 Particle과 Cable Management 기준"
    )
    assert len(title) <= 40, title
    assert not title.split(" | ", 1)[0].endswith(("과", "와", "및", "시")), title

    amr_title = make_safe_mode_seo_title(
        "AMR Fleet 운영 시 교차로 정체와 Deadlock을 줄이는 교통제어 기준"
    )
    assert len(amr_title) <= 40, amr_title
    assert not amr_title.split(" | ", 1)[0].endswith(("과", "와", "및", "시")), amr_title

    print("RUNTIME QUALITY REGRESSION TESTS: PASS")
    print(f"semiconductor_image={image}")
    print(f"semiconductor_title={title}")
    print(f"amr_title={amr_title}")


if __name__ == "__main__":
    main()
