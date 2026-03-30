import re
from pathlib import Path
from dotenv import load_dotenv
import os, google.generativeai as genai

load_dotenv(override=True)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

posts_dir = Path(r"E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\github_pages\_posts")
fixed = 0

for md in sorted(posts_dir.glob("*.md")):
    text = md.read_text(encoding="utf-8")
    if "title:" in text:
        continue
    
    desc = re.search(r"description:\s*(.+)", text)
    desc = desc.group(1).strip().strip('"') if desc else ""
    
    try:
        title = model.generate_content(
            f"다음 내용으로 한국어 블로그 제목 30자 이내 작성. 텍스트만 출력:\n{desc[:200]}"
        ).text.strip()[:60]
    except:
        title = desc[:40]
    
    new_text = text.replace("---\n", f'---\ntitle: "{title}"\n', 1)
    md.write_text(new_text, encoding="utf-8")
    print(f"✅ {md.name[:30]}: {title}")
    fixed += 1

print(f"\n완료: {fixed}개 title 추가")
