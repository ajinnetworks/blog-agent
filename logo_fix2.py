import os
from github import Auth, Github
from dotenv import load_dotenv

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

f = repo.get_contents('_layouts/default.html', ref='main')
content = f.decoded_content.decode('utf-8')

lines = content.split('\n')
target_line = lines[295]
print('실제값(repr):', repr(target_line))

old = target_line.strip()
new = '<div class="logo-box"><img src="{{ "/assets/ajin_logo.png" | relative_url }}" alt="ajin logo" style="height:40px;width:auto;display:block;" /></div>'

if old in content:
    new_content = content.replace(old, new, 1)
    repo.update_file(
        '_layouts/default.html',
        'feat: replace icon with company logo image',
        new_content,
        f.sha,
        branch='main'
    )
    print('로고 교체 완료')
else:
    print('교체 실패 - repr 값을 공유해주세요')
