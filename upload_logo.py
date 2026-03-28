import os
import base64
from github import Auth, Github
from dotenv import load_dotenv

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

# 로고 파일 경로 — 본인 파일 경로로 교체
logo_path = r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\ajin_logo.png'
logo_filename = 'logo.png'  # PNG면 logo.png, SVG면 logo.svg

with open(logo_path, 'rb') as f:
    logo_data = f.read()

# 이미 업로드된 파일인지 확인
try:
    existing = repo.get_contents(f'assets/{logo_filename}', ref='main')
    repo.update_file(
        f'assets/{logo_filename}',
        'feat: update company logo',
        logo_data,
        existing.sha,
        branch='main'
    )
    print(f'로고 업데이트 완료: assets/{logo_filename}')
except:
    repo.create_file(
        f'assets/{logo_filename}',
        'feat: add company logo',
        logo_data,
        branch='main'
    )
    print(f'로고 업로드 완료: assets/{logo_filename}')
