"""upload_final.py — 최종 고급 기능 업로드"""
import os, sys
from pathlib import Path
from github import Github, GithubException

ROOT = Path(__file__).parent
token = os.environ.get("GITHUB_TOKEN")
if not token:
    print("❌ $env:GITHUB_TOKEN 설정 필요")
    sys.exit(1)

g = Github(token)
repo = g.get_repo("ajinnetworks/ajinnetworks.github.io")
branch = "main"

files = {
    "_includes/head.html": ROOT / "github_pages" / "_includes" / "head.html",
    "_layouts/home.html":  ROOT / "github_pages" / "_layouts" / "home.html",
    "_layouts/post.html":  ROOT / "github_pages" / "_layouts" / "post.html",
}

print("최종 고급 기능 업로드")
print()
success = 0
for remote, local in files.items():
    if not local.exists():
        print(f"⚠️ 없음: {local}")
        continue
    content = local.read_bytes()
    try:
        existing = repo.get_contents(remote, ref=branch)
        repo.update_file(remote, f"feat: advanced blog {remote}", content, existing.sha, branch=branch)
        print(f"✅ {remote}")
        success += 1
    except GithubException as e:
        if e.status == 404:
            repo.create_file(remote, f"feat: add {remote}", content, branch=branch)
            print(f"✅ {remote} (신규)")
            success += 1
        else:
            print(f"❌ {remote}: {e}")

print(f"\n{success}/{len(files)} 완료")
print("\n추가된 고급 기능:")
print("  ✅ 헤더 □ 깨진 문자 제거")
print("  ✅ 읽기 진행 바 (상단 파란 바)")
print("  ✅ 상단으로 버튼 (우측 하단)")
print("  ✅ 목차 자동 생성 (TOC)")
print("  ✅ 읽기 시간 자동 계산")
print("  ✅ 카테고리 필터 (클릭으로 필터링)")
print("  ✅ 검색 기능 (Ctrl+K)")
print("  ✅ 포스트 통계 바")
print("  ✅ Twitter/LinkedIn/URL 공유 버튼")
print("  ✅ 관련 포스트 섹션")
print("  ✅ 회사 CTA 카드")
print("\n2~3분 후: https://ajinnetworks.github.io")
