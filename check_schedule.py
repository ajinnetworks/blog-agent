from github import Auth, Github
from dotenv import load_dotenv
import os

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

items = repo.get_contents('.github/workflows', ref='main')
print('=== workflows 파일 목록 ===')
for item in items:
    print(item.name)
    f = repo.get_contents(f'.github/workflows/{item.name}', ref='main')
    print(f.decoded_content.decode('utf-8'))
    print('---')