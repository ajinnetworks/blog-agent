"""
fix_upload.py — 수정된 Gemfile과 deploy.yml을 GitHub에 강제 업데이트
실행: python fix_upload.py
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
    print("❌ GITHUB_TOKEN 미설정 — .env 파일 확인")
    sys.exit(1)

g = Github(token)
repo = g.get_repo(repo_name)

# 업데이트할 파일 목록
files_to_update = {
    "Gemfile": ROOT / "github_pages" / "Gemfile",
    ".github/workflows/deploy.yml": ROOT / "github_pages" / ".github" / "workflows" / "deploy.yml",
}

print(f"레포: {repo_name}")
print(f"브랜치: {branch}")
print()

for remote_path, local_path in files_to_update.items():
    content = local_path.read_bytes()
    try:
        existing = repo.get_contents(remote_path, ref=branch)
        repo.update_file(
            path=remote_path,
            message=f"fix: update {remote_path} for Jekyll build",
            content=content,
            sha=existing.sha,
            branch=branch,
        )
        print(f"✅ 업데이트: {remote_path}")
    except GithubException as e:
        if e.status == 404:
            repo.create_file(
                path=remote_path,
                message=f"fix: add {remote_path}",
                content=content,
                branch=branch,
            )
            print(f"✅ 새로 생성: {remote_path}")
        else:
            print(f"❌ 실패 {remote_path}: {e}")

print()
print("완료! GitHub Actions 탭에서 빌드 결과 확인:")
print(f"https://github.com/{repo_name}/actions")
