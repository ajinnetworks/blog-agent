"""Deterministic technical content enricher for Ajin Networks blog posts.

Safe Mode Content Engine V2 expands short drafts into proposal-grade technical
articles with category-specific mechanism, controls, validation and RFQ guidance.
It never invents project-specific numeric results.
"""

import re

from agents.safe_content_engine_v2 import domain_profile

TARGET_MIN_CHARS = 1700
SEO_KEYWORD_LIMIT = 8


def _compact_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def _keyword(post: dict) -> str:
    return post.get("source_topic", {}).get("keyword") or post.get("title") or "산업자동화 설비"


def _category(post: dict) -> str:
    return str(post.get("category") or post.get("source_topic", {}).get("category") or "공장자동화")


def _technical_body(keyword: str, category: str) -> str:
    p = domain_profile(category)
    return f"""# {keyword}

{keyword}를 실제 생산라인에 적용할 때는 단순 장비 선정이나 단품 사양 비교만으로 결론을 내리기 어렵습니다. 자동화 설비는 제품 조건, 작업 순서, Cycle Time, 기구 구조, 제어 인터록, 검사, 안전, 유지보수와 상위 시스템이 하나의 시스템으로 맞물려야 합니다. 초기 검토 단계에서는 확인된 현장 데이터와 가정을 분리하고, 핵심 불확실성은 PoC 또는 사전 시험으로 제거해야 합니다.

## 1. 현행 공정과 병목 계측
자동화의 출발점은 장비가 아니라 현재 공정입니다. 제품이 어디에서 공급되고 어떤 방향으로 정렬되는지, 작업자 개입 구간과 대기시간, 정상·비정상 Cycle Time, 품종 변경시간, 불량 발생 위치를 시간축으로 기록해야 합니다. 평균값만으로 CAPA를 확정하지 않고 최대·최소값과 변동폭을 함께 확인해야 병목을 잘못 판단하는 위험을 줄일 수 있습니다.

## 2. {category} 기구·설비 구조 핵심 검토
{p['mechanism']}

기구 설계는 정상 제품뿐 아니라 위치 편차, 공차 누적, 자재 변형, 설비 정지 후 재기동과 유지보수 접근성을 포함해야 합니다. Robot이나 Servo가 포함되면 명목 Payload만 보지 않고 EOAT·Cable·배관을 포함한 실제 부하와 Moment, 관성, Reach를 계산해야 합니다. 제품 손상이나 낙하가 가능한 공정은 Fail-safe와 감지 구조를 동시에 설계하는 것이 바람직합니다.

## 3. 제어·통신 아키텍처
{p['control']}

Start, Ready, Busy, Complete, Alarm, Reset 같은 상태 신호는 장비 간 의미를 통일해야 하며, Timeout과 비정상 종료 시 어느 단계부터 복구할 수 있는지를 정의해야 합니다. 자동운전과 Manual Mode의 권한과 인터록을 구분하고, 통신 장애가 위험 동작이나 이중 처리로 이어지지 않도록 상태기계를 구성해야 합니다.

## 4. Cycle Time과 생산성 검증
목표 Cycle Time은 단일 Robot 또는 핵심 유닛의 이론값으로 확정하지 않습니다. 공급, 정렬, 클램핑, 촬영, 이송, 작업, 검사, 배출, 다음 제품 준비시간을 직렬·병렬 구간으로 나눠 계산해야 합니다. 정상 CT 외에 Changeover, Jam Recovery, 자재 보충, 불량 배출과 재시작 조건을 포함해야 실질적인 시간당 생산량과 OEE를 판단할 수 있습니다. 현장 실측 전 생산성 수치는 확정값으로 표현하지 않습니다.

## 5. 안전·인터록·고장복구
비상정지, Door Interlock, Light Curtain, Safety Scanner, Servo STO, 공압 잔압 배출 등은 위험성 평가를 기준으로 선정해야 합니다. 일반 PLC 인터록과 Safety 기능을 분리하고 Sensor 단선, 통신 끊김, 제품 미검출, Actuator 미도달 같은 단일 고장이 위험 동작으로 이어지지 않도록 설계합니다. 고장복구는 'Reset 후 전체 재시작'이 아니라 공정 상태에 따라 안전한 재진입 지점을 정의하는 것이 유지보수에 유리합니다.

## 6. PoC·FAT에서 확인할 핵심 항목
{p['validation']}

PoC는 전체 설비를 축소 복제하는 것이 아니라 기술적으로 가장 불확실한 핵심 유닛을 먼저 검증하는 시험이어야 합니다. FAT에서는 Cycle Time, 반복정밀도, 불량 검출, Alarm Recovery, Safety, 장시간 연속운전과 데이터 기록을 체크리스트화하고 고객과 승인 기준을 사전에 합의해야 합니다.

## 7. ROI와 투자 판단
ROI는 단순 인원 절감만으로 계산하지 않습니다. 생산량 증가, 불량·재작업 감소, Down Time, 유지보수, 소모품, 교육, Changeover, 향후 품종 확장성을 함께 반영해야 합니다. 자동화 이후에도 제품 투입·자재 보충·검사 승인에 작업자가 필요하다면 순수 절감 인원과 재배치 인원을 구분해야 합니다. 투자회수기간은 실제 생산계획과 가동시간이 확인된 이후 산정하는 것이 안전합니다.

## 8. RFQ·현장조사 전 확보할 입력정보
{category} 기술검토에서는 최소한 다음 입력을 확보하는 것이 좋습니다: **{p['rfq']}**.

확인되지 않은 항목은 추정값과 구분해 제안서·설계사양서에 기록해야 변경관리와 추가비용 분쟁을 줄일 수 있습니다. 특히 제품 Sample, 도면, Layout, 현재 CT, 목표 CAPA, 기존 제어 자산, 안전 요구사항은 Concept과 견적 정확도에 직접 영향을 줍니다.

아진네트웍스는 {category} 프로젝트를 개별 장비가 아니라 기구·제어·검사·안전·생산성이 결합된 통합 시스템으로 검토하고, 현장 데이터와 PoC 결과를 기준으로 사양과 투자효과를 단계적으로 검증하는 접근을 권장합니다.
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
    profile = domain_profile(category)
    post["category"] = category
    post["content"] = _technical_body(keyword, category)
    post["generation_provider"] = "safe-mode-content-engine-v2"
    post["content_enriched"] = True
    post["content_template"] = category
    post["seo_keywords"] = list(dict.fromkeys([
        keyword, category, *profile["keywords"], "산업자동화", "아진네트웍스"
    ]))[:SEO_KEYWORD_LIMIT]
    meta = f"{keyword}의 기구·제어·Cycle Time·안전·PoC·RFQ 검토 기준을 {category} 엔지니어링 관점에서 정리합니다."
    post["meta_description"] = meta[:160]
    post["word_count"] = _compact_len(post["content"])
    return post


def enrich_posts(posts: list[dict]) -> list[dict]:
    return [enrich_post(post) for post in posts]
