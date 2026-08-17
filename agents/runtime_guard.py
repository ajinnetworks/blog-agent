"""Runtime safeguards for provider failures and title cleanup.

- Avoid repeated Gemini/Claude calls within one workflow after hard quota/billing failures.
- Clean truncated technical titles at word/token boundaries before review/publish.
- Skip RPM sleeps when all external LLM providers are already disabled.
- Normalize deterministic Safe Mode titles to reviewer-recognized SEO patterns.
"""

import re

_PROVIDER_DISABLED = {"gemini": False, "claude": False}
SEO_PATTERNS = ("완전 정복", "도입 전", "해결한", "달성한")


def disable_provider(name: str) -> None:
    if name in _PROVIDER_DISABLED:
        _PROVIDER_DISABLED[name] = True


def provider_disabled(name: str) -> bool:
    return bool(_PROVIDER_DISABLED.get(name, False))


def all_llm_providers_disabled() -> bool:
    return provider_disabled("gemini") and provider_disabled("claude")


def classify_hard_provider_failure(exc: Exception) -> str | None:
    text = str(exc).lower()
    if any(x in text for x in ["quota", "resource_exhausted", "429", "free_tier_requests"]):
        return "gemini"
    if any(x in text for x in ["credit balance is too low", "purchase credits", "billing"]):
        return "claude"
    return None


def clean_title_boundary(title: str, limit: int = 40) -> str:
    title = " ".join(str(title or "").split()).strip()
    if len(title) <= limit:
        return title

    suffix = " | 아진네트웍스"
    base = title
    for marker in [" | 아진네트웍스", " — 아진네트웍스", " - 아진네트웍스"]:
        if title.endswith(marker):
            base = title[:-len(marker)].rstrip()
            break

    has_brand_suffix = title.endswith((" | 아진네트웍스", " — 아진네트웍스", " - 아진네트웍스"))
    max_base = limit - len(suffix) if has_brand_suffix else limit
    cut = base[:max_base].rstrip(" ·-/—")

    positions = [cut.rfind(ch) for ch in [" ", "·", "/", "-", "—", ",", ":", ";"]]
    boundary = max(positions)
    if boundary >= max(12, int(max_base * 0.60)):
        cut = cut[:boundary].rstrip(" ·-/—,:;")

    m = re.search(r"[A-Za-z0-9._]+$", cut)
    if m and m.start() > 0:
        cut = cut[:m.start()].rstrip(" ·-/—,:;")

    if has_brand_suffix:
        return (cut + suffix)[:limit]
    return cut[:limit]


def make_safe_mode_seo_title(keyword: str, limit: int = 40) -> str:
    """Build a concise title containing a reviewer-recognized SEO pattern."""
    suffix = " | 아진네트웍스"
    raw = " ".join(str(keyword or "산업자동화").split()).strip()

    if any(pattern in raw for pattern in SEO_PATTERNS):
        candidate = raw + suffix
        return clean_title_boundary(candidate, limit)

    # Prefer a factual, non-clickbait pattern that matches technical search intent.
    base_limit = max(8, limit - len(" 도입 전") - len(suffix))
    base = clean_title_boundary(raw, base_limit)
    candidate = f"{base} 도입 전{suffix}"
    return clean_title_boundary(candidate, limit)


def clean_post_titles(posts: list[dict]) -> list[dict]:
    for post in posts:
        if post.get("error"):
            continue
        old = str(post.get("title") or "")
        new = clean_title_boundary(old)
        if new:
            post["title"] = new
    return posts
