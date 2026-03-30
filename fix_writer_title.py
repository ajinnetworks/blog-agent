import re
from pathlib import Path

p = Path(r"E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\agents\writer_agent.py")
text = p.read_text(encoding="utf-8")
p.with_suffix(".py.bak").write_text(text, encoding="utf-8")

# 293줄: title: {post.get("title", "")} → title 없으면 description으로 대체
old = 'title: {post.get("title", "")}'
new = 'title: {post.get("title", "") or post.get("description", "")[:40]}'

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("✅ title 폴백 수정 완료")
    print(f"  변경: {old}")
    print(f"  →     {new}")
else:
    # 전체 title 관련 줄 출력
    print("⚠️ 패턴 없음. 실제 293줄 내용 확인:")
    lines = text.split("\n")
    for i in [291, 292, 293, 294, 295]:
        if i < len(lines):
            print(f"  {i+1}: {lines[i]}")
