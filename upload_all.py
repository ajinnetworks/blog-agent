"""
upload_all.py — 디자인 파일 전체 GitHub 업로드
"""
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from github import Github, GithubException

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env", override=True)

token = os.environ.get("GITHUB_TOKEN")
repo_name = "ajinnetworks/ajinnetworks.github.io"
branch = "main"

if not token:
    print("❌ GITHUB_TOKEN 미설정")
    sys.exit(1)

g = Github(token)
repo = g.get_repo(repo_name)

files = {
    "_config.yml": ROOT / "github_pages" / "_config.yml",
    "assets/css/style.scss": ROOT / "github_pages" / "assets" / "css" / "style.scss",
    "_layouts/home.html": ROOT / "github_pages" / "_layouts" / "home.html",
}

for remote, local in files.items():
    if not local.exists():
        print(f"⚠️  파일 없음: {local}")
        continue
    content = local.read_bytes()
    try:
        existing = repo.get_contents(remote, ref=branch)
        repo.update_file(remote, f"design: update {remote}", content, existing.sha, branch=branch)
        print(f"✅ 업데이트: {remote}")
    except GithubException as e:
        if e.status == 404:
            repo.create_file(remote, f"design: add {remote}", content, branch=branch)
            print(f"✅ 생성: {remote}")
        else:
            print(f"❌ 실패 {remote}: {e}")

print("\n완료! 1~3분 후 블로그 확인:")
print("https://ajinnetworks.github.io")
