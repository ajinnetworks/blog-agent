import os
from github import Github
from dotenv import load_dotenv

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
g = Github(os.environ['GITHUB_TOKEN'])
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

f = repo.get_contents('_layouts/default.html', ref='main')
content = f.decoded_content.decode('utf-8')

if 'google-site-verification' in content:
    print('이미 삽입되어 있습니다.')
else:
    meta_tag = '<meta name="google-site-verification" content="Q3BDRaC5dhhNiHwPbnXtM2nDQ8-aqaj3TSXctJEnvn8" />'
    new_content = content.replace('</head>', meta_tag + '\n</head>', 1)
    repo.update_file(
        '_layouts/default.html',
        'feat: add Google Search Console verification meta tag',
        new_content,
        f.sha,
        branch='main'
    )
    print('삽입 완료.')
