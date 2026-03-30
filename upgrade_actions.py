from pathlib import Path

wf = Path(r"E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.github\workflows\auto-post.yml")
text = wf.read_text(encoding="utf-8")
original = text

text = text.replace("actions/checkout@v4", "actions/checkout@v4.2.2")
text = text.replace("actions/setup-python@v5", "actions/setup-python@v5.4.0")
text = text.replace("actions/upload-artifact@v3", "actions/upload-artifact@v4.6.2")
text = text.replace("actions/upload-artifact@v4\"", "actions/upload-artifact@v4.6.2\"")

if text != original:
    wf.write_text(text, encoding="utf-8")
    print("✅ auto-post.yml 업그레이드 완료")
else:
    print("ℹ️  변경사항 없음 — 이미 최신 버전")

# 현재 버전 확인
import re
versions = re.findall(r"actions/\S+@\S+", text)
for v in set(versions):
    print(f"  {v}")
