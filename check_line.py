import os
from github import Auth, Github
from dotenv import load_dotenv

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

f = repo.get_contents('_layouts/default.html', ref='main')
content = f.decoded_content.decode('utf-8')

# 296번 줄 실제 내용 출력
lines = content.split('\n')
print(f'295번줄: {repr(lines[294])}')
print(f'296번줄: {repr(lines[295])}')
print(f'297번줄: {repr(lines[296])}')
