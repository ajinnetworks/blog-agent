"""Runtime safeguards for provider failures and title cleanup.

- Avoid repeated Gemini/Claude calls within one workflow after hard quota/billing failures.
- Clean truncated technical titles at word/token boundaries before review/publish.
"""

import re

_PROVIDER_DISABLED = {"gemini": False, "claude": False}


def disable_provider(name: str) -> None:
    if name in _PROVIDER_DISABLED:
        _PROVIDER_DISABLED[name] = True


def provider_disabled(name: str) -> bool:
    return bool(_PROVIDER_DISABLED.get(name, False))


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

    max_base = limit - len(suffix) if title.endswith((" | 아진네트웍스", " — 아진네트웍스", " - 아진네트웍스")) else limit
    cut = base[:max_base].rstrip(" ·-/—")

    # Prefer a natural word/punctuation boundary when one is reasonably near the end.
    positions = [cut.rfind(ch) for ch in [" ", "·", "/", "-", "—", ",", ":", ";"]]
    boundary = max(positions)
    if boundary >= max(12, int(max_base * 0.60)):
        cut = cut[:boundary].rstrip(" ·-/—,:;")

    # Never leave a chopped ASCII technical token such as 'Fa' from Fail-safe.
    m = re.search(r"[A-Za-z0-9._]+$", cut)
    if m and m.start() > 0:
        cut = cut[:m.start()].rstrip(" ·-/—,:;")

    if title.endswith((" | 아진네트웍스", " — 아진네트웍스", " - 아진네트웍스")):
        return (cut + suffix)[:limit]
    return cut[:limit]


def clean_post_titles(posts: list[dict]) -> list[dict]:
    for post in posts:
        if post.get("error"):
            continue
        old = str(post.get("title") or "")
        new = clean_title_boundary(old)
        if new:
            post["title"] = new
    return posts
