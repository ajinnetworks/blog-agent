"""Topic-aware hero image selector for Ajin Networks GitHub Pages posts.

Uses the current curated hero library in ajinnetworks.github.io.
It avoids repeating the same hero inside one publishing batch whenever possible.
"""

import hashlib

HERO_LIBRARY = {
    "물류자동화": ["/assets/img/hero/logistics.jpg", "/assets/img/hero/factory.jpg"],
    "딥러닝비전": ["/assets/img/hero/vision.jpg", "/assets/img/hero/smart.jpg"],
    "비전검사": ["/assets/img/hero/vision.jpg", "/assets/img/hero/smart.jpg"],
    "제어SW": ["/assets/img/hero/control.jpg", "/assets/img/hero/smart.jpg"],
    "PLC제어": ["/assets/img/hero/control.jpg", "/assets/img/hero/smart.jpg"],
    "스마트팩토리": ["/assets/img/hero/smart.jpg", "/assets/img/hero/factory.jpg"],
    "공장자동화": ["/assets/img/hero/factory.jpg", "/assets/img/hero/control.jpg"],
    "포장자동화": ["/assets/img/hero/factory.jpg", "/assets/img/hero/logistics.jpg"],
    "로봇자동화": ["/assets/img/hero/factory.jpg", "/assets/img/hero/logistics.jpg"],
}

ALL_HEROES = [
    "/assets/img/hero/logistics.jpg",
    "/assets/img/hero/vision.jpg",
    "/assets/img/hero/control.jpg",
    "/assets/img/hero/smart.jpg",
    "/assets/img/hero/factory.jpg",
]


def _category_candidates(category: str) -> list[str]:
    category = str(category or "")
    if category in HERO_LIBRARY:
        return HERO_LIBRARY[category]
    for key, values in HERO_LIBRARY.items():
        if key in category or category in key:
            return values
    return ALL_HEROES


def build_image_alt(post: dict) -> str:
    keyword = post.get("source_topic", {}).get("keyword") or post.get("title") or "산업자동화"
    category = post.get("category") or "산업자동화"
    return f"{keyword} 관련 {category} 기술 구성 및 아진네트웍스 자동화 솔루션 대표 이미지"


def assign_batch_images(posts: list[dict]) -> list[dict]:
    used = set()
    for post in posts:
        if post.get("error"):
            continue
        title = str(post.get("title") or "")
        candidates = _category_candidates(post.get("category")) + ALL_HEROES
        ordered = []
        for img in candidates:
            if img not in ordered:
                ordered.append(img)

        seed = int(hashlib.sha256(title.encode("utf-8")).hexdigest()[:8], 16) if title else 0
        if ordered:
            start = seed % len(ordered)
            ordered = ordered[start:] + ordered[:start]

        image = next((img for img in ordered if img not in used), ordered[0] if ordered else "/assets/img/og-default.png")
        used.add(image)
        alt = build_image_alt(post)
        post["image"] = image
        post["image_alt"] = alt
        post["image_strategy"] = "topic-aware-curated-hero"

        content = str(post.get("content") or "")
        image_md = f"![{alt}]({image})"
        if image not in content:
            post["content"] = image_md + "\n\n" + content
    return posts
