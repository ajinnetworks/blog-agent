from github import Auth, Github
from dotenv import load_dotenv
import os

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

f = repo.get_contents('_layouts/home.html', ref='main')
home = f.decoded_content.decode('utf-8')

home = home.replace("function filterPosts(cat) {", "function filterPosts(cat, btn) {")
home = home.replace("  event.target.classList.add('active');", "  if (btn) btn.classList.add('active');")
home = home.replace('onclick="filterPosts(\'all\')"', 'onclick="filterPosts(\'all\', this)"')
home = home.replace("onclick=\"filterPosts('{{ cat_clean }}')\"", "onclick=\"filterPosts('{{ cat_clean }}', this)\"")

repo.update_file('_layouts/home.html', 'fix: filterPosts', home, f.sha, branch='main')
print('완료')
print('함수수정:', 'filterPosts(cat, btn)' in home)
print('event제거:', 'event.target' not in home)