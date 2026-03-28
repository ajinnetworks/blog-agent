import os
from github import Auth, Github

env_path = r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env'
with open(env_path, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')
GA4_ID = 'G-RYPE4V64TJ'

# 1. _config.yml
f = repo.get_contents('_config.yml', ref='main')
config = f.decoded_content.decode('utf-8')
if 'google_analytics' not in config:
    config += f'\ngoogle_analytics: {GA4_ID}\n'
    repo.update_file('_config.yml', 'feat: add GA4 ID', config, f.sha, branch='main')
    print('_config.yml GA4 추가 완료')
else:
    print('_config.yml GA4 이미 존재')

# 2. default.html
fd = repo.get_contents('_layouts/default.html', ref='main')
default = fd.decoded_content.decode('utf-8')
ga4 = f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>\n<script>\n  window.dataLayer = window.dataLayer || [];\n  function gtag(){{dataLayer.push(arguments);}}\n  gtag("js", new Date());\n  gtag("config", "{GA4_ID}");\n</script>'
if GA4_ID not in default:
    default = default.replace('</head>', ga4 + '\n</head>', 1)
    repo.update_file('_layouts/default.html', 'feat: add GA4 script', default, fd.sha, branch='main')
    print('default.html GA4 삽입 완료')
else:
    print('default.html GA4 이미 존재')

# 3. auto_post.yml checkout v5
try:
    fw = repo.get_contents('.github/workflows/auto_post.yml', ref='main')
    wf = fw.decoded_content.decode('utf-8')
    if 'checkout@v4' in wf:
        wf = wf.replace('actions/checkout@v4', 'actions/checkout@v5')
        repo.update_file('.github/workflows/auto_post.yml', 'fix: checkout v5', wf, fw.sha, branch='main')
        print('workflow checkout v5 완료')
    else:
        print('workflow 이미 v5')
except Exception as e:
    print(f'workflow 오류: {e}')

print('\n=== 완료 ===')
print(f'GA4 ID: {GA4_ID}')