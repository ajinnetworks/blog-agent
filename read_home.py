import os
from github import Auth, Github
from dotenv import load_dotenv

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

f = repo.get_contents('_layouts/home.html', ref='main')
content = f.decoded_content.decode('utf-8')

# 전체 파일을 로컬에 저장
with open('home_current.html', 'w', encoding='utf-8') as out:
    out.write(content)

print('home_current.html 저장 완료')
print(f'총 {len(content.split(chr(10)))}줄')
