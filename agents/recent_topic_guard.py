"""Phase 3 topic guard and category rotation for Ajin Networks blog automation.

Responsibilities:
- Read recently published Jekyll titles from BLOG_REPO.
- Reject proposed topics that are too similar to recent content or same-run topics.
- Refill rejected slots from the Safe Mode Content Engine V2 topic universe.
- Keep deterministic behavior when external LLM providers are unavailable.
"""

import logging
import os
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

from github import Auth, Github, GithubException
from agents.safe_content_engine_v2 import CATEGORY_ORDER, build_topic_pool

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")

STOPWORDS = {
    "아진네트웍스", "도입", "설계", "기준", "자동화", "시스템", "기술", "가이드",
    "분석", "적용", "구축", "연계", "활용", "전", "및", "위한", "하는", "줄이는",
    "운영", "안정화", "고장복구", "방법", "사전", "검증",
}

PHASE3_TOPIC_POOL = build_topic_pool()


def _normalize(text: str) -> str:
    text = re.sub(r"[^0-9a-zA-Z가-힣]+", " ", str(text).lower())
    return " ".join(text.split())


def _tokens(text: str) -> set[str]:
    return {t for t in _normalize(text).split() if len(t) >= 2 and t not in STOPWORDS}


def topic_similarity(a: str, b: str) -> float:
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
    token = (os.getenv("BLOG_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip()
    repo_name = (os.getenv("BLOG_REPO") or os.getenv("GITHUB_REPO") or "").strip()
    branch = os.getenv("GITHUB_BRANCH", "main").strip()
    posts_path = os.getenv("GITHUB_POSTS_PATH", "_posts").strip()
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


def _rotation_start(now: datetime | None = None) -> int:
    now = now or datetime.now(KST)
    return (now.toordinal() + now.isocalendar().week) % len(CATEGORY_ORDER)


def refill_topics(accepted: list[dict], recent_titles: list[str], target_count: int = 3,
                  threshold: float = 0.62, now: datetime | None = None) -> list[dict]:
    result = list(accepted)
    if len(result) >= target_count:
        return result[:target_count]

    start = _rotation_start(now)
    categories = CATEGORY_ORDER[start:] + CATEGORY_ORDER[:start]
    existing_titles = list(recent_titles) + [x.get("keyword", "") for x in result]
    selected_index = {category: 0 for category in categories}

    while len(result) < target_count:
        added_this_pass = False
        for category in categories:
            pool = PHASE3_TOPIC_POOL.get(category, [])
            idx = selected_index[category]
            chosen = None
            while idx < len(pool):
                keyword = pool[idx]
                idx += 1
                best = max((topic_similarity(keyword, old) for old in existing_titles), default=0.0)
                if best < threshold:
                    chosen = keyword
                    break
            selected_index[category] = idx
            if not chosen:
                continue
            result.append({
                "keyword": chosen,
                "category": category,
                "angle": f"{chosen}를 기구·제어·Cycle Time·안전·PoC·ROI 관점에서 설명",
                "reason": "Safe Mode Content Engine V2 category rotation refill",
                "estimated_search_volume": "medium",
            })
            existing_titles.append(chosen)
            added_this_pass = True
            logger.info("[TOPIC-ROTATION-V2] refill: %s -> %s", category, chosen)
            if len(result) >= target_count:
                return result
        if not added_this_pass:
            break
    return result


def guard_and_refill_topics(topics: list[dict], days: int = 60, threshold: float = 0.62,
                            target_count: int = 3) -> tuple[list[dict], list[dict]]:
    history = load_recent_titles(days=days)
    accepted, rejected = filter_recent_topics(topics, recent_titles=history, threshold=threshold)
    final_topics = refill_topics(accepted, history, target_count=target_count, threshold=threshold)
    logger.info("[TOPIC-GUARD-V2] final=%s / rejected=%s / pool=%s", len(final_topics), len(rejected), sum(map(len, PHASE3_TOPIC_POOL.values())))
    return final_topics, rejected
