import os
from github import Auth, Github
from dotenv import load_dotenv

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

# default.html 푸터 부분 확인
f = repo.get_contents('_layouts/default.html', ref='main')
content = f.decoded_content.decode('utf-8')
lines = content.split('\n')

print('=== default.html 푸터 영역 (310~360번줄) ===')
for i in range(309, min(360, len(lines))):
    print(f'{i+1}: {lines[i]}')

# home.html 회사 위젯 확인
h = repo.get_contents('_layouts/home.html', ref='main')
home = h.decoded_content.decode('utf-8')
home_lines = home.split('\n')

print('\n=== home.html 회사 위젯 영역 ===')
for i, line in enumerate(home_lines):
    if 'company' in line.lower() or 'logo' in line.lower() or 'footer' in line.lower():
        print(f'{i+1}: {line}')

with open('default_current.html', 'w', encoding='utf-8') as f2:
    f2.write(content)
with open('home_latest.html', 'w', encoding='utf-8') as f3:
    f3.write(home)
print('\n파일 저장 완료')
