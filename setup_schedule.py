from github import Auth, Github
from dotenv import load_dotenv
import os

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

schedule_yml = """name: Auto Blog Post

on:
  schedule:
    - cron: '0 0 * * 2'
    - cron: '0 0 * * 4'
    - cron: '0 0 * * 6'
  workflow_dispatch:

jobs:
  auto-post:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout blog repo
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Checkout agent repo
        uses: actions/checkout@v4
        with:
          repository: ajinnetworks/ajinnetworks.github.io
          path: blog_agent
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install anthropic PyGithub python-dotenv PyYAML requests beautifulsoup4 Pillow

      - name: Run blog agent
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          cd blog_agent
          python agents/main_agent.py

      - name: Trigger Pages deploy
        run: echo "Deploy triggered by post commit"
"""

try:
    existing = repo.get_contents('.github/workflows/auto_post.yml', ref='main')
    repo.update_file(
        '.github/workflows/auto_post.yml',
        'feat: add auto post schedule Tue/Thu/Sat 09:00 KST',
        schedule_yml,
        existing.sha,
        branch='main'
    )
    print('auto_post.yml 업데이트 완료')
except:
    repo.create_file(
        '.github/workflows/auto_post.yml',
        'feat: add auto post schedule Tue/Thu/Sat 09:00 KST',
        schedule_yml,
        branch='main'
    )
    print('auto_post.yml 생성 완료')

print('')
print('스케줄 설정:')
print('  화요일 09:00 KST (UTC 00:00)')
print('  목요일 09:00 KST (UTC 00:00)')
print('  토요일 09:00 KST (UTC 00:00)')
print('')
print('다음 단계: GitHub Secrets에 ANTHROPIC_API_KEY 등록 필요')
print('  Settings > Secrets > Actions > New repository secret')