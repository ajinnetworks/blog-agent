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

print('shareKakao 존재:', 'shareKakao' in post)
print('Kakao.Share 존재:', 'Kakao.Share' in post)

kakao_script = """
<script src="https://t1.kakaocdn.net/kakao_js_sdk/2.7.2/kakao.min.js" integrity="sha384-TiCUE00h649CAMonG018J2ujOgDKW/kVWlChEuu4jK2vxfAAD0eZxzCKakxg55G4" crossorigin="anonymous"></script>
<script>
if (!window.Kakao) {
  console.error('Kakao SDK not loaded');
} else if (!Kakao.isInitialized()) {
  Kakao.init('""" + KAKAO_KEY + """');
  console.log('Kakao initialized:', Kakao.isInitialized());
}

function shareKakao() {
  if (!window.Kakao || !Kakao.isInitialized()) {
    alert('카카오 SDK 로딩 실패. 페이지를 새로고침 후 시도해주세요.');
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
}
</script>
</body>"""

if 'Kakao.Share' not in post:
    post = post.replace('</body>', kakao_script)
    repo.update_file(
        '_layouts/post.html',
        'fix: add shareKakao function to post.html',
        post,
        fp.sha,
        branch='main'
    )
    print('shareKakao 함수 추가 완료')
else:
    print('이미 존재 - 내용 확인 필요')
    lines = post.split('\n')
    for i, line in enumerate(lines):
        if 'kakao' in line.lower() or 'Kakao' in line:
            print(f'{i+1}: {line.strip()}')