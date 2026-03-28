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

fd = repo.get_contents('_layouts/default.html', ref='main')
default = fd.decoded_content.decode('utf-8')

old_footer = '<footer class="site-footer">'
new_footer = '''<footer class="site-footer">
  <div class="footer-company-info" style="background:#0a0e1a;color:rgba(255,255,255,0.8);padding:40px 20px;text-align:center;border-top:1px solid rgba(0,150,255,0.2);">
    <img src="{{ "/assets/ajin_logo.png" | relative_url }}" alt="아진네트웍스" style="height:40px;width:auto;filter:brightness(0) invert(1);margin-bottom:16px;" />
    <p style="font-size:16px;font-weight:700;color:#fff;margin-bottom:12px;">아진네트웍스 주식회사 | AJIN NETWORKS Co., Ltd.</p>
    <p style="font-size:13px;color:rgba(0,150,255,0.8);margin-bottom:16px;">Machine Vision &amp; FA Total Solution</p>
    <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:8px 24px;font-size:13px;color:rgba(255,255,255,0.6);margin-bottom:12px;">
      <span>📍 본사: 경기도 시흥시 금오로212번길 19-1</span>
      <span>🏭 FA사업부: 경기도 평택시 청북읍 현곡산단로 28-9</span>
    </div>
    <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:8px 24px;font-size:13px;color:rgba(255,255,255,0.6);margin-bottom:12px;">
      <span>📞 010-4168-0472</span>
      <span>📠 FAX: 0504-419-0472</span>
      <span>✉️ wave624@naver.com</span>
      <span>🌐 <a href="https://www.ajinnetworks.co.kr" target="_blank" style="color:#4da6ff;">www.ajinnetworks.co.kr</a></span>
    </div>
  </div>'''

if old_footer in default:
    default = default.replace(old_footer, new_footer, 1)
    repo.update_file(
        '_layouts/default.html',
        'fix: correct company address in footer',
        default,
        fd.sha,
        branch='main'
    )
    print('푸터 주소 수정 완료')
else:
    print('푸터 위치 미발견')
    for i, line in enumerate(default.split('\n')):
        if 'footer' in line.lower():
            print(f'{i+1}: {line.strip()}')