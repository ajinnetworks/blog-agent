import os
import io
import base64
from PIL import Image
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

KAKAO_KEY = 'f49db6cf9929746a86ba847b21167032'

# ── 1. favicon 생성 ──────────────────────────
logo_path = r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\ajin_logo.png'
img = Image.open(logo_path).convert('RGBA')
img = img.resize((32, 32), Image.LANCZOS)
buf = io.BytesIO()
img.save(buf, format='PNG')
favicon_data = buf.getvalue()

try:
    existing = repo.get_contents('assets/images/favicon.png', ref='main')
    repo.update_file('assets/images/favicon.png', 'feat: add favicon', favicon_data, existing.sha, branch='main')
except:
    repo.create_file('assets/images/favicon.png', 'feat: add favicon', favicon_data, branch='main')
print('favicon.png 업로드 완료')

# ── 2. _includes/head.html favicon 태그 추가 ──
try:
    fh = repo.get_contents('_includes/head.html', ref='main')
    head = fh.decoded_content.decode('utf-8')
    favicon_tag = '<link rel="icon" type="image/png" href="{{ \"/assets/images/favicon.png\" | relative_url }}">\n'
    if 'favicon' not in head:
        head = head.replace('<meta charset', favicon_tag + '<meta charset', 1)
        repo.update_file('_includes/head.html', 'feat: add favicon link', head, fh.sha, branch='main')
        print('head.html favicon 태그 추가 완료')
    else:
        print('favicon 태그 이미 존재')
except Exception as e:
    print(f'head.html 없음: {e}')
    fd = repo.get_contents('_layouts/default.html', ref='main')
    default = fd.decoded_content.decode('utf-8')
    favicon_tag = '<link rel="icon" type="image/png" href="{{ \"/assets/images/favicon.png\" | relative_url }}">\n'
    if 'favicon' not in default:
        default = default.replace('</head>', favicon_tag + '</head>', 1)
        repo.update_file('_layouts/default.html', 'feat: add favicon', default, fd.sha, branch='main')
        print('default.html favicon 태그 추가 완료')

# ── 3. post.html 카카오 완전 재작성 ──────────
fp = repo.get_contents('_layouts/post.html', ref='main')
post = fp.decoded_content.decode('utf-8')

# 기존 카카오 관련 코드 모두 제거 후 재삽입
lines = post.split('\n')
clean_lines = []
skip = False
for line in lines:
    if 'kakao_js_sdk' in line or 'Kakao.init' in line:
        skip = True
    if skip and '</script>' in line:
        skip = False
        continue
    if not skip:
        clean_lines.append(line)

post = '\n'.join(clean_lines)

kakao_full = '''
<!-- Kakao Share -->
<script src="https://t1.kakaocdn.net/kakao_js_sdk/2.7.2/kakao.min.js" integrity="sha384-TiCUE00h649CAMonG018J2ujOgDKW/kVWlChEuu4jK2vxfAAD0eZxzCKakxg55G4" crossorigin="anonymous"></script>
<script>
window.addEventListener('load', function() {
  if (window.Kakao && !Kakao.isInitialized()) {
    Kakao.init('''' + KAKAO_KEY + '''');
    console.log('Kakao ready:', Kakao.isInitialized());
  }
});

function shareKakao() {
  if (!window.Kakao) { alert('카카오 SDK 로드 실패'); return; }
  if (!Kakao.isInitialized()) { Kakao.init('''' + KAKAO_KEY + ''''); }
  Kakao.Share.sendDefault({
    objectType: 'feed',
    content: {
      title: document.title,
      description: (document.querySelector('meta[name="description"]') || {}).content || '아진네트웍스 기술 블로그',
      imageUrl: 'https://ajinnetworks.github.io/assets/images/ajin_logo.png',
      link: { mobileWebUrl: window.location.href, webUrl: window.location.href }
    },
    buttons: [{ title: '포스트 보기', link: { mobileWebUrl: window.location.href, webUrl: window.location.href } }]
  });
}
</script>
</body>'''

post = post.replace('</body>', kakao_full)

repo.update_file(
    '_layouts/post.html',
    'fix: rewrite Kakao share script',
    post,
    fp.sha,
    branch='main'
)
print('post.html 카카오 재작성 완료')
print('\n모든 작업 완료')