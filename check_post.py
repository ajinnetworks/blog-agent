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

with open('post_current.html', 'w', encoding='utf-8') as f:
    f.write(post)

print('post_current.html 저장 완료')
print(f'총 {len(post.split(chr(10)))}줄')

print('\n=== 공유 버튼 관련 코드 ===')
for i, line in enumerate(post.split('\n')):
    if any(kw in line.lower() for kw in ['share', 'kakao', 'linkedin', 'copy', '공유']):
        print(f'{i+1}: {line.strip()}')