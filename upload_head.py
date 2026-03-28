"""upload_head.py — head.html 업로드"""
import os
from pathlib import Path
from dotenv import load_dotenv
from github import Github, GithubException

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env", override=True)
g = Github(os.environ["GITHUB_TOKEN"])
repo = g.get_repo("ajinnetworks/ajinnetworks.github.io")

files = {
    "_includes/head.html": ROOT / "github_pages" / "_includes" / "head.html",
    "_layouts/home.html": ROOT / "github_pages" / "_layouts" / "home.html",
    "assets/css/style.scss": ROOT / "github_pages" / "assets" / "css" / "style.scss",
}

for remote, local in files.items():
    content = local.read_bytes()
    try:
        existing = repo.get_contents(remote, ref="main")
        repo.update_file(remote, f"design: update {remote}", content, existing.sha, branch="main")
        print(f"✅ 업데이트: {remote}")
    except GithubException as e:
        if e.status == 404:
            repo.create_file(remote, f"design: add {remote}", content, branch="main")
            print(f"✅ 생성: {remote}")
        else:
            print(f"❌ {remote}: {e}")

print("\n완료! 2~3분 후 확인: https://ajinnetworks.github.io")
