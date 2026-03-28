from github import Auth, Github
from dotenv import load_dotenv
import os

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

# publisher_agent.py 첫 30줄 확인
f = repo.get_contents('agents/publisher_agent.py', ref='main')
lines = f.decoded_content.decode('utf-8').split('\n')
print('=== publisher_agent.py 상단 30줄 ===')
for i, line in enumerate(lines[:30], 1):
    print(f'{i}: {line}')

# auto_post.yml 올바른 저장소에 생성
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
      - name: Checkout repo
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.BLOG_GITHUB_TOKEN }}
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install anthropic PyGithub python-dotenv PyYAML requests beautifulsoup4 Pillow

      - name: Create .env
        run: |
          echo "ANTHROPIC_API_KEY=${{ secrets.ANTHROPIC_API_KEY }}" >> .env
          echo "GITHUB_TOKEN=${{ secrets.BLOG_GITHUB_TOKEN }}" >> .env
          echo "BLOG_REPO=${{ secrets.BLOG_REPO }}" >> .env
          echo "GMAIL_USER=${{ secrets.GMAIL_USER }}" >> .env
          echo "GMAIL_APP_PASSWORD=${{ secrets.GMAIL_APP_PASSWORD }}" >> .env

      - name: Run publisher agent
        run: python agents/publisher_agent.py

      - name: Cleanup
        if: always()
        run: rm -f .env
"""

try:
    existing = repo.get_contents('.github/workflows/auto_post.yml', ref='main')
    repo.update_file(
        '.github/workflows/auto_post.yml',
        'feat: fix auto post schedule with correct entry point',
        schedule_yml,
        existing.sha,
        branch='main'
    )
    print('\nauto_post.yml 업데이트 완료')
except Exception as e:
    print(f'\n업데이트 실패: {e}')
    try:
        repo.create_file(
            '.github/workflows/auto_post.yml',
            'feat: add auto post schedule',
            schedule_yml,
            branch='main'
        )
        print('auto_post.yml 신규 생성 완료')
    except Exception as e2:
        print(f'생성도 실패: {e2}')

print('\n스케줄 설정:')
print('  화요일 09:00 KST (UTC 00:00)')
print('  목요일 09:00 KST (UTC 00:00)')
print('  토요일 09:00 KST (UTC 00:00)')