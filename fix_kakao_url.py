import os
from github import Auth, Github

env_path = r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env'
with open(env_path, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

fp = repo.get_contents('_layouts/post.html', ref='main')
post = fp.decoded_content.decode('utf-8')

print('현재 카카오 버튼 코드:')
for i, line in enumerate(post.split('\n')):
    if 'kakao' in line.lower() or 'kakaotalk' in line.lower():
        print(f'{i+1}: {line.strip()}')

old_btn = '<button onclick="shareKakao()" class="share-btn share-kakao">\U0001f49b \uce74\uce74\uc624\ud1a1</button>'
new_btn = '<a href="https://sharer.kakao.com/talk/friends/picker/link?app_key=f49db6cf9929746a86ba847b21167032&url={{ page.url | absolute_url | uri_escape }}&text={{ page.title | uri_escape }}" target="_blank" class="share-btn share-kakao">\U0001f49b \uce74\uce74\uc624\ud1a1</a>'

if 'shareKakao()' in post:
    import re
    post = re.sub(
        r'<button[^>]*onclick=["\']shareKakao\(\)["\'][^>]*>.*?</button>',
        new_btn,
        post
    )
    repo.update_file(
        '_layouts/post.html',
        'fix: kakao share URL method',
        post,
        fp.sha,
        branch='main'
    )
    print('URL 방식으로 변경 완료')
else:
    print('버튼 미발견')