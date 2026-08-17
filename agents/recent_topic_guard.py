"""Phase 3 topic guard and category rotation for Ajin Networks blog automation.

Responsibilities:
- Read recently published Jekyll titles from BLOG_REPO.
- Reject proposed topics that are too similar to recent content or same-run topics.
- Refill rejected slots from a larger, category-balanced industrial topic pool.
- Keep deterministic behavior when external LLM providers are unavailable.
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

CATEGORY_ORDER = [
    "물류자동화", "딥러닝비전", "공장자동화", "제어SW", "스마트팩토리",
    "포장자동화", "자동차자동화", "의료기기자동화", "반도체자동화",
]

PHASE3_TOPIC_POOL = {
    "물류자동화": [
        "AMR Fleet 운영 시 교차로 정체와 Deadlock을 줄이는 교통제어 기준",
        "자동창고 AS/RS 처리량 산정과 WMS·PLC 인터페이스 설계",
        "컨베이어 Merge·Diverter 병목을 줄이는 센서와 제어 로직",
        "팔레트 이송라인 Buffer 용량과 Cycle Time 산정 방법",
        "AMR 충전 스테이션 수량과 Opportunity Charging 운영 기준",
    ],
    "딥러닝비전": [
        "AI 비전검사 조명 조건을 고정하는 DOE와 Golden Sample 운영 방법",
        "2D 비전과 3D 비전 선택 시 정밀도·Cycle Time 비교 기준",
        "라인스캔 카메라 검사에서 Encoder 동기와 조명 균일도 설계",
        "비전검사 오검·미검을 줄이는 불량 데이터셋 관리 방법",
        "로봇 비전 Pick 보정 시 Hand-Eye Calibration 검증 기준",
    ],
    "공장자동화": [
        "산업용 로봇 EOAT 설계 시 Payload·Moment·관성 검토 방법",
        "로봇 셀 Cycle Time을 줄이는 동작경로와 I/O 병렬처리 방법",
        "자동화 설비 FAT 전 인터록과 Recovery 시나리오 검증 기준",
        "협동로봇 적용 전 안전거리와 작업자 간섭 검토 포인트",
        "조립자동화에서 Poka-Yoke와 Traceability를 구현하는 방법",
    ],
    "제어SW": [
        "PLC·HMI 알람 표준화와 설비 정지 원인 추적 설계 방법",
        "OPC-UA와 MES 연계 시 Tag 구조와 통신 장애 복구 기준",
        "EtherCAT 서보축 원점복귀와 안전정지 Sequence 설계",
        "Profinet 네트워크 구성 시 Device Name·IP·진단 표준",
        "PLC 프로그램 모듈화로 설비 개조 시간을 줄이는 구조",
    ],
    "스마트팩토리": [
        "OEE 손실 6대 항목으로 자동화 투자 우선순위를 정하는 방법",
        "예지보전 센서 선정 시 진동·전류·온도 데이터 수집 기준",
        "MES 구축 전 설비 데이터 표준과 생산실적 정의 방법",
        "디지털트윈 PoC에서 실제 Cycle Time과 모델 오차 검증 방법",
        "스마트팩토리 구축 전 설비별 데이터 Ownership 정의 기준",
    ],
    "포장자동화": [
        "파우치 포장자동화에서 개구·삽입·실링 안정화 설계 기준",
        "카토닝 자동화에서 제품 정렬과 박스 공급 병목 개선 방법",
        "실링 공정 온도·압력·시간 Recipe 관리와 품질 Traceability",
        "포장라인 Vision 검사와 Reject Station 인터록 설계",
        "다품종 포장설비 Changeover 시간을 줄이는 치구 표준화",
    ],
    "자동차자동화": [
        "자동차 열처리 로봇 핸들링에서 위치 반복정밀도 검증 방법",
        "중량 자동차부품 로봇 Gripper 설계 시 안전율과 Fail-safe 기준",
        "차종 변경 대응 자동화 지그의 Quick Change 설계 기준",
        "자동차 조립 토크 Traceability와 PLC·Nutrunner 연계 방법",
        "자동차 부품 Palletizing에서 간지 취급과 적재 안정화 방법",
    ],
    "의료기기자동화": [
        "카테터 권선 자동화에서 장력과 최소 굽힘반경 관리 기준",
        "의료기기 파우치 삽입 자동화에서 제품 손상 방지 설계",
        "튜브 인장검사 지그의 Load Cell 선정과 반복성 검증 방법",
        "의료 포장 실링 공정의 Recipe와 Lot Traceability 설계",
        "의료기기 자동화 FAT에서 검사 데이터 무결성 검증 항목",
    ],
    "반도체자동화": [
        "반도체 클린룸 로봇 적용 시 Particle과 Cable Management 기준",
        "웨이퍼 핸들링 자동화에서 진공 Gripper와 파손 감지 설계",
        "반도체 인라인 비전검사 Cycle Time과 검사해상도 최적화",
        "FOUP 이송 자동화에서 Interlock과 Carrier ID 추적 방법",
        "반도체 설비 SECS/GEM 연계 전 PLC 데이터 구조 검토 항목",
    ],
}


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
    """Fill rejected slots round-robin across categories with non-duplicate vetted topics."""
    result = list(accepted)
    if len(result) >= target_count:
        return result[:target_count]

    start = _rotation_start(now)
    categories = CATEGORY_ORDER[start:] + CATEGORY_ORDER[:start]
    existing_titles = list(recent_titles) + [x.get("keyword", "") for x in result]
    selected_index = {category: 0 for category in categories}

    # Each pass selects at most one topic per category. This prevents a single
    # category from consuming every refill slot while preserving deterministic order.
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
                "reason": "Phase 3 category rotation refill",
                "estimated_search_volume": "medium",
            })
            existing_titles.append(chosen)
            added_this_pass = True
            logger.info("[TOPIC-ROTATION] refill: %s -> %s", category, chosen)
            if len(result) >= target_count:
                return result
        if not added_this_pass:
            break
    return result


def guard_and_refill_topics(topics: list[dict], days: int = 60, threshold: float = 0.62,
                            target_count: int = 3) -> tuple[list[dict], list[dict]]:
    """Production entrypoint: history load -> duplicate filter -> balanced refill."""
    history = load_recent_titles(days=days)
    accepted, rejected = filter_recent_topics(topics, recent_titles=history, threshold=threshold)
    final_topics = refill_topics(accepted, history, target_count=target_count, threshold=threshold)
    logger.info("[TOPIC-GUARD] final=%s / rejected=%s", len(final_topics), len(rejected))
    return final_topics, rejected
