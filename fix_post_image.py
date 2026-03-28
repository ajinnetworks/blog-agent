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

fs = repo.get_contents('assets/css/style.scss', ref='main')
scss = fs.decoded_content.decode('utf-8')

image_fix = '''
/* 포스트 본문 이미지 규격 통일 */
.post-content img,
.post-body img,
article img,
.post-page img {
  width: 100%;
  max-width: 100%;
  height: 400px;
  object-fit: cover;
  object-position: center;
  border-radius: 8px;
  margin: 24px 0;
  display: block;
}

/* 포스트 상단 대표 이미지 */
.post-hero-image {
  width: 100%;
  height: 400px;
  object-fit: cover;
  object-position: center;
  border-radius: 12px;
  margin-bottom: 32px;
  display: block;
}

/* 포스트 컨테이너 overflow 방지 */
.post-page,
.post-content,
article {
  overflow: hidden;
  max-width: 100%;
}

/* 모바일 이미지 규격 */
@media (max-width: 768px) {
  .post-content img,
  .post-body img,
  article img,
  .post-page img,
  .post-hero-image {
    height: 220px;
    border-radius: 6px;
    margin: 16px 0;
  }
}

/* 포스트 카드 이미지 */
.post-card img {
  width: 100%;
  height: 200px;
  object-fit: cover;
  object-position: center;
  border-radius: 8px 8px 0 0;
  display: block;
}'''

if 'post-hero-image' not in scss:
    scss += image_fix
    repo.update_file(
        'assets/css/style.scss',
        'fix: post image size standardization',
        scss,
        fs.sha,
        branch='main'
    )
    print('이미지 규격 CSS 적용 완료')
else:
    # 기존 값 업데이트
    print('기존 CSS 업데이트 필요 — 수동 확인')

print('완료 — 1~3분 후 포스트 페이지 새로고침 후 확인하세요')