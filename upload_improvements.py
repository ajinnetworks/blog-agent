"""
upload_improvements.py — 개선사항 전체 GitHub 업로드
"""
import os, sys
from pathlib import Path
from github import Github, GithubException

ROOT = Path(__file__).parent

token = os.environ.get("GITHUB_TOKEN")
if not token:
    print("❌ GITHUB_TOKEN 환경변수 미설정")
    print("실행: $env:GITHUB_TOKEN = '토큰값'")
    sys.exit(1)

g = Github(token)
repo = g.get_repo("ajinnetworks/ajinnetworks.github.io")
branch = "main"

files = {
    "_includes/head.html": ROOT / "github_pages" / "_includes" / "head.html",
    "_layouts/post.html":  ROOT / "github_pages" / "_layouts" / "post.html",
    "_layouts/home.html":  ROOT / "github_pages" / "_layouts" / "home.html",
    "agents/reviewer_agent.py": ROOT / "agents" / "reviewer_agent.py",
    "agents/github_publisher.py": ROOT / "agents" / "github_publisher.py",
    "prompts/writer_prompt.md": ROOT / "prompts" / "writer_prompt.md",
}

print(f"GitHub 업로드 시작: {len(files)}개 파일")
print()

success = 0
for remote, local in files.items():
    if not local.exists():
        print(f"⚠️  파일 없음: {local}")
        continue
    content = local.read_bytes()
    try:
        existing = repo.get_contents(remote, ref=branch)
        repo.update_file(remote, f"improve: update {remote}", content, existing.sha, branch=branch)
        print(f"✅ 업데이트: {remote}")
        success += 1
    except GithubException as e:
        if e.status == 404:
            repo.create_file(remote, f"improve: add {remote}", content, branch=branch)
            print(f"✅ 생성: {remote}")
            success += 1
        else:
            print(f"❌ 실패 {remote}: {e}")

print(f"\n완료: {success}/{len(files)}개 업로드")
print("\n개선 내용:")
print("  ✅ 포스트 상세 레이아웃 (히어로 헤더 + 카드 본문 + CTA)")
print("  ✅ SEO 메타태그 (OG, Twitter Card)")
print("  ✅ 이미지 자동 삽입 (Unsplash 무료 이미지)")
print("  ✅ 포스트 태그 섹션")
print("  ✅ 회사 CTA 섹션")
print("  ✅ 목록으로 돌아가기 버튼")
print("\n2~3분 후 확인: https://ajinnetworks.github.io")
