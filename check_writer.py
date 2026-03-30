import re
from pathlib import Path

# writer_agent_current.py에서 front matter 생성 부분 찾아 title 추가
p = Path(r"E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\agents\writer_agent_current.py")
text = p.read_text(encoding="utf-8")

# front matter 생성 패턴 확인
if "title" not in text:
    print("❌ title 생성 코드 없음 — 추가 필요")
    # front_matter 딕셔너리에 title 추가
    old = "front_matter = {"
    new = """front_matter = {
        'title': self._generate_title(content, category),"""
    if old in text:
        text = text.replace(old, new, 1)
        p.write_text(text, encoding="utf-8")
        print("✅ title 생성 코드 추가")
else:
    print("✅ title 코드 이미 있음")
    # title 관련 코드 출력
    for i, line in enumerate(text.split("\n")):
        if "title" in line.lower():
            print(f"  {i}: {line.strip()}")
