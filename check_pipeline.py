from github import Auth, Github
from dotenv import load_dotenv
import os

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

agents = [
    'publisher_agent.py',
    'github_publisher.py',
    'trend_agent.py',
    'reviewer_agent.py',
    'writer_agent.py',
    'email_notifier.py',
    'image_optimizer.py',
]

for name in agents:
    try:
        f = repo.get_contents(f'agents/{name}', ref='main')
        content = f.decoded_content.decode('utf-8')
        lines = content.split('\n')
        print(f'\n{"="*50}')
        print(f'{name} ({len(lines)}줄)')
        print(f'{"="*50}')
        for i, line in enumerate(lines, 1):
            if any(kw in line for kw in [
                '__main__',
                'def run_',
                'import ',
                'HUMAN_GATE',
                'trend_agent',
                'writer_agent',
                'reviewer_agent',
                'github_publisher',
                'publisher_agent',
            ]):
                print(f'{i:4d}: {line}')
    except Exception as e:
        print(f'{name}: 없음 ({e})')