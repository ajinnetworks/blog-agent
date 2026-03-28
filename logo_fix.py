import os
import io
from PIL import Image
from github import Auth, Github
from dotenv import load_dotenv

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

logo_path = r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\ajin_logo.png'

# 1. 압축
img = Image.open(logo_path).convert('RGBA')
MAX_HEIGHT = 80
ratio = MAX_HEIGHT / img.height
new_w = int(img.width * ratio)
img = img.resize((new_w, MAX_HEIGHT), Image.LANCZOS)
buffer = io.BytesIO()
img.save(buffer, format='PNG', optimize=True, compress_level=9)
logo_data = buffer.getvalue()
original_kb = os.path.getsize(logo_path) // 1024
compressed_kb = len(logo_data) // 1024
print(f'압축 완료: {original_kb}KB -> {compressed_kb}KB ({new_w}x{MAX_HEIGHT}px)')

# 2. 업로드
logo_filename = 'ajin_logo.png'
try:
    existing = repo.get_contents(f'assets/{logo_filename}', ref='main')
    repo.update_file(
        f'assets/{logo_filename}',
        'feat: upload optimized company logo',
        logo_data,
        existing.sha,
        branch='main'
    )
    print(f'로고 업데이트 완료: assets/{logo_filename}')
except Exception as e:
    repo.create_file(
        f'assets/{logo_filename}',
        'feat: upload optimized company logo',
        logo_data,
        branch='main'
    )
    print(f'로고 업로드 완료: assets/{logo_filename}')

# 3. default.html 교체
f = repo.get_contents('_layouts/default.html', ref='main')
content = f.decoded_content.decode('utf-8')

old = '<div class="logo-box">\u2699</div>'
new = '<div class="logo-box"><img src="{{ "/assets/ajin_logo.png" | relative_url }}" alt="ajin logo" style="height:40px;width:auto;display:block;" /></div>'

if old in content:
    new_content = content.replace(old, new, 1)
    repo.update_file(
        '_layouts/default.html',
        'feat: replace icon with company logo image',
        new_content,
        f.sha,
        branch='main'
    )
    print('default.html 로고 교체 완료')
else:
    lines = content.split('\n')
    print('미발견 - 실제값:', repr(lines[295]))
