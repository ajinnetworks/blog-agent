"""Phase 3.1 standardized tag policy for Ajin Networks industrial content."""
import re

CORE_TAGS = [
    '산업자동화','스마트팩토리','공장자동화','물류자동화','포장자동화','자동차자동화','반도체자동화','의료기기자동화',
    '산업용로봇','협동로봇','로봇비전','EOAT','그리퍼','AGV','AMR','자동창고','WMS','컨베이어',
    'PLC','HMI','SCADA','MES','OPC-UA','EtherCAT','Profinet','머신비전','딥러닝비전','3D비전','비전검사','Traceability'
]
ALIASES = {
    'ai비전검사':'딥러닝비전','ai검사':'딥러닝비전','딥러닝비전검사':'딥러닝비전','머신 비전':'머신비전',
    '3d 비전':'3D비전','agv/amr':'AMR','물류로봇':'AMR','자동창고시스템':'자동창고','as/rs':'자동창고',
    'plc제어':'PLC','plc 제어':'PLC','오피씨유에이':'OPC-UA','추적성':'Traceability','이력관리':'Traceability',
    '로봇자동화':'산업용로봇','엔드이펙터':'EOAT','엔드 이펙터':'EOAT'
}

def _norm(s: str) -> str:
    return re.sub(r'[^0-9a-zA-Z가-힣]+','',str(s).lower())

CORE_BY_NORM = {_norm(t): t for t in CORE_TAGS}
ALIAS_BY_NORM = {_norm(k): v for k,v in ALIASES.items()}

def normalize_tags(raw_tags, text: str = '', max_tags: int = 5):
    raw_tags = raw_tags if isinstance(raw_tags, list) else [raw_tags] if raw_tags else []
    chosen=[]
    def add(tag):
        if tag and tag not in chosen and tag in CORE_TAGS: chosen.append(tag)
    for raw in raw_tags:
        n=_norm(raw)
        add(CORE_BY_NORM.get(n) or ALIAS_BY_NORM.get(n))
    hay=_norm(text)
    for n, canonical in CORE_BY_NORM.items():
        if n and n in hay: add(canonical)
    for n, canonical in ALIAS_BY_NORM.items():
        if n and n in hay: add(canonical)
    if not chosen: chosen=['산업자동화']
    return chosen[:max_tags]

def normalize_posts_tags(posts):
    for post in posts:
        text=' '.join([str(post.get('title','')),str(post.get('category','')),str(post.get('content','')),str(post.get('source_topic',{}).get('keyword',''))])
        post['tags']=normalize_tags(post.get('tags',[]), text=text, max_tags=5)
    return posts
