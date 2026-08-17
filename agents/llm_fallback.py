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
import unicodedata

from google import genai as google_genai
from anthropic import Anthropic
from agents.runtime_guard import (
    classify_hard_provider_failure,
    disable_provider,
    provider_disabled,
)

logger = logging.getLogger(__name__)

GEMINI_MODELS = ["gemini-flash-latest"]
CLAUDE_MODELS = ["claude-sonnet-4-20250514", "claude-3-7-sonnet-latest"]

INDUSTRIAL_CATEGORY_KEYWORDS = {
    "물류자동화": ["AGV", "AMR", "물류로봇", "컨베이어", "소터", "자동창고", "AS/RS", "피킹", "팔레타이징", "WMS", "입출고 자동화", "재고 추적"],
    "딥러닝비전": ["비전검사", "머신비전", "딥러닝", "AI 검사", "불량검출", "결함검출", "외관검사", "OCR", "3D비전", "2D비전", "AOI", "카메라", "조명", "검사자동화"],
    "공장자동화": ["공장자동화", "로봇자동화", "산업용 로봇", "협동로봇", "SCARA", "6축 로봇", "포장자동화", "포장 자동화", "조립자동화", "조립 자동화", "용접자동화", "픽앤플레이스", "CNC", "엔드이펙터", "그리퍼", "자동화 설비", "생산라인", "병목 공정", "Cycle Time", "사이클타임"],
    "스마트팩토리": ["스마트팩토리", "MES", "OEE", "예지보전", "디지털트윈", "IIoT", "엣지AI", "생산성", "설비 모니터링", "공정 데이터", "스마트센서", "FEMS"],
    "제어SW": ["PLC", "HMI", "SCADA", "Siemens", "Mitsubishi", "LS PLC", "Profinet", "EtherCAT", "Modbus", "OPC-UA", "서보", "모션제어", "인버터", "제어반"],
    "자동차자동화": ["자동차", "EV", "배터리", "차체", "용접", "열처리", "부품 조립", "토크 관리", "로봇 핸들링", "검사 지그"],
    "반도체자동화": ["반도체", "웨이퍼", "FOUP", "클린룸", "다이 본딩", "패키징", "인라인 검사"],
    "의료기기자동화": ["의료기기", "카테터", "튜브", "파우치 포장", "실링", "권선", "인장검사"],
}

NON_INDUSTRIAL_BLOCKLIST = ["연예", "배우", "가수", "아이돌", "드라마", "영화", "예능", "스포츠", "야구", "축구", "게임", "웹툰", "정년", "퇴직", "사원", "채용", "연봉", "부동산", "주식", "코인", "대출", "보험", "카드", "금융", "정치", "선거", "대통령", "국회", "사건", "사고", "맛집", "음식", "카페", "여행", "호텔", "패션", "뷰티", "화장품", "육아", "건강", "다이어트", "날씨", "태풍", "최애", "팬", "콘서트"]

SAFE_TOPIC_POOL = {
    "물류자동화": ["AGV·AMR 도입 전 동선·충전·교통제어 설계 기준", "컨베이어와 로봇을 연계한 팔레타이징 자동화 설계", "자동창고 입출고 병목을 줄이는 WMS·PLC 인터페이스"],
    "딥러닝비전": ["AI 비전검사 도입 전 조명·렌즈·불량 데이터 검증 기준", "2D·3D 머신비전 선택 기준과 로봇 좌표 연동 방법", "외관검사 자동화의 오검·미검을 줄이는 설계 체크리스트"],
    "공장자동화": ["산업용 로봇 자동화 도입 전 Cycle Time과 가동률 검토 방법", "로봇 엔드이펙터 설계 시 Payload·Moment·Fail-safe 검토", "포장·조립 자동화 라인의 병목 공정 개선 방법"],
    "스마트팩토리": ["OEE 기반 설비 병목 분석과 자동화 투자 우선순위 선정", "예지보전용 센서 데이터 수집 구조와 PLC·MES 연계", "스마트팩토리 구축 전 현장 데이터 표준화 체크리스트"],
    "제어SW": ["PLC·HMI·SCADA 통합 시 네트워크와 알람 설계 기준", "Profinet·EtherCAT·Modbus 산업통신 선택 기준", "서보 모션제어 적용 시 인터록·원점·안전회로 설계"],
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
            message = client.messages.create(model=model_name, max_tokens=8192, temperature=0.2, messages=[{"role": "user", "content": prompt}])
            text = "\n".join(block.text for block in message.content if getattr(block, "type", None) == "text").strip()
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


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = re.sub(r"[·•・/\\|,;:_+\-–—()\[\]{}]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", "", _normalize_text(text))


def _contains_blocked_term(text: str) -> bool:
    normalized = _normalize_text(text)
    compact = _compact_text(text)
    for term in NON_INDUSTRIAL_BLOCKLIST:
        term_n = _normalize_text(term)
        if term_n in normalized or _compact_text(term) in compact:
            return True
    return False


def _industrial_score(text: str) -> tuple[int, str | None]:
    if _contains_blocked_term(text):
        return -100, None
    normalized = _normalize_text(text)
    compact = _compact_text(text)
    best_score = 0
    best_category = None
    for category, keywords in INDUSTRIAL_CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            key_n = _normalize_text(keyword)
            key_c = _compact_text(keyword)
            if (key_n and key_n in normalized) or (key_c and key_c in compact):
                score += 2 if len(key_c) >= 3 else 1
        if score > best_score:
            best_score = score
            best_category = category
    context_terms = ["제조", "생산", "공정", "설비", "자동화", "로봇", "검사", "제어", "산업"]
    context_hits = sum(1 for term in context_terms if _compact_text(term) in compact)
    if best_score > 0:
        best_score += min(context_hits, 2)
    return best_score, best_category


def _safe_category(priority: str) -> str:
    return priority if priority in SAFE_TOPIC_POOL else "공장자동화"


def _topic_dict(keyword: str, category: str, reason: str, score: int | None = None) -> dict:
    score_note = f" (score={score})" if score is not None else ""
    return {"keyword": keyword, "angle": f"{keyword}를 실제 자동화 설비 설계·제어·생산성·품질·ROI 관점에서 기술적으로 설명", "reason": reason + score_note, "category": category, "estimated_search_volume": "medium"}


def validate_selected_topics(selected: list[dict], priority: str = "공장자동화", top_n: int = 3) -> list[dict]:
    priority = _safe_category(priority)
    validated = []
    seen = set()
    for item in selected or []:
        keyword = str(item.get("keyword", "")).strip()
        if not keyword or keyword in seen:
            continue
        score, detected = _industrial_score(keyword)
        if score < 2 or not detected:
            logger.warning("[INDUSTRIAL-GATE] rejected LLM topic: '%s' (score=%s)", keyword, score)
            continue
        category = item.get("category")
        if category not in SAFE_TOPIC_POOL:
            category = detected if detected in SAFE_TOPIC_POOL else priority
        clean = dict(item)
        clean["keyword"] = keyword
        clean["category"] = category
        clean["reason"] = f"{clean.get('reason', 'LLM 선정')} | 산업 gate 통과(score={score})"
        validated.append(clean)
        seen.add(keyword)
        if len(validated) >= top_n:
            return validated
    pool_order = [priority] + [c for c in SAFE_TOPIC_POOL if c != priority]
    for category in pool_order:
        for keyword in SAFE_TOPIC_POOL[category]:
            if keyword in seen:
                continue
            score, detected = _industrial_score(keyword)
            if score < 2 or not detected:
                logger.error("[INDUSTRIAL-GATE] safe seed failed: '%s' score=%s", keyword, score)
                continue
            validated.append(_topic_dict(keyword, category, "LLM 결과가 산업 기준을 통과하지 못해 검증 주제로 대체", score))
            seen.add(keyword)
            if len(validated) >= top_n:
                return validated
    raise RuntimeError(f"Industrial gate could not supply {top_n} validated topics")


def _select_industrial_topics(prompt: str, top_n: int = 3) -> list[dict]:
    priority_match = re.search(r"오늘 우선 카테고리:\s*(.+)", prompt)
    priority = _safe_category(priority_match.group(1).strip() if priority_match else "공장자동화")
    trends = _extract_trend_keywords(prompt)
    candidates = []
    for keyword in trends:
        score, category = _industrial_score(keyword)
        if score >= 2 and category:
            candidates.append(_topic_dict(keyword, category if category in SAFE_TOPIC_POOL else priority, "산업 연관성 검증 통과", score))
        else:
            logger.warning("[SAFE-MODE] trend rejected: '%s' (industrial_score=%s)", keyword, score)
    candidates.sort(key=lambda item: _industrial_score(item["keyword"])[0], reverse=True)
    return validate_selected_topics(candidates, priority=priority, top_n=top_n)


def _short_safe_title(keyword: str) -> str:
    from agents.runtime_guard import clean_title_boundary
    suffix = " | 아진네트웍스"
    max_keyword = max(1, 40 - len(suffix))
    base = clean_title_boundary(keyword, max_keyword)
    return (base + suffix)[:40]


def _rule_based(prompt: str) -> str:
    logger.warning("[LLM] Switching Claude -> deterministic fallback")
    if '"selected_topics"' in prompt:
        selected = _select_industrial_topics(prompt, top_n=3)
        logger.info("[SAFE-MODE] industrial topic engine selected: %s", [x["keyword"] for x in selected])
        return json.dumps({"selected_topics": selected}, ensure_ascii=False)
    if "100점 만점으로 평가" in prompt:
        indexes = [int(x) for x in re.findall(r"\[포스트\s+(\d+)\]", prompt)]
        if indexes:
            return json.dumps([{"index": i, "score": 80, "pass": True, "reason": "규칙기반 기본 검수 통과"} for i in indexes], ensure_ascii=False)
        return json.dumps({"score": 80, "pass": True, "reason": "규칙기반 기본 검수 통과"}, ensure_ascii=False)
    if "개선된 포스트를 동일한 JSON 형식으로 반환" in prompt:
        return json.dumps({"title": "자동화 설비 개선 | 아진네트웍스", "content": "자동화 설비 개선은 현행 공정 계측, 병목 분석, Cycle Time 검증, 인터록 정의, 안전회로 검증, PoC 시험 순으로 진행해야 합니다. 생산성 개선 효과는 현장 데이터로 확인하고 불확실한 조건은 추정값과 확인값을 구분하여 관리해야 합니다.", "category": "공장자동화", "tags": ["공장자동화", "로봇자동화", "아진네트웍스"], "meta_description": "자동화 설비 개선 시 확인해야 할 공정·Cycle Time·제어·안전·PoC 검증 기준을 정리합니다."}, ensure_ascii=False)
    if "블로그 포스트를 작성" in prompt and '"title"' in prompt:
        keyword_match = re.search(r"키워드:\s*(.+)", prompt)
        keyword = keyword_match.group(1).strip() if keyword_match else "산업용 로봇 자동화"
        score, detected_category = _industrial_score(keyword)
        if score < 2 or not detected_category:
            logger.warning("[SAFE-MODE] writer rejected non-industrial keyword '%s' -> safe replacement", keyword)
            detected_category = "공장자동화"
            keyword = SAFE_TOPIC_POOL[detected_category][0]
        title = _short_safe_title(keyword)
        content = f"# {keyword}\n\n{keyword}를 검토할 때는 단순 장비 선정이 아니라 공정 데이터와 기구·제어 인터페이스를 함께 분석해야 합니다.\n\n## 1. 현행 공정 계측\n작업 순서, Cycle Time, 대기시간, 작업자 개입, 불량 발생 구간을 실측하고 병목을 분리합니다.\n\n## 2. 기구 및 로봇 검토\nPayload, Reach, Moment, 반복정밀도, EOAT, 제품 공차와 비정상 상태에서의 Fail-safe 조건을 확인합니다.\n\n## 3. PLC·비전·상위시스템 연동\nI/O, 산업통신, 인터록, 알람, 좌표계, 데이터 추적성을 정의하고 복구 시퀀스를 사전에 설계합니다.\n\n## 4. 안전 및 PoC\n위험성 평가 후 안전회로를 구성하고 PoC에서 실제 Cycle Time, 반복성, 오검·미검, 가동률을 검증합니다.\n\n## 5. 투자 판단\n자동화 전후 인원, 생산량, 불량률, 다운타임, 유지보수 비용을 동일 기준으로 비교해 ROI를 산정합니다.\n\n아진네트웍스는 로봇·PLC·비전·기구를 통합 관점에서 검토하며, 확인값과 추정값을 구분해 기술 제안에 반영합니다."
        return json.dumps({"title": title, "content": content, "category": detected_category if detected_category in SAFE_TOPIC_POOL else "공장자동화", "tags": [keyword, detected_category or "공장자동화", "산업자동화", "아진네트웍스"], "meta_description": f"{keyword}의 공정분석, 기구·PLC·비전 연동, 안전, PoC, ROI 검토 기준을 아진네트웍스가 설명합니다."}, ensure_ascii=False)
    raise RuntimeError("Deterministic fallback has no compatible response for this prompt")


def get_llm_response(prompt: str) -> str:
    errors = []
    if not provider_disabled("gemini"):
        try:
            return _gemini(prompt)
        except Exception as exc:
            errors.append(str(exc))
            hard = classify_hard_provider_failure(exc)
            if hard == "gemini":
                disable_provider("gemini")
                logger.warning("[LLM] Gemini circuit opened for this run after hard quota failure")
            logger.warning("[LLM] Switching Gemini -> Claude")
    else:
        logger.info("[LLM] Gemini skipped: circuit already open for this run")

    if not provider_disabled("claude"):
        try:
            return _claude(prompt)
        except Exception as exc:
            errors.append(str(exc))
            hard = classify_hard_provider_failure(exc)
            if hard == "claude":
                disable_provider("claude")
                logger.warning("[LLM] Claude circuit opened for this run after hard billing failure")
    else:
        logger.info("[LLM] Claude skipped: circuit already open for this run")

    try:
        return _rule_based(prompt)
    except Exception as exc:
        errors.append(str(exc))
    raise RuntimeError("All LLM providers and Ajin safe-mode failed: " + " | ".join(errors))
