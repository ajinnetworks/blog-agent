from github import Auth, Github
from dotenv import load_dotenv
import os

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

f = repo.get_contents('.github/workflows/auto_post.yml', ref='main')
content = f.decoded_content.decode('utf-8')

content = content.replace('actions/checkout@v4', 'actions/checkout@v5')
print('checkout v4 -> v5 업그레이드')

repo.update_file(
    '.github/workflows/auto_post.yml',
    'fix: upgrade actions/checkout to v5',
    content,
    f.sha,
    branch='main'
)
print('auto_post.yml 업데이트 완료')