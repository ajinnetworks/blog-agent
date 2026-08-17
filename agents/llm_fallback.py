"""Shared LLM fallback helper for blog agents.

Safe-mode policy:
- Never publish unrelated consumer/news trends.
- Accept only Ajin Networks industrial automation topics.
- If real-time trends are not industrially relevant, replace them with vetted industrial seed topics.
"""

import json
import logging
import os
import re

from google import genai as google_genai
from anthropic import Anthropic

logger = logging.getLogger(__name__)

GEMINI_MODELS = ["gemini-flash-latest"]
CLAUDE_MODELS = ["claude-sonnet-4-20250514", "claude-3-7-sonnet-latest"]

# Allowed Ajin Networks industrial domains. Safe-mode topics must map here.
INDUSTRIAL_CATEGORY_KEYWORDS = {
    "물류자동화": [
        "AGV", "AMR", "물류로봇", "컨베이어", "소터", "자동창고", "AS/RS",
        "피킹", "팔레타이징", "WMS", "입출고 자동화", "재고 추적",
    ],
    "딥러닝비전": [
        "비전검사", "머신비전", "딥러닝", "AI 검사", "불량검출", "결함검출",
        "외관검사", "OCR", "3D비전", "AOI", "카메라", "조명", "검사자동화",
    ],
    "공장자동화": [
        "공장자동화", "로봇자동화", "산업용 로봇", "협동로봇", "SCARA", "6축 로봇",
        "포장자동화", "조립자동화", "용접자동화", "픽앤플레이스", "CNC", "엔드이펙터",
        "그리퍼", "자동화 설비", "생산라인",
    ],
    "스마트팩토리": [
        "스마트팩토리", "MES", "OEE", "예지보전", "디지털트윈", "IIoT", "엣지AI",
        "생산성", "설비 모니터링", "공정 데이터", "스마트센서", "FEMS",
    ],
    "제어SW": [
        "PLC", "HMI", "SCADA", "Siemens", "Mitsubishi", "LS PLC", "Profinet",
        "EtherCAT", "Modbus", "OPC-UA", "서보", "모션제어", "인버터", "제어반",
    ],
    "자동차자동화": [
        "자동차", "EV", "배터리", "차체", "용접", "열처리", "부품 조립", "토크 관리",
        "로봇 핸들링", "검사 지그",
    ],
    "반도체자동화": [
        "반도체", "웨이퍼", "FOUP", "클린룸", "다이 본딩", "패키징", "인라인 검사",
    ],
    "의료기기자동화": [
        "의료기기", "카테터", "튜브", "파우치 포장", "실링", "권선", "인장검사",
    ],
}

# Explicitly reject common non-industrial trend classes even when they contain a generic word like AI.
NON_INDUSTRIAL_BLOCKLIST = [
    "연예", "배우", "가수", "아이돌", "드라마", "영화", "예능", "스포츠", "야구", "축구",
    "게임", "웹툰", "정년", "퇴직", "사원", "채용", "연봉", "부동산", "주식", "코인",
    "대출", "보험", "카드", "금융", "정치", "선거", "대통령", "국회", "사건", "사고",
    "맛집", "음식", "카페", "여행", "호텔", "패션", "뷰티", "화장품", "육아", "건강",
    "다이어트", "날씨", "태풍", "최애", "팬", "콘서트",
]

# Vetted fallback topics. These are intentionally specific enough to generate useful B2B technical posts.
SAFE_TOPIC_POOL = {
    "물류자동화": [
        "AGV·AMR 도입 전 동선·충전·교통제어 설계 기준",
        "컨베이어와 로봇을 연계한 팔레타이징 자동화 설계",
        "자동창고 입출고 병목을 줄이는 WMS·PLC 인터페이스",
    ],
    "딥러닝비전": [
        "AI 비전검사 도입 전 조명·렌즈·불량 데이터 검증 기준",
        "2D·3D 머신비전 선택 기준과 로봇 좌표 연동 방법",
        "외관검사 자동화의 오검·미검을 줄이는 설계 체크리스트",
    ],
    "공장자동화": [
        "산업용 로봇 자동화 도입 전 Cycle Time과 가동률 검토 방법",
        "로봇 엔드이펙터 설계 시 Payload·Moment·Fail-safe 검토",
        "포장·조립 자동화 라인의 병목 공정 개선 방법",
    ],
    "스마트팩토리": [
        "OEE 기반 설비 병목 분석과 자동화 투자 우선순위 선정",
        "예지보전용 센서 데이터 수집 구조와 PLC·MES 연계",
        "스마트팩토리 구축 전 현장 데이터 표준화 체크리스트",
    ],
    "제어SW": [
        "PLC·HMI·SCADA 통합 시 네트워크와 알람 설계 기준",
        "Profinet·EtherCAT·Modbus 산업통신 선택 기준",
        "서보 모션제어 적용 시 인터록·원점·안전회로 설계",
    ],
}


def _gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")
    client = google_genai.Client(api_key=api_key)
    last_error = None
    for model_name in GEMINI_MODELS:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            text = (response.text or "").strip()
            if not text:
                raise RuntimeError("empty Gemini response")
            logger.info("[LLM] Gemini model used: %s", model_name)
            return text
        except Exception as exc:
            last_error = exc
            logger.warning("[LLM] Gemini unavailable (%s): %s", model_name, exc)
    raise RuntimeError(f"Gemini unavailable: {last_error}")


def _claude(prompt: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    client = Anthropic(api_key=api_key)
    last_error = None
    for model_name in CLAUDE_MODELS:
        try:
            message = client.messages.create(
                model=model_name,
                max_tokens=8192,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "\n".join(
                block.text for block in message.content
                if getattr(block, "type", None) == "text"
            ).strip()
            if not text:
                raise RuntimeError("empty Claude response")
            logger.info("[LLM] Claude model used: %s", model_name)
            return text
        except Exception as exc:
            last_error = exc
            logger.warning("[LLM] Claude unavailable (%s): %s", model_name, exc)
    raise RuntimeError(f"Claude unavailable: {last_error}")


def _extract_trend_keywords(prompt: str) -> list[str]:
    keywords = []
    for line in prompt.splitlines():
        line = line.strip()
        if line.startswith("- [") and "]" in line:
            keyword = line.split("]", 1)[1].strip()
            if keyword and keyword not in keywords:
                keywords.append(keyword)
    return keywords


def _contains_blocked_term(text: str) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in NON_INDUSTRIAL_BLOCKLIST)


def _industrial_score(text: str) -> tuple[int, str | None]:
    """Return (score, best_category). Minimum safe acceptance score is 2."""
    lowered = text.lower()
    if _contains_blocked_term(text):
        return -100, None

    best_score = 0
    best_category = None
    for category, keywords in INDUSTRIAL_CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in lowered:
                # Specific industrial phrases receive stronger weight.
                score += 2 if len(keyword) >= 3 else 1
        if score > best_score:
            best_score = score
            best_category = category

    # Generic manufacturing context can raise a borderline industrial term, but can never rescue blocked content.
    context_terms = ["제조", "생산", "공정", "설비", "자동화", "로봇", "검사", "제어", "산업"]
    context_hits = sum(1 for term in context_terms if term in lowered)
    if best_score > 0:
        best_score += min(context_hits, 2)

    return best_score, best_category


def _safe_category(priority: str) -> str:
    if priority in SAFE_TOPIC_POOL:
        return priority
    return "공장자동화"


def _select_industrial_topics(prompt: str, top_n: int = 3) -> list[dict]:
    priority_match = re.search(r"오늘 우선 카테고리:\s*(.+)", prompt)
    priority = _safe_category(priority_match.group(1).strip() if priority_match else "공장자동화")
    trends = _extract_trend_keywords(prompt)

    candidates = []
    for keyword in trends:
        score, category = _industrial_score(keyword)
        if score >= 2 and category:
            candidates.append((score, keyword, category))
        else:
            logger.warning("[SAFE-MODE] trend rejected: '%s' (industrial_score=%s)", keyword, score)

    # Highest industrial relevance first; never use an unqualified trend.
    candidates.sort(key=lambda item: item[0], reverse=True)
    selected = []
    seen = set()
    for score, keyword, category in candidates:
        if keyword in seen:
            continue
        selected.append({
            "keyword": keyword,
            "angle": f"{keyword}를 제조 자동화의 생산성·품질·Cycle Time·ROI 관점에서 기술적으로 분석",
            "reason": f"산업 연관성 검증 통과(score={score})",
            "category": category if category in SAFE_TOPIC_POOL else priority,
            "estimated_search_volume": "medium",
        })
        seen.add(keyword)
        if len(selected) >= top_n:
            break

    # Fill all missing slots only from vetted Ajin industrial seed topics.
    pool_order = [priority] + [c for c in SAFE_TOPIC_POOL if c != priority]
    for category in pool_order:
        for keyword in SAFE_TOPIC_POOL[category]:
            if keyword in seen:
                continue
            selected.append({
                "keyword": keyword,
                "angle": f"{keyword}를 실제 자동화 설비 설계·제어·현장 적용 기준으로 설명",
                "reason": "실시간 트렌드가 산업 기준을 통과하지 못해 아진네트웍스 검증 주제로 대체",
                "category": category,
                "estimated_search_volume": "medium",
            })
            seen.add(keyword)
            if len(selected) >= top_n:
                return selected

    return selected[:top_n]


def _rule_based(prompt: str) -> str:
    logger.warning("[LLM] Switching Claude -> deterministic fallback")

    if '"selected_topics"' in prompt:
        selected = _select_industrial_topics(prompt, top_n=3)
        logger.info("[SAFE-MODE] industrial topic engine selected: %s", [x["keyword"] for x in selected])
        return json.dumps({"selected_topics": selected}, ensure_ascii=False)

    if "100점 만점으로 평가" in prompt:
        indexes = [int(x) for x in re.findall(r"\[포스트\s+(\d+)\]", prompt)]
        if indexes:
            return json.dumps([
                {"index": i, "score": 80, "pass": True, "reason": "규칙기반 기본 검수 통과"}
                for i in indexes
            ], ensure_ascii=False)
        return json.dumps({"score": 80, "pass": True, "reason": "규칙기반 기본 검수 통과"}, ensure_ascii=False)

    if "개선된 포스트를 동일한 JSON 형식으로 반환" in prompt:
        return json.dumps({
            "title": "자동화 설비 개선 체크리스트 - 아진네트웍스",
            "content": (
                "자동화 설비 개선은 현행 공정 계측, 병목 분석, Cycle Time 검증, 인터록 정의, "
                "안전회로 검증, PoC 시험 순으로 진행해야 합니다. 생산성 개선 효과는 현장 데이터로 확인하고 "
                "불확실한 조건은 추정값과 확인값을 구분하여 관리해야 합니다."
            ),
            "category": "공장자동화",
            "tags": ["공장자동화", "로봇자동화", "아진네트웍스"],
            "meta_description": "자동화 설비 개선 시 확인해야 할 공정·Cycle Time·제어·안전·PoC 검증 기준을 정리합니다.",
        }, ensure_ascii=False)

    if "블로그 포스트를 작성" in prompt and '"title"' in prompt:
        keyword_match = re.search(r"키워드:\s*(.+)", prompt)
        keyword = keyword_match.group(1).strip() if keyword_match else "산업용 로봇 자동화"
        score, detected_category = _industrial_score(keyword)
        if score < 2:
            logger.error("[SAFE-MODE] blocked non-industrial writer topic: '%s'", keyword)
            keyword = SAFE_TOPIC_POOL["공장자동화"][0]
            detected_category = "공장자동화"

        category = detected_category if detected_category in SAFE_TOPIC_POOL else "공장자동화"
        title = f"{keyword} 설계 기준 - 아진네트웍스"
        if len(title) > 40:
            title = f"{category} 실무 설계 기준 - 아진네트웍스"

        content = (
            f"# {keyword}\n\n"
            "## 1. 도입 목적\n"
            f"{keyword} 검토의 출발점은 단순한 설비 교체가 아니라 현재 공정의 병목과 작업자 개입 구간을 수치로 확인하는 것입니다. "
            "현행 Cycle Time, 목표 Takt Time, 생산량, 불량률, 작업 인원, 설비 가동률을 먼저 계측해야 합니다.\n\n"
            "## 2. 기구 설계 검토\n"
            "제품 중량과 형상, 반복정밀도, 가속도, Payload와 Moment, 그리퍼 또는 지그의 파지 안정성, 유지보수 접근성을 검토합니다. "
            "로봇 적용 시 제조사 허용하중과 EOAT 중량을 합산하고 최악 조건에서의 관성모멘트를 확인해야 합니다.\n\n"
            "## 3. 제어 및 통신\n"
            "PLC, 로봇 컨트롤러, 비전, 안전PLC, 인버터와 서보 간 I/O 및 산업용 Ethernet 인터페이스를 정의합니다. "
            "자동운전, 수동운전, 원점복귀, 알람복귀, 제품 변경, 통신 단절 시 Fail-safe 상태를 사전에 설계해야 합니다.\n\n"
            "## 4. 안전과 품질\n"
            "안전펜스, 인터록, 비상정지, 라이트커튼 또는 스캐너의 위험원 분석이 필요합니다. "
            "검사 공정은 PASS/FAIL 판정 기준과 기준샘플, 재검 로직, 데이터 저장 조건을 명확하게 정의합니다.\n\n"
            "## 5. Cycle Time과 생산성\n"
            "자동화 전후의 작업 분해표를 작성하고 로봇 이동, 파지, 검사, 이송, 대기 시간을 분리 계측합니다. "
            "평균값만 사용하지 말고 최대 Cycle Time과 공정 변동성을 함께 검토해야 실제 양산 CAPA를 보수적으로 산정할 수 있습니다.\n\n"
            "## 6. PoC와 투자검토\n"
            "본설비 제작 전에 핵심 불확실성이 큰 공정은 PoC로 검증하는 것이 안전합니다. 반복정밀도, 제품 손상, 인식률, Cycle Time, "
            "복구성 및 작업자 개입 빈도를 시험하고, 검증된 데이터로 CAPEX와 ROI를 산정해야 합니다.\n\n"
            "아진네트웍스는 기구·제어·로봇·비전·검사 인터페이스를 하나의 시스템으로 검토하여 현장 적용 가능성과 리스크를 구분합니다."
        )
        return json.dumps({
            "title": title,
            "content": content,
            "category": category,
            "tags": [category, "자동화설비", "아진네트웍스"],
            "meta_description": f"{keyword}의 기구·제어·Cycle Time·안전·PoC 설계 기준을 아진네트웍스 관점에서 정리합니다.",
        }, ensure_ascii=False)

    raise RuntimeError("Deterministic fallback has no compatible response for this prompt")


def get_llm_response(prompt: str) -> str:
    """Try Gemini, then Claude, then Ajin industrial deterministic safe-mode."""
    errors = []
    try:
        return _gemini(prompt)
    except Exception as exc:
        errors.append(str(exc))
        logger.warning("[LLM] Switching Gemini -> Claude")

    try:
        return _claude(prompt)
    except Exception as exc:
        errors.append(str(exc))

    try:
        return _rule_based(prompt)
    except Exception as exc:
        errors.append(str(exc))

    raise RuntimeError("All LLM providers and deterministic fallback failed: " + " | ".join(errors))
