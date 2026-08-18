"""Ajin Networks Safe Mode Content Engine V2.

Provides a deterministic industrial-only topic universe and category-specific
engineering guidance for runs where external LLM providers are unavailable.
No project-specific performance figures are invented here.
"""

from __future__ import annotations

CATEGORY_ORDER = [
    "물류자동화", "딥러닝비전", "공장자동화", "제어SW", "스마트팩토리",
    "포장자동화", "자동차자동화", "의료기기자동화", "반도체자동화",
]

ANGLE_TEMPLATES = (
    "{subject} 설계 시 사전 검증 기준",
    "{subject} 운영 안정화와 고장복구 설계 방법",
)

CATEGORY_SUBJECTS = {
    "물류자동화": [
        "AMR Fleet 교차로·Deadlock 교통제어", "AMR 충전 스테이션과 Opportunity Charging",
        "AS/RS 처리량과 WMS·PLC 인터페이스", "컨베이어 Merge·Diverter 병목 제어",
        "팔레트 이송 Buffer 용량과 Cycle Time", "자동창고 입출고 Queue와 우선순위 제어",
        "AGV·AMR 안전스캐너 Zone과 속도제어", "피킹 스테이션 공급·배출 동기화",
        "물류로봇 Fleet 장애 시 수동복구 시나리오", "다품종 물류라인 Routing과 Destination 관리",
    ],
    "딥러닝비전": [
        "AI 비전검사 DOE·Golden Sample·조명조건", "2D·3D 비전 FOV·해상도·정밀도 선정",
        "라인스캔 Encoder 동기와 조명 균일도", "비전 오검·미검 데이터셋과 Threshold 관리",
        "로봇 Hand-Eye Calibration과 좌표보정", "투명·반사체 검사 편광·돔·백라이트 조명",
        "OCR·OCV 문자검사와 Traceability 연계", "3D 높이검사 기준면과 Z Calibration",
        "딥러닝 모델 변경관리와 검증 데이터셋", "고속 비전검사 Trigger·Exposure·Reject 동기화",
    ],
    "공장자동화": [
        "산업용 로봇 EOAT Payload·Moment·관성", "로봇 셀 Cycle Time과 I/O 병렬처리",
        "자동화 설비 FAT 인터록·Recovery 시나리오", "협동로봇 위험성평가와 작업자 간섭",
        "조립자동화 Poka-Yoke와 Traceability", "Servo Press 압입 Force·Position 모니터링",
        "공압 실린더 End Position과 센서 진단", "Quick Change 치구와 품종 Recipe 관리",
        "로봇 Cable Dress와 간섭·수명 관리", "자동화 셀 Jam 감지와 단계별 재기동",
    ],
    "제어SW": [
        "PLC·HMI Alarm 표준화와 정지원인 추적", "OPC-UA·MES Tag 구조와 통신복구",
        "EtherCAT Servo 원점복귀와 안전정지", "Profinet Device Name·IP·진단 표준",
        "PLC 프로그램 모듈화와 설비 개조", "Robot·PLC Handshake 상태기계",
        "설비 Recipe Version과 변경이력 관리", "Safety PLC E-Stop·Door·STO 로직",
        "산업 Ethernet 통신 Timeout·Retry·Watchdog", "HMI Manual Mode 권한과 오조작 방지",
    ],
    "스마트팩토리": [
        "OEE 6대 손실과 자동화 투자 우선순위", "예지보전 진동·전류·온도 데이터 수집",
        "MES 설비 데이터 표준과 생산실적 정의", "Digital Twin Cycle Time 모델 검증",
        "설비 데이터 Ownership과 Master Data", "Andon·Downtime Reason Code 표준화",
        "Energy Monitoring과 설비별 원단위", "생산 Traceability Lot·Serial 데이터 모델",
        "Edge Gateway Buffer와 네트워크 단절 대응", "스마트팩토리 KPI Dashboard와 데이터 품질",
    ],
    "포장자동화": [
        "파우치 개구·삽입·실링 안정화", "카토닝 제품정렬과 Carton 공급",
        "실링 온도·압력·시간 Recipe와 품질이력", "포장 Vision 검사와 Reject 인터록",
        "다품종 포장 Changeover 치구 표준화", "필름 Tension·Web Guide·Mark Sensor 제어",
        "라벨 부착 위치와 Barcode 검증", "Pick-and-Place 포장 그리퍼와 제품 손상방지",
        "포장라인 Buffer와 Upstream·Downstream 동기화", "파우치 누락·겹침·미개구 검출",
    ],
    "자동차자동화": [
        "열처리 로봇 핸들링 반복정밀도와 위치보정", "중량부품 Gripper 안전율과 Fail-safe",
        "차종변경 Quick Change 지그", "Nutrunner Torque Traceability와 PLC 연계",
        "부품 Palletizing 간지취급과 적재 안정화", "Vision Bin Picking 좌표보정과 재시도",
        "열처리 전후 Scale·고온·오염 대응 EOAT", "자동차 부품 검사 MSA·GRR와 자동판정",
        "Pallet ID·차종 Recipe·공정이력 연계", "Brownfield 로봇 개조 시 기존 I/O·Safety 검증",
    ],
    "의료기기자동화": [
        "카테터 권선 장력과 최소 굽힘반경", "의료기기 파우치 삽입과 제품 손상방지",
        "튜브 인장검사 Load Cell과 반복성", "의료 포장 실링 Recipe와 Lot Traceability",
        "의료 자동화 FAT 데이터 무결성", "연성 튜브 정렬·가이드·푸셔 삽입",
        "19G·22G 교체형 검사치구와 Gauge 관리", "카테터 길이·Loop 형상 Vision 검사",
        "Clean Assembly 접촉재질과 세척성", "검사 결과 PASS·FAIL Audit Trail과 재시험 관리",
    ],
    "반도체자동화": [
        "클린룸 로봇 Particle과 Cable Management", "Wafer 진공 Gripper와 파손감지",
        "인라인 Vision Cycle Time과 검사해상도", "FOUP 이송 Interlock과 Carrier ID",
        "SECS/GEM 연계 PLC 데이터 구조", "Wafer Map과 공정 Recipe 동기화",
        "EFEM Robot Teaching과 Cassette Alignment", "Vacuum Pressure·Leak 감지와 Wafer Presence",
        "Cleanroom 소재·윤활·Cable Particle 관리", "반도체 설비 Alarm·Event·Trace 데이터 표준",
    ],
}

DOMAIN_PROFILES = {
    "물류자동화": {
        "mechanism": "동선 폭, 회전반경, 교차로, Buffer, 충전 위치, 팔레트·랙 인터페이스와 물류 단위의 치수·중량을 먼저 검토합니다.",
        "control": "Fleet Manager, WMS/WCS, PLC 사이의 Mission·Destination·Ready·Busy·Complete·Fault 상태와 교통 우선순위를 정의해야 합니다.",
        "validation": "Peak 물동량, 교차로 혼잡, Deadlock, 충전 대기, 통신 단절, 수동 회수 상황을 포함해 처리량과 Recovery를 검증합니다.",
        "rfq": "물동량/시간, 출발·도착점, 팔레트 규격, 동선도, 충전조건, WMS/WCS 유무, 목표 가동률",
        "keywords": ["AMR", "AGV", "WMS", "WCS", "Fleet", "교통제어", "Buffer"],
    },
    "딥러닝비전": {
        "mechanism": "FOV, 최소 결함 크기, Working Distance, Lens, 조명 입사각, 제품 반사율과 카메라 고정 강성을 함께 검토합니다.",
        "control": "Trigger, Exposure, Encoder, 판정 결과, 좌표값, Reject 타이밍과 제품 ID를 PLC·Robot·MES와 동기화해야 합니다.",
        "validation": "Golden Sample, 실제 불량 Sample, 조명 편차, 위치 편차를 사용해 미검·오검 기준과 반복성을 검증합니다.",
        "rfq": "검사 Sample, 최소 결함, FOV, Line Speed, CT, 허용 미검/오검, 카메라 설치공간, 판정 이력 요구",
        "keywords": ["비전검사", "카메라", "조명", "FOV", "딥러닝", "Golden Sample", "Calibration"],
    },
    "공장자동화": {
        "mechanism": "제품 공차, 파지면, 무게중심, EOAT 중량, Robot Reach·Moment·관성, 치구 반복정밀도와 유지보수 공간을 검토합니다.",
        "control": "PLC Master 기준으로 Robot·Servo·Pneumatic·Vision의 상태기계와 Manual/Auto Recovery를 명확히 분리합니다.",
        "validation": "정상 CT뿐 아니라 Jam, 센서 이상, 제품 미취출, E-Stop 후 재기동, 품종변경을 FAT 시나리오로 검증합니다.",
        "rfq": "제품 도면/중량, 현행 공정, CT, Layout, Robot/PLC 선호사양, Safety 요구, 품종수, Changeover 시간",
        "keywords": ["로봇자동화", "EOAT", "Cycle Time", "인터록", "FAT", "Recovery", "안전"],
    },
    "제어SW": {
        "mechanism": "제어반 I/O 여유, 네트워크 토폴로지, Servo·Drive 수량, Safety Device와 기존 제어 자산의 재사용 범위를 확인합니다.",
        "control": "State Machine, Handshake, Alarm Code, Timeout, Watchdog, Recipe, 권한관리, 통신복구를 표준 Function Block으로 관리합니다.",
        "validation": "전원 재인가, 통신 단절, Sensor Stuck, Servo Alarm, Robot Fault, Recipe 오류를 Fault Injection 방식으로 검증합니다.",
        "rfq": "PLC/HMI 모델, I/O List, Network 구성, 기존 Program Backup, 상위통신 규격, Alarm/Recipe 요구, Safety I/O",
        "keywords": ["PLC", "HMI", "OPC-UA", "Profinet", "EtherCAT", "Handshake", "Watchdog"],
    },
    "스마트팩토리": {
        "mechanism": "센서·PLC·Edge Gateway의 데이터 취득 지점과 설비별 Tag 품질, Timestamp, 데이터 저장주기를 먼저 정리합니다.",
        "control": "MES·SCADA·Historian·Dashboard 간 Master Data와 Event·Downtime·Production Record의 책임 시스템을 정의합니다.",
        "validation": "누락 데이터, 중복 데이터, 시간동기 오차, 네트워크 단절 후 재전송과 KPI 계산 일관성을 샘플 기간으로 검증합니다.",
        "rfq": "대상 설비수, PLC 종류, 수집 Tag, 데이터 주기, MES/ERP 유무, KPI 정의, 보존기간, 사용자 권한",
        "keywords": ["MES", "OEE", "SCADA", "IIoT", "예지보전", "Historian", "Traceability"],
    },
    "포장자동화": {
        "mechanism": "제품 형상, 포장재 마찰·정전기·강성, 개구 방식, Guide, Pusher, Seal Jaw와 Changeover 치구를 검토합니다.",
        "control": "제품 공급·포장재 공급·Mark Sensor·Servo Index·Sealing·Vision·Reject의 동기와 Recipe를 관리해야 합니다.",
        "validation": "미개구, 겹침, 제품 끼임, Seal 주름·미실링, Mark 오차, 자재 소진과 재투입 상황을 반복 시험합니다.",
        "rfq": "제품 Sample/도면, 포장재 규격, 목표 CT, 품종수, Seal 조건, 검사기준, 공급방식, Changeover 목표",
        "keywords": ["파우치", "실링", "카토닝", "포장자동화", "Mark Sensor", "Reject", "Changeover"],
    },
    "자동차자동화": {
        "mechanism": "부품 중량·온도·Scale·오염, Pallet 공차, Gripper 안전율, Robot Load·Moment와 기존 설비 간섭을 검토합니다.",
        "control": "차종 Recipe, Pallet ID, Vision 좌표, Robot Program, PLC Interlock과 공정 Traceability를 일관된 키로 연결합니다.",
        "validation": "차종 혼입, Pallet 위치편차, Gripper 미파지, Vision 실패, 기존 설비 정지와 수동운전을 포함해 Brownfield 조건을 검증합니다.",
        "rfq": "부품도면/중량, Pallet 도면, 차종수, 기존 Robot/PLC, I/O Backup, CT, 열처리 조건, 안전요구, 정지가능시간",
        "keywords": ["자동차부품", "열처리", "Gripper", "Pallet", "Vision", "Traceability", "Brownfield"],
    },
    "의료기기자동화": {
        "mechanism": "연성 제품의 최소 굽힘반경, 장력, 접촉재질, 손상 허용기준, 교체형 치구와 세척·이물 관리성을 검토합니다.",
        "control": "제품 Lot·Recipe·검사조건·Load Cell·Vision 결과를 제품 ID와 연결하고 재시험 권한과 Audit Trail을 분리합니다.",
        "validation": "제품 손상, 인장 반복성, 삽입 걸림, 실링 조건, 검사 GRR와 데이터 무결성을 Sample 기반으로 검증합니다.",
        "rfq": "제품 Sample/도면, Gauge/길이, 최소 굽힘반경, 시험하중, 파우치 규격, CT, 검사기준, Lot/Trace 요구",
        "keywords": ["카테터", "의료기기", "Load Cell", "파우치", "Traceability", "검사치구", "데이터무결성"],
    },
    "반도체자동화": {
        "mechanism": "Cleanroom 등급, Particle 발생원, Vacuum EOAT, Cable Dress, 저발진 소재·윤활과 Wafer·FOUP 취급 공차를 검토합니다.",
        "control": "SECS/GEM Event·Alarm·Recipe, Carrier ID, Wafer Map, Robot·PLC·EFEM 상태와 Host Command의 우선순위를 정의합니다.",
        "validation": "Wafer Presence, Vacuum Leak, Cassette 오정렬, Host 통신 단절, Robot Recovery와 Particle 영향을 실제 조건으로 검증합니다.",
        "rfq": "Wafer/FOUP 규격, Cleanroom 등급, CT, EFEM/Robot 사양, SECS/GEM 요구, Host Interface, Particle 기준, Vacuum 조건",
        "keywords": ["반도체자동화", "Cleanroom", "Wafer", "FOUP", "SECS/GEM", "Vacuum", "Particle"],
    },
}

DEFAULT_PROFILE = DOMAIN_PROFILES["공장자동화"]


def build_topic_pool() -> dict[str, list[str]]:
    """Return >=20 deterministic, industrial-only candidates per category."""
    pools: dict[str, list[str]] = {}
    for category in CATEGORY_ORDER:
        subjects = CATEGORY_SUBJECTS[category]
        candidates = []
        for subject in subjects:
            for template in ANGLE_TEMPLATES:
                candidates.append(template.format(subject=subject))
        pools[category] = candidates
    return pools


def domain_profile(category: str) -> dict:
    return DOMAIN_PROFILES.get(str(category or ""), DEFAULT_PROFILE)
