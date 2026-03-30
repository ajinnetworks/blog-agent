import re
from pathlib import Path

# 1. writer_agent.py에서 title 관련 코드 확인
p = Path(r"E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\agents\writer_agent.py")
text = p.read_text(encoding="utf-8")

print("=== title 관련 코드 ===")
for i, line in enumerate(text.split("\n"), 1):
    if "title" in line.lower():
        print(f"  {i:4d}: {line.rstrip()}")

# front_matter 생성 위치 확인
print("\n=== front_matter 관련 코드 ===")
for i, line in enumerate(text.split("\n"), 1):
    if "front_matter" in line.lower() or "frontmatter" in line.lower():
        print(f"  {i:4d}: {line.rstrip()}")
