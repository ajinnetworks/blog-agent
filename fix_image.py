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

# assets/css/style.scss 이미지 규격 수정
fs = repo.get_contents('assets/css/style.scss', ref='main')
scss = fs.decoded_content.decode('utf-8')

image_css = '''
.post-thumbnail {
  width: 100%;
  height: 200px;
  object-fit: cover;
  border-radius: 8px 8px 0 0;
  display: block;
}
.post-card img {
  width: 100%;
  height: 200px;
  object-fit: cover;
  border-radius: 8px 8px 0 0;
}
.post-page img {
  width: 100%;
  max-height: 500px;
  object-fit: cover;
  border-radius: 8px;
  margin: 20px 0;
}
@media (max-width: 640px) {
  .post-thumbnail, .post-card img { height: 160px; }
  .post-page img { max-height: 280px; }
}'''

if 'post-thumbnail' not in scss:
    scss += image_css
    repo.update_file(
        'assets/css/style.scss',
        'fix: standardize image dimensions 16:9',
        scss,
        fs.sha,
        branch='main'
    )
    print('이미지 규격 CSS 추가 완료')
else:
    print('이미지 CSS 이미 존재')

# _layouts/post.html 이미지 태그에 클래스 추가
fp = repo.get_contents('_layouts/post.html', ref='main')
post = fp.decoded_content.decode('utf-8')

print('\n현재 post.html 이미지 관련 줄:')
for i, line in enumerate(post.split('\n')):
    if 'img' in line.lower() or 'image' in line.lower() or 'thumbnail' in line.lower():
        print(f'{i+1}: {line.strip()}')