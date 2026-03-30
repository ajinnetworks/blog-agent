from pathlib import Path

WRITER = Path(r"E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\agents\writer_agent.py")

TITLE_METHOD = """
    def _generate_title(self, content: str, category: str) -> str:
        prompt = f"다음 블로그 포스트 내용으로 한국어 제목 30자 이내 작성. 텍스트만 출력.\\n카테고리: {category}\\n내용: {content[:300]}"
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip().strip(chr(34)+chr(39)).strip()[:50]
        except Exception as e:
            return ""

"""

text = WRITER.read_text(encoding="utf-8")
WRITER.with_suffix(".py.bak_title").write_text(text, encoding="utf-8")

changed = 0

if "_generate_title" not in text:
    target = "    def generate"
    if target in text:
        text = text.replace(target, TITLE_METHOD + target, 1)
        changed += 1
        print("✅ _generate_title 메서드 추가")
    else:
        print("⚠️  삽입 위치 없음")

old = 'post.get("title", "") or post.get("description", "")[:40]'
new = 'post.get("title", "") or self._generate_title(post.get("content",""), post.get("category",""))'
if old in text:
    text = text.replace(old, new, 1)
    changed += 1
    print("✅ title 호출 업그레이드")

WRITER.write_text(text, encoding="utf-8")
print(f"완료: {changed}개 수정")
