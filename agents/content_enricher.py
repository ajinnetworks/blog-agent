"""Deterministic technical content enricher for Ajin Networks blog posts.

Expands short AI/fallback drafts into a consistent proposal-grade technical article
before reviewer/final quality gates. It does not invent project-specific numeric results.
"""

import re

TARGET_MIN_CHARS = 1700


def _compact_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def _keyword(post: dict) -> str:
    return (
        post.get("source_topic", {}).get("keyword")
        or post.get("title")
        or "산업자동화 설비"
    )


def _category(post: dict) -> str:
    return str(post.get("category") or "공장자동화")


def _technical_body(keyword: str, category: str) -> str:
    return f"""# {keyword}

{keyword}를 실제 생산라인에 적용할 때는 단순 장비 선정이나 단품 사양 비교만으로 결론을 내리기 어렵습니다. 자동화 설비는 제품 조건, 작업 순서, Cycle Time, 기구 구조, 로봇 동작, PLC 인터록, 비전검사, 안전회로, 유지보수성과 상위 시스템 연동이 하나의 시스템으로 맞물려야 합니다. 따라서 초기 검토 단계에서는 확인된 현장 데이터와 아직 확인되지 않은 가정을 구분하고, PoC 또는 사전 시험을 통해 핵심 리스크를 먼저 제거하는 방식이 필요합니다.

## 1. 적용 공정과 현행 작업을 먼저 계측해야 하는 이유
자동화의 출발점은 장비가 아니라 현재 공정입니다. 작업자가 제품을 어디에서 집고, 어떤 방향으로 정렬하며, 어느 위치에서 대기하고, 불량이나 설비 정지 시 어떤 복구 작업을 수행하는지 실제 동작을 시간축으로 기록해야 합니다. 평균 Cycle Time만 보는 것보다 최대·최소값, 대기시간, 작업자 개입 횟수, 품종 변경시간을 함께 측정해야 병목을 정확히 찾을 수 있습니다. 특히 물류자동화나 로봇 이송은 앞뒤 공정의 공급 변동이 크면 로봇 자체가 빨라도 전체 생산성은 개선되지 않을 수 있습니다.

## 2. 기구 구조와 로봇 선정 기준
기구 검토에서는 제품의 중량과 외형뿐 아니라 무게중심, 파지 가능한 면, 변형 허용량, 표면 손상 가능성, 공차 누적을 함께 확인해야 합니다. 산업용 로봇을 적용할 경우 Payload만으로 선정하지 않고 Reach, 손목 허용 Moment, 관성, EOAT 중량, 케이블 및 공압 배관까지 포함한 실제 부하를 계산해야 합니다. 그리퍼는 정상 제품뿐 아니라 위치 편차나 비정상 제품이 들어왔을 때도 낙하를 방지할 수 있도록 Fail-safe 구조와 감지 센서를 포함하는 것이 바람직합니다.

## 3. PLC·Robot·Vision 통합제어 구조
제어 시스템은 PLC를 공정 Master로 두고 로봇, 비전, 서보, 인버터, 안전기기와 명확한 Handshake를 구성하는 방식이 유지보수에 유리합니다. Start, Ready, Busy, Complete, Alarm, Reset과 같은 상태 신호를 정의하고 비정상 종료 시 어느 단계에서 재시작할 수 있는지 복구 시퀀스를 설계해야 합니다. 비전검사가 포함된다면 카메라 판정 결과뿐 아니라 촬영 트리거, 제품 ID, 좌표값, 판정 이력과 로봇 좌표계 변환 조건까지 관리해야 추후 원인 분석이 가능합니다.

## 4. Cycle Time과 생산성 검증
목표 Cycle Time은 로봇 단독 시뮬레이션 값으로 확정하지 않는 것이 중요합니다. 제품 공급, 클램핑, 비전 촬영, 로봇 이동, 작업 수행, 검사, 배출, 다음 제품 준비시간을 모두 합산하고 병렬 처리 가능한 구간과 직렬 처리 구간을 분리해야 합니다. 또한 정상 운전 Cycle Time 외에 품종 변경, 설비 재기동, 불량 배출, 작업자 보충시간까지 고려해야 실질적인 시간당 생산량과 OEE를 추정할 수 있습니다. 생산성 수치는 현장 실측값이 확보되기 전에는 확정값으로 표현하지 않는 것이 안전합니다.

## 5. 안전회로와 인터록
자동화 설비는 생산성보다 안전이 우선입니다. 비상정지, 도어 인터록, 라이트커튼, 안전스캐너, 로봇 안전영역, 공압 잔압 배출, 서보 STO 등 적용 가능한 안전기능을 위험성 평가 결과에 따라 선정해야 합니다. PLC 일반 프로그램의 인터록과 안전 PLC 또는 안전 릴레이의 기능을 구분하고, 센서 단선이나 통신 장애 같은 단일 고장이 위험 동작으로 이어지지 않도록 설계해야 합니다.

## 6. PoC와 FAT에서 확인할 항목
PoC에서는 기술적으로 가장 불확실한 항목을 먼저 시험해야 합니다. 예를 들어 비정형 제품 파지, 투명·반사체 비전검사, 긴 연성 제품 이송, 고속 팔레타이징처럼 난도가 높은 공정은 전체 설비 제작 전에 핵심 유닛만 구성해 반복 시험하는 것이 투자 리스크를 줄입니다. FAT에서는 Cycle Time, 반복정밀도, 불량 검출, 알람 복구, 안전기능, 장시간 연속운전 조건을 체크리스트화하고 승인 기준을 사전에 합의해야 합니다.

## 7. ROI와 투자 판단
ROI는 단순 인원 절감만으로 계산하지 않고 생산량 증가, 불량률 감소, 재작업 감소, 다운타임, 유지보수 비용, 소모품, 교육비와 향후 품종 확장 가능성을 함께 반영해야 합니다. 자동화 이후에도 제품 투입이나 자재 보충에 작업자가 계속 필요하다면 순수 절감 인원과 재배치 인원을 구분하는 것이 현실적입니다. 투자회수기간은 실제 생산계획과 가동시간이 확인된 이후 산정하는 것이 바람직합니다.

## 8. 현장 적용 전 최종 확인사항
{category} 프로젝트에서는 제품 도면, 공정 레이아웃, 목표 생산량, 현재 Cycle Time, 품종 수, 불량 유형, 사용 중인 PLC·Robot·Vision 브랜드, 상위 시스템 인터페이스, 안전 요구사항을 우선 확보하는 것이 좋습니다. 확인되지 않은 조건은 추정값과 명확히 분리해 제안서와 설계 사양서에 기록해야 변경관리와 추가비용 분쟁을 줄일 수 있습니다.

아진네트웍스는 로봇·PLC·비전·기구를 개별 장비가 아닌 통합 자동화 시스템으로 검토하고, 현장 데이터와 PoC 결과를 기준으로 구조·제어·생산성·안전·ROI를 단계적으로 검증하는 접근을 권장합니다.
"""


def enrich_post(post: dict) -> dict:
    if post.get("error"):
        return post
    content = str(post.get("content") or "")
    if _compact_len(content) >= TARGET_MIN_CHARS:
        post.setdefault("generation_provider", "llm")
        return post

    keyword = _keyword(post)
    category = _category(post)
    post["content"] = _technical_body(keyword, category)
    post["generation_provider"] = "deterministic-enriched"
    post["content_enriched"] = True
    post["seo_keywords"] = list(dict.fromkeys([
        keyword, category, "산업자동화", "로봇자동화", "PLC", "비전검사", "스마트팩토리", "아진네트웍스"
    ]))[:8]
    meta = f"{keyword} 적용을 위한 공정분석, 기구·로봇 선정, PLC·비전 통합제어, Cycle Time, 안전, PoC, ROI 검증 기준을 아진네트웍스 기술 관점에서 정리합니다."
    post["meta_description"] = meta[:160]
    post["word_count"] = _compact_len(post["content"])
    return post


def enrich_posts(posts: list[dict]) -> list[dict]:
    return [enrich_post(post) for post in posts]
