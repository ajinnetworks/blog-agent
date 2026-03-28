"""
upload_design.py — 디자인 파일 + 자동화 워크플로우 GitHub 업로드
실행: python upload_design.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from github import Github, GithubException

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env", override=True)

token = os.environ.get("GITHUB_TOKEN")
repo_name = os.environ.get("GITHUB_REPO", "ajinnetworks/ajinnetworks.github.io")
branch = os.environ.get("GITHUB_BRANCH", "main")

if not token:
    print("❌ GITHUB_TOKEN 미설정")
    sys.exit(1)

g = Github(token)
repo = g.get_repo(repo_name)

# 업로드할 파일 목록
files = {
    "assets/css/style.scss": ROOT / "github_pages" / "assets" / "css" / "style.scss",
    ".github/workflows/auto-post.yml": ROOT / "github_pages" / ".github" / "workflows" / "auto-post.yml",
}

print(f"레포: {repo_name}")
print()

for remote_path, local_path in files.items():
    if not local_path.exists():
        print(f"⚠️  파일 없음: {local_path}")
        continue

    content = local_path.read_bytes()

    try:
        existing = repo.get_contents(remote_path, ref=branch)
        repo.update_file(
            path=remote_path,
            message=f"design: update {remote_path}",
            content=content,
            sha=existing.sha,
            branch=branch,
        )
        print(f"✅ 업데이트: {remote_path}")
    except GithubException as e:
        if e.status == 404:
            repo.create_file(
                path=remote_path,
                message=f"design: add {remote_path}",
                content=content,
                branch=branch,
            )
            print(f"✅ 새로 생성: {remote_path}")
        else:
            print(f"❌ 실패 {remote_path}: {e}")

print()
print("완료!")
print()
print("다음 단계:")
print("1. GitHub Secrets 설정:")
print(f"   https://github.com/{repo_name}/settings/secrets/actions")
print("   → ANTHROPIC_API_KEY: Anthropic API 키")
print("   → BLOG_GITHUB_TOKEN: GitHub Personal Access Token")
print()
print("2. 블로그 확인:")
print("   https://ajinnetworks.github.io")
