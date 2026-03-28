import os
from github import Github
from dotenv import load_dotenv

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
g = Github(os.environ['GITHUB_TOKEN'])
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

f = repo.get_contents('_config.yml', ref='main')
content = f.decoded_content.decode('utf-8')

content = content.replace('  - assets/\n', '')
content = content.replace('- assets/\n', '')
print('수정 완료')

repo.update_file('_config.yml', 'fix: assets exclude 제거', content.encode('utf-8'), f.sha, branch='main')
print('업로드 완료')
