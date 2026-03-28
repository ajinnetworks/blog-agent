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

KAKAO_KEY = 'f49db6cf9929746a86ba847b21167032'

# 1. _layouts/default.html 카카오 SDK 추가
fd = repo.get_contents('_layouts/default.html', ref='main')
default = fd.decoded_content.decode('utf-8')

kakao_sdk = '<script src="https://t1.kakaocdn.net/kakao_js_sdk/2.7.2/kakao.min.js" integrity="sha384-TiCUE00h649CAMonG018J2ujOgDKW/kVWlChEuu4jK2vxfAAD0eZxzCKakxg55G4" crossorigin="anonymous"></script>\n<script>Kakao.init(\'' + KAKAO_KEY + '\');</script>\n</body>'

if KAKAO_KEY not in default:
    default = default.replace('</body>', kakao_sdk)
    repo.update_file('_layouts/default.html', 'feat: add Kakao SDK', default, fd.sha, branch='main')
    print('SDK 추가 완료')
else:
    print('SDK 이미 존재')

# 2. _layouts/post.html 카카오 공유 버튼 + 함수 추가
fp = repo.get_contents('_layouts/post.html', ref='main')
post = fp.decoded_content.decode('utf-8')

kakao_btn = '<button onclick="shareKakao()" class="share-btn share-kakao">카카오톡 공유</button>'
kakao_fn = '''function shareKakao() {
  Kakao.Share.sendDefault({
    objectType: "feed",
    content: {
      title: document.title,
      description: document.querySelector("meta[name=description]") ? document.querySelector("meta[name=description]").content : "아진네트웍스 기술 블로그",
      imageUrl: "https://ajinnetworks.github.io/assets/images/ajin_logo.png",
      link: { mobileWebUrl: window.location.href, webUrl: window.location.href }
    },
    buttons: [{ title: "포스트 보기", link: { mobileWebUrl: window.location.href, webUrl: window.location.href } }]
  });
}'''

if 'shareKakao' not in post:
    post = post.replace('<button onclick="shareLinkedIn"', kakao_btn + '\n<button onclick="shareLinkedIn"', 1)
    post = post.replace('</script>', kakao_fn + '\n</script>', 1)
    repo.update_file('_layouts/post.html', 'feat: add Kakao share button', post, fp.sha, branch='main')
    print('카카오 버튼 추가 완료')
else:
    print('카카오 버튼 이미 존재')

# 3. assets/css/style.scss 카카오 버튼 스타일 추가
fs = repo.get_contents('assets/css/style.scss', ref='main')
scss = fs.decoded_content.decode('utf-8')

kakao_css = '''.share-kakao {
  background: #FEE500;
  color: #000000;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  font-size: 14px;
}
.share-kakao:hover { background: #F0D900; }'''

if 'share-kakao' not in scss:
    scss += '\n' + kakao_css
    repo.update_file('assets/css/style.scss', 'feat: add Kakao button style', scss, fs.sha, branch='main')
    print('카카오 CSS 추가 완료')
else:
    print('카카오 CSS 이미 존재')

print('\n모든 작업 완료')
print('1~3분 후 포스트 페이지에서 카카오 버튼 확인하세요')