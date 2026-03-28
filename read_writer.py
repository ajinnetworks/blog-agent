import os
from github import Auth, Github
from dotenv import load_dotenv

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

# agents 폴더 목록 확인
items = repo.get_contents('agents', ref='main')
print('=== agents 폴더 목록 ===')
for item in items:
    print(item.name)

# writer_agent.py 읽기
try:
    f = repo.get_contents('agents/writer_agent.py', ref='main')
    content = f.decoded_content.decode('utf-8')
    with open('writer_agent_current.py', 'w', encoding='utf-8') as out:
        out.write(content)
    print('\nwriter_agent_current.py 저장 완료')
    print(f'총 {len(content.split(chr(10)))}줄')
except Exception as e:
    print(f'writer_agent.py 없음: {e}')
    # 로컬 파일 확인
    local_path = r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\agents\writer_agent.py'
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        with open('writer_agent_current.py', 'w', encoding='utf-8') as out:
            out.write(content)
        print('로컬 파일에서 저장 완료')
