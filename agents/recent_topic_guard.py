"""Recent Topic Guard V1 — prevent repetitive industrial blog topics.

Reads recent Jekyll posts from the configured blog repository, extracts titles,
and rejects proposed topics that are too similar to recently published content.
The guard is deterministic and remains active when external LLMs are unavailable.
"""

import logging
import os
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

from github import Auth, Github, GithubException

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")

STOPWORDS = {
    "아진네트웍스", "도입", "설계", "기준", "자동화", "시스템", "기술", "가이드",
    "분석", "적용", "구축", "연계", "활용", "전", "및", "위한", "하는", "줄이는",
}


def _normalize(text: str) -> str:
    text = re.sub(r"[^0-9a-zA-Z가-힣]+", " ", str(text).lower())
    return " ".join(text.split())


def _tokens(text: str) -> set[str]:
    return {t for t in _normalize(text).split() if len(t) >= 2 and t not in STOPWORDS}


def topic_similarity(a: str, b: str) -> float:
    """Hybrid lexical similarity: token overlap + normalized sequence similarity."""
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return 0.0
    ta, tb = _tokens(a), _tokens(b)
    jaccard = len(ta & tb) / max(1, len(ta | tb))
    sequence = SequenceMatcher(None, na, nb).ratio()
    containment = 1.0 if (na in nb or nb in na) and min(len(na), len(nb)) >= 8 else 0.0
    return max(jaccard, sequence * 0.78, containment)


def _date_from_filename(name: str):
    m = re.match(r"(\d{4}-\d{2}-\d{2})-", name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def _title_from_markdown(content: str, fallback_name: str) -> str:
    m = re.search(r"(?m)^title:\s*[\"']?(.*?)[\"']?\s*$", content)
    if m and m.group(1).strip():
        return m.group(1).strip()
    return re.sub(r"^\d{4}-\d{2}-\d{2}-|\.md$", "", fallback_name).replace("-", " ")


def load_recent_titles(days: int = 60, max_posts: int = 120) -> list[str]:
    """Load recent published titles from BLOG_REPO. Fail open on GitHub read errors."""
    token = os.getenv("BLOG_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("BLOG_REPO") or os.getenv("GITHUB_REPO")
    branch = os.getenv("GITHUB_BRANCH", "main")
    posts_path = os.getenv("GITHUB_POSTS_PATH", "_posts")
    if not token or not repo_name:
        logger.warning("[TOPIC-GUARD] GitHub config missing; recent-title check skipped")
        return []

    cutoff = datetime.now(KST).date() - timedelta(days=days)
    try:
        repo = Github(auth=Auth.Token(token)).get_repo(repo_name)
        entries = repo.get_contents(posts_path, ref=branch)
        candidates = []
        for item in entries:
            if getattr(item, "type", "") != "file" or not item.name.endswith(".md"):
                continue
            post_date = _date_from_filename(item.name)
            if post_date and post_date >= cutoff:
                candidates.append((post_date, item))
        candidates.sort(key=lambda x: x[0], reverse=True)

        titles = []
        for _, item in candidates[:max_posts]:
            try:
                raw = item.decoded_content.decode("utf-8", errors="ignore")
                titles.append(_title_from_markdown(raw, item.name))
            except Exception as exc:
                logger.warning("[TOPIC-GUARD] title read skipped: %s (%s)", item.name, exc)
        logger.info("[TOPIC-GUARD] loaded %s titles from last %s days", len(titles), days)
        return titles
    except GithubException as exc:
        logger.warning("[TOPIC-GUARD] GitHub history read failed; fail-open: %s", exc)
        return []


def filter_recent_topics(topics: list[dict], recent_titles: list[str] | None = None,
                         days: int = 60, threshold: float = 0.62) -> tuple[list[dict], list[dict]]:
    """Reject topics similar to recent titles or another topic already accepted in this batch."""
    history = list(recent_titles) if recent_titles is not None else load_recent_titles(days=days)
    accepted, rejected = [], []

    for topic in topics:
        keyword = str(topic.get("keyword", "")).strip()
        comparisons = history + [t.get("keyword", "") for t in accepted]
        best_title, best_score = "", 0.0
        for existing in comparisons:
            score = topic_similarity(keyword, existing)
            if score > best_score:
                best_title, best_score = existing, score

        if best_score >= threshold:
            rejected.append({"topic": topic, "matched_title": best_title, "similarity": round(best_score, 3)})
            logger.warning("[TOPIC-GUARD] rejected '%s' ~= '%s' (%.3f)", keyword, best_title, best_score)
        else:
            accepted.append(topic)

    return accepted, rejected
