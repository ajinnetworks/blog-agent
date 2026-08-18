"""Image Selector V2 for Ajin Networks.

Selection priority:
1) topic/image semantic relevance
2) recent/batch duplication penalty
3) category fallback

The selector never prefers an unrelated image merely to avoid a duplicate.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HeroAsset:
    path: str
    label: str
    categories: tuple[str, ...]
    keywords: tuple[str, ...]
    fallback_rank: int = 50


ASSETS: tuple[HeroAsset, ...] = (
    HeroAsset("/assets/img/hero-v2/logistics-amr.svg", "AGV·AMR 물류", ("물류자동화",), ("agv", "amr", "자율주행", "충전", "교통제어", "물류로봇"), 1),
    HeroAsset("/assets/img/hero-v2/logistics-asrs.svg", "자동창고·WMS", ("물류자동화",), ("자동창고", "as/rs", "asrs", "wms", "입출고", "창고", "피킹"), 2),
    HeroAsset("/assets/img/hero-v2/palletizing.svg", "팔레타이징", ("물류자동화", "포장자동화", "로봇자동화"), ("팔레타이징", "팔레트", "컨베이어", "박스", "적재"), 3),
    HeroAsset("/assets/img/hero-v2/robot-eoat.svg", "로봇·EOAT", ("로봇자동화", "공장자동화"), ("로봇", "그리퍼", "엔드이펙터", "eoat", "payload", "moment", "티칭", "반도체", "클린룸", "particle", "cable management"), 4),
    HeroAsset("/assets/img/hero-v2/vision-inspection.svg", "AI 비전검사", ("딥러닝비전", "비전검사"), ("비전", "검사", "카메라", "조명", "렌즈", "불량", "딥러닝", "aoi", "ocr"), 5),
    HeroAsset("/assets/img/hero-v2/plc-control.svg", "PLC·HMI·SCADA", ("제어SW", "PLC제어", "공장자동화"), ("plc", "hmi", "scada", "opc", "profinet", "ethercat", "modbus", "인터록", "제어"), 6),
    HeroAsset("/assets/img/hero-v2/smart-oee.svg", "OEE·스마트팩토리", ("스마트팩토리",), ("oee", "mes", "예지보전", "iiot", "데이터", "스마트팩토리", "설비모니터링", "디지털트윈"), 7),
    HeroAsset("/assets/img/hero-v2/packaging-line.svg", "포장자동화", ("포장자동화",), ("포장", "카토닝", "실링", "라벨", "파우치", "테이핑", "슈링크"), 8),
    HeroAsset("/assets/img/hero/logistics.jpg", "물류자동화 기본", ("물류자동화",), ("물류", "컨베이어", "자동창고"), 20),
    HeroAsset("/assets/img/hero/vision.jpg", "비전검사 기본", ("딥러닝비전", "비전검사"), ("비전", "검사"), 21),
    HeroAsset("/assets/img/hero/control.jpg", "제어 기본", ("제어SW", "PLC제어"), ("plc", "제어"), 22),
    HeroAsset("/assets/img/hero/smart.jpg", "스마트팩토리 기본", ("스마트팩토리",), ("스마트팩토리", "mes", "oee"), 23),
    HeroAsset("/assets/img/hero/factory.jpg", "공장자동화 기본", ("공장자동화", "로봇자동화", "포장자동화"), ("공장", "자동화", "로봇"), 24),
)


def _topic_text(post: dict) -> str:
    parts = [
        post.get("title", ""),
        post.get("category", ""),
        post.get("source_topic", {}).get("keyword", ""),
        post.get("source_topic", {}).get("angle", ""),
        " ".join(post.get("seo_keywords", []) or []),
        " ".join(post.get("tags", []) or []),
    ]
    return " ".join(str(x) for x in parts if x).lower()


def _asset_score(asset: HeroAsset, post: dict, used_counts: dict[str, int]) -> int:
    text = _topic_text(post)
    category = str(post.get("category") or "")
    score = 0

    if category in asset.categories:
        score += 45
    elif any(c in category or category in c for c in asset.categories if category):
        score += 30

    matched = sum(1 for kw in asset.keywords if kw.lower() in text)
    score += min(matched, 5) * 18

    if "/hero-v2/" in asset.path:
        score += 8

    score -= used_counts.get(asset.path, 0) * 22
    score -= asset.fallback_rank
    return score


def rank_images(post: dict, used_counts: dict[str, int] | None = None) -> list[tuple[int, HeroAsset]]:
    used_counts = used_counts or {}
    ranked = [(_asset_score(asset, post, used_counts), asset) for asset in ASSETS]
    ranked.sort(key=lambda x: (-x[0], x[1].fallback_rank, x[1].path))
    return ranked


def select_image(post: dict, used_counts: dict[str, int] | None = None) -> tuple[str, int, str]:
    ranked = rank_images(post, used_counts)
    if not ranked:
        return "/assets/img/og-default.png", 0, "default"
    score, asset = ranked[0]
    if score < 10:
        return "/assets/img/og-default.png", score, "default"
    return asset.path, score, asset.label


def build_image_alt(post: dict, label: str = "산업자동화") -> str:
    keyword = post.get("source_topic", {}).get("keyword") or post.get("title") or "산업자동화"
    category = post.get("category") or "산업자동화"
    return f"{keyword} 관련 {label} 이미지 - {category} 아진네트웍스 기술 콘텐츠"


def assign_batch_images(posts: list[dict]) -> list[dict]:
    used_counts: dict[str, int] = {}
    for post in posts:
        if post.get("error"):
            continue

        image, relevance_score, label = select_image(post, used_counts)
        used_counts[image] = used_counts.get(image, 0) + 1
        alt = build_image_alt(post, label)

        post["image"] = image
        post["image_alt"] = alt
        post["image_strategy"] = "relevance-first-v2"
        post["image_relevance_score"] = relevance_score
        post["image_label"] = label

        content = str(post.get("content") or "")
        image_md = f"![{alt}]({image})"
        if image not in content:
            post["content"] = image_md + "\n\n" + content
    return posts
