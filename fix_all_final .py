import os
from github import Auth, Github
from dotenv import load_dotenv

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

# ════════════════════════════════════════════
# 1. home.html 수정
#    - 사이드바 회사 로고 교체
#    - filterPosts 함수 수정
# ════════════════════════════════════════════
f = repo.get_contents('_layouts/home.html', ref='main')
home = f.decoded_content.decode('utf-8')

# 1-1. 사이드바 회사 로고 교체
old_logo = '<div class="company-logo">⚙️</div>'
new_logo = '<div class="company-logo"><img src="{{ \"/assets/ajin_logo.png\" | relative_url }}" alt="아진네트웍스 로고" style="height:60px;width:auto;display:block;margin:0 auto;" /></div>'

if old_logo in home:
    home = home.replace(old_logo, new_logo)
    print('사이드바 회사 로고 교체 완료')
else:
    print('사이드바 로고 미발견')

# 1-2. filterPosts 함수 수정 (event.target → 파라미터로 전달)
old_filter_btn = '<button class="cat-badge active" onclick="filterPosts(\'all\')">'
new_filter_btn = '<button class="cat-badge active" onclick="filterPosts(\'all\', this)">'
if old_filter_btn in home:
    home = home.replace(old_filter_btn, new_filter_btn)

old_filter_cat = '<button class="cat-badge" onclick="filterPosts(\'{{ cat_clean }}\')">'
new_filter_cat = '<button class="cat-badge" onclick="filterPosts(\'{{ cat_clean }}\', this)">'
if old_filter_cat in home:
    home = home.replace(old_filter_cat, new_filter_cat)

# 1-3. filterPosts JS 함수 수정
old_js = '''function filterPosts(cat) {
  document.querySelectorAll('.cat-badge').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.post-card').forEach(card => {
    if (cat === 'all' || card.dataset.cats.includes(cat)) {
      card.style.display = '';
    } else {
      card.style.display = 'none';
    }
  });
  document.getElementById('posts').scrollIntoView({behavior: 'smooth'});
}'''

new_js = '''function filterPosts(cat, btn) {
  // active 버튼 전환
  document.querySelectorAll('.cat-badge').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  // 포스트 필터링 (대소문자 무시, 공백 trim)
  const target = cat.trim();
  document.querySelectorAll('.post-card').forEach(card => {
    const cats = card.dataset.cats
      .split(',')
      .map(c => c.trim());
    if (target === 'all' || cats.includes(target)) {
      card.style.display = '';
    } else {
      card.style.display = 'none';
    }
  });

  // 포스트 영역으로 스크롤
  const postsEl = document.getElementById('posts');
  if (postsEl) postsEl.scrollIntoView({behavior: 'smooth'});
}'''

if old_js in home:
    home = home.replace(old_js, new_js)
    print('filterPosts 함수 수정 완료')
else:
    print('filterPosts 함수 미발견 - 수동 확인 필요')

repo.update_file(
    '_layouts/home.html',
    'fix: sidebar logo + filterPosts event.target bug',
    home,
    f.sha,
    branch='main'
)
print('home.html 업데이트 완료')

# ════════════════════════════════════════════
# 2. default.html 푸터 로고 확인 및 수정
# ════════════════════════════════════════════
fd = repo.get_contents('_layouts/default.html', ref='main')
default_html = fd.decoded_content.decode('utf-8')
default_lines = default_html.split('\n')

print('\n=== default.html 푸터 영역 확인 ===')
for i, line in enumerate(default_lines):
    if 'footer' in line.lower() or 'logo' in line.lower() or 'fb-logo' in line.lower():
        print(f'{i+1}: {line.strip()}')

# fb-logo 또는 footer logo 교체
old_fb = '<div class="fb-logo">'
if old_fb in default_html:
    # fb-logo 블록 찾아서 img 삽입
    old_fb_block = '<div class="fb-logo">'
    new_fb_block = '<div class="fb-logo"><img src="{{ \"/assets/ajin_logo.png\" | relative_url }}" alt="아진네트웍스" style="height:40px;width:auto;filter:brightness(0) invert(1);" />'
    default_html = default_html.replace(old_fb_block, new_fb_block, 1)
    repo.update_file(
        '_layouts/default.html',
        'fix: add logo to footer fb-logo block',
        default_html,
        fd.sha,
        branch='main'
    )
    print('default.html 푸터 로고 추가 완료')
else:
    print('fb-logo 블록 미발견 - 푸터 구조 확인 필요')
    print('푸터 관련 줄:')
    for i in range(310, min(360, len(default_lines))):
        print(f'{i+1}: {default_lines[i]}')
