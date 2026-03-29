p = r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\_includes\og-tags.html'
with open(p, 'r', encoding='utf-8') as f:
    html = f.read()
html = html.replace(
    "/assets/images/og-default.png",
    "/assets/img/og-default.png"
)
with open(p, 'w', encoding='utf-8') as f:
    f.write(html)
print("✅ OG 이미지 경로 수정 완료")
