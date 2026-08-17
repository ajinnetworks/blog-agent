"""Regression tests for Recent Topic Guard V1."""
from agents.recent_topic_guard import filter_recent_topics, topic_similarity

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
assert topic_similarity("자동창고 WMS PLC 인터페이스", recent[2]) >= 0.62
assert topic_similarity("AI 비전검사 조명 렌즈 선정", recent[0]) < 0.62

# Same-run duplicates must also be suppressed.
batch = [
    {"keyword": "산업용 로봇 EOAT 그리퍼 선정 기준"},
    {"keyword": "산업용 로봇 EOAT 그리퍼 선정 가이드"},
]
accepted2, rejected2 = filter_recent_topics(batch, recent_titles=[], threshold=0.62)
assert len(accepted2) == 1 and len(rejected2) == 1

print("RECENT TOPIC GUARD V1 TESTS: PASS")
print("Recent-title duplicate rejection: PASS")
print("Same-run semantic duplicate rejection: PASS")
