from github import Auth, Github
from dotenv import load_dotenv
import os

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)

print('=== 접근 가능한 저장소 목록 ===')
for repo in g.get_user().get_repos():
    print(repo.full_name)
    try:
        items = repo.get_contents('.github/workflows', ref='main')
        for item in items:
            print(f'  workflow: {item.name}')
    except:
        pass
