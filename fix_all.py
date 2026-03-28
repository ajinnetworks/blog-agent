import os
from github import Auth, Github
from dotenv import load_dotenv

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

# ── 1. default.html 수정 ──────────────────────
f = repo.get_contents('_layouts/default.html', ref='main')
content = f.decoded_content.decode('utf-8')
original = content

# 로고 배경 제거: logo-box CSS에서 배경/border-radius 제거
content = content.replace(
    '.logo-box{width:32px;height:32px;background:linear-gradient(135deg,var(--gold-500),var(--gold-300));border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;}',
    '.logo-box{display:flex;align-items:center;justify-content:center;flex-shrink:0;background:none;}'
)

# 로고 img 교체 (296번줄 실제값 기반)
lines = content.split('\n')
target = lines[295].strip()
new_logo = '<div class="logo-box"><img src="{{ "/assets/ajin_logo.png" | relative_url }}" alt="ajin logo" style="height:40px;width:auto;display:block;" /></div>'
if target in content:
    content = content.replace(target, new_logo, 1)
    print('로고 교체 완료')
else:
    print('로고 교체 실패 - 실제값:', repr(target))

if content != original:
    repo.update_file(
        '_layouts/default.html',
        'fix: remove logo background, replace icon with image',
        content,
        f.sha,
        branch='main'
    )
    print('default.html 업데이트 완료')

# ── 2. home.html 읽어서 카테고리 중복 확인 ──
try:
    h = repo.get_contents('_layouts/home.html', ref='main')
    home = h.decoded_content.decode('utf-8')
    print('\n=== home.html 카테고리 관련 코드 ===')
    for i, line in enumerate(home.split('\n')):
        if 'categor' in line.lower() or 'filter' in line.lower():
            print(f'{i+1}: {line.strip()}')
except:
    print('home.html 없음')

# ── 3. _layouts 파일 목록 확인 ──
items = repo.get_contents('_layouts', ref='main')
print('\n=== _layouts 파일 목록 ===')
for item in items:
    print(item.name)
