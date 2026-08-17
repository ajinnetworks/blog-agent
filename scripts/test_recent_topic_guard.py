"""Regression tests for Phase 3 duplicate guard and category rotation."""
from datetime import datetime
from zoneinfo import ZoneInfo

from agents.recent_topic_guard import (
    filter_recent_topics,
    topic_similarity,
    refill_topics,
)

KST = ZoneInfo("Asia/Seoul")
recent = [
    "AGV·AMR 도입 전 동선·충전·교통제어 설계 기준 | 아진네트웍스",
    "컨베이어와 로봇을 연계한 팔레타이징 자동화 설계 도입 전 | 아진네트웍스",
    "자동창고 입출고 병목을 줄이는 WMS 도입 전 | 아진네트웍스",
]

proposed = [
    {"keyword": "AGV AMR 동선 및 충전 교통제어 설계"},
    {"keyword": "2D·3D 머신비전 검사 선정 기준과 조명 설계"},
    {"keyword": "PLC SCADA 설비 데이터 수집과 알람 표준화"},
]

accepted, rejected = filter_recent_topics(proposed, recent_titles=recent, threshold=0.62)
assert len(rejected) == 1, rejected
assert "AGV" in rejected[0]["topic"]["keyword"], rejected
assert len(accepted) == 2, accepted
# Near-duplicate wording must remain above the production threshold.
assert topic_similarity("자동창고 입출고 병목을 줄이는 WMS 도입", recent[2]) >= 0.62
# Unrelated vision content must stay below the threshold.
assert topic_similarity("AI 비전검사 조명 렌즈 선정", recent[0]) < 0.62

batch = [
    {"keyword": "산업용 로봇 EOAT 그리퍼 선정 기준"},
    {"keyword": "산업용 로봇 EOAT 그리퍼 선정 가이드"},
]
accepted2, rejected2 = filter_recent_topics(batch, recent_titles=[], threshold=0.62)
assert len(accepted2) == 1 and len(rejected2) == 1

# If all original Safe Mode topics were recently published, rotation must refill to 3 new topics.
all_old = recent + [
    "AI 비전검사 도입 전 조명·렌즈·불량 데이터 검증 기준 | 아진네트웍스",
    "산업용 로봇 자동화 도입 전 Cycle Time과 가동률 검토 방법 | 아진네트웍스",
]
refilled = refill_topics([], all_old, target_count=3, threshold=0.62,
                        now=datetime(2026, 8, 18, 6, 30, tzinfo=KST))
assert len(refilled) == 3, refilled
assert len({x["category"] for x in refilled}) >= 2, refilled
for topic in refilled:
    assert max((topic_similarity(topic["keyword"], old) for old in all_old), default=0) < 0.62

print("PHASE 3 TOPIC GUARD & ROTATION TESTS: PASS")
print("Recent-title duplicate rejection: PASS")
print("Same-run semantic duplicate rejection: PASS")
print("Category-balanced refill after duplicate rejection: PASS")
