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

fp = repo.get_contents('_layouts/post.html', ref='main')
post = fp.decoded_content.decode('utf-8')

# LinkedIn 버튼 앞에 카카오 버튼 삽입
kakao_btn = '<button onclick="shareKakao()" class="share-btn share-kakao">💛 카카오톡</button>\n'
old_linkedin = '<a href="https://www.linkedin.com'

if 'shareKakao' not in post:
    post = post.replace(old_linkedin, kakao_btn + old_linkedin, 1)
    print('카카오 버튼 삽입 완료')
else:
    print('카카오 버튼 이미 존재')

# shareKakao 함수 삽입 — </script> 앞에
kakao_fn = '''
function shareKakao() {
  if (!window.Kakao || !Kakao.isInitialized()) {
    alert('카카오 SDK 로딩 중입니다. 잠시 후 다시 시도해주세요.');
    return;
  }
  Kakao.Share.sendDefault({
    objectType: 'feed',
    content: {
      title: document.title,
      description: document.querySelector('meta[name="description"]')
        ? document.querySelector('meta[name="description"]').content
        : '아진네트웍스 기술 블로그',
      imageUrl: 'https://ajinnetworks.github.io/assets/images/ajin_logo.png',
      link: {
        mobileWebUrl: window.location.href,
        webUrl: window.location.href
      }
    },
    buttons: [{
      title: '포스트 보기',
      link: {
        mobileWebUrl: window.location.href,
        webUrl: window.location.href
      }
    }]
  });
}'''

if 'shareKakao' not in post:
    post = post.replace('</script>', kakao_fn + '\n</script>', 1)
elif 'shareKakao' in post and 'Kakao.Share' not in post:
    post = post.replace('</script>', kakao_fn + '\n</script>', 1)

repo.update_file(
    '_layouts/post.html',
    'feat: add KakaoTalk share button',
    post,
    fp.sha,
    branch='main'
)
print('post.html 업데이트 완료')

# style.scss 카카오 버튼 스타일
fs = repo.get_contents('assets/css/style.scss', ref='main')
scss = fs.decoded_content.decode('utf-8')

if 'share-kakao' not in scss:
    scss += '''
.share-kakao {
  background: #FEE500;
  color: #000000;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  font-size: 14px;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.share-kakao:hover { background: #F0D900; transform: translateY(-1px); }'''
    repo.update_file('assets/css/style.scss', 'feat: kakao button style', scss, fs.sha, branch='main')
    print('CSS 추가 완료')
else:
    print('CSS 이미 존재')

print('\n완료 — 1~3분 후 포스트 페이지에서 카카오 버튼 확인하세요')