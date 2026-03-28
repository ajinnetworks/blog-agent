from github import Auth, Github
from dotenv import load_dotenv
import os

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

# agents 폴더 목록 확인
print('=== agents 폴더 ===')
for item in repo.get_contents('agents', ref='main'):
    print(item.name)

# 현재 auto_post.yml 확인
f = repo.get_contents('.github/workflows/auto_post.yml', ref='main')
print('\n=== 현재 auto_post.yml ===')
print(f.decoded_content.decode('utf-8'))