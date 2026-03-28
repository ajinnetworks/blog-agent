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

KAKAO_KEY = 'f49db6cf9929746a86ba847b21167032'

fp = repo.get_contents('_layouts/post.html', ref='main')
post = fp.decoded_content.decode('utf-8')

print('총 줄수:', len(post.split('\n')))
print('</body> 존재:', '</body>' in post)
print('shareKakao 존재:', 'shareKakao' in post)
print('share-section 존재:', 'share-section' in post)

lines = post.split('\n')
for i, line in enumerate(lines[-30:], len(lines)-30):
    print(f'{i+1}: {repr(line)}')