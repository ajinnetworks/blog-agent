"""
github_publisher.py — GitHub Pages 자동 커밋 발행 에이전트
Goal: 검수 완료 포스트를 Jekyll 마크다운으로 변환 후
      GitHub API를 통해 레포지토리에 자동 커밋 → GitHub Actions 빌드 트리거

의존성: PyGithub, python-frontmatter
설치: pip install PyGithub python-frontmatter
"""

import io
import json
import logging
import os
import re
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', errors='replace'
    )
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding='utf-8', errors='replace'
    )

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import frontmatter                  # python-frontmatter
from github import Auth, Github, GithubException, InputGitTreeElement   # PyGithub

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")


# ─── 설정 로드 ────────────────────────────────────────────────────────────────

from dotenv import load_dotenv
load_dotenv(override=True)

# 로컬: GITHUB_TOKEN / Actions: BLOG_GITHUB_TOKEN 통합
GITHUB_TOKEN = (
    os.getenv("BLOG_GITHUB_TOKEN") or
    os.getenv("GITHUB_TOKEN")
)

if not GITHUB_TOKEN:
    raise ValueError("GitHub 토큰 없음: BLOG_GITHUB_TOKEN 또는 GITHUB_TOKEN 필요")


def get_github_config() -> dict:
    """환경변수에서 GitHub 설정 읽기."""
    token = GITHUB_TOKEN
    repo_name = os.environ.get("GITHUB_REPO")          # 예: "username/username.github.io"
    branch = os.environ.get("GITHUB_BRANCH", "main")
    posts_path = os.environ.get("GITHUB_POSTS_PATH", "_posts")

    if not repo_name:
        raise EnvironmentError(
            "필수 환경변수 미설정: GITHUB_REPO\n"
            "config/.env.sample 참고 후 .env에 추가하세요."
        )

    return {
        "token": token,
        "repo_name": repo_name,
        "branch": branch,
        "posts_path": posts_path,
    }


# ─── 마크다운 변환 ────────────────────────────────────────────────────────────

def make_slug(title: str) -> str:
    """
    포스트 제목을 Jekyll URL-safe 슬러그로 변환.
    한글은 romanize 없이 그대로 사용 (GitHub Pages 한글 URL 지원).
    특수문자만 제거.
    """
    # 특수문자 제거, 공백을 하이픈으로
    slug = re.sub(r"[^\w\s가-힣-]", "", title)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = slug[:60]  # 최대 60자
    return slug


def post_to_jekyll_markdown(post: dict) -> tuple[str, str]:
    """
    에이전트 포스트 dict → Jekyll Front Matter + 본문 마크다운 변환.

    Returns:
        (file_name, markdown_content)
        file_name: "YYYY-MM-DD-slug.md"
    """
    now = datetime.now(KST)
    date_str = now.strftime("%Y-%m-%d")
    datetime_str = now.strftime("%Y-%m-%d %H:%M:%S +0900")

    title = post.get("title", "제목 없음")
    slug = make_slug(title)
    file_name = f"{date_str}-{slug}.md"

    # content 안전 변환
    raw_content = post.get("content", "")
    if isinstance(raw_content, list):
        safe_content = "\n\n".join(str(c) for c in raw_content)
    elif isinstance(raw_content, dict):
        safe_content = str(raw_content)
    else:
        safe_content = str(raw_content) if raw_content else ""
    safe_content = safe_content.encode("utf-8", errors="ignore").decode("utf-8")

    # Front Matter 구성
    meta = frontmatter.Post(
        content=safe_content,
        layout="post",
        title=title,
        date=datetime_str,
        categories=_parse_category(post.get("category", "기술")),
        tags=post.get("tags", [])[:10],
        description=post.get("meta_description", "")[:160],
        keywords=post.get("seo_keywords", []),
        author="AI Agent",
        # 검수 점수 메타로 기록 (독자에게 비표시)
        review_score=post.get("review_result", {}).get("total_score", 0),
        generated_at=post.get("generated_at", now.isoformat()),
    )

    # python-frontmatter 로 직렬화
    md_content = frontmatter.dumps(meta)

    # <!--more--> 태그 자동 삽입 (첫 단락 뒤)
    # 본문에 이미 있으면 생략
    if "<!--more-->" not in md_content:
        lines = md_content.split("\n")
        # Front Matter 끝(---) 이후 첫 빈 줄 찾기
        in_front = True
        dash_count = 0
        insert_idx = None
        for i, line in enumerate(lines):
            if line.strip() == "---":
                dash_count += 1
                if dash_count == 2:
                    in_front = False
                continue
            if not in_front and line.strip() == "" and insert_idx is None:
                insert_idx = i + 1  # 빈 줄 다음에 삽입

        if insert_idx and insert_idx < len(lines):
            lines.insert(insert_idx, "\n<!--more-->\n")
            md_content = "\n".join(lines)

    return file_name, md_content


def _parse_category(category_str: str) -> list[str]:
    """'기술/자동화' → ['기술', '자동화'] 변환."""
    if not category_str:
        return ["기술"]
    parts = re.split(r"[/,·]", category_str)
    return [p.strip() for p in parts if p.strip()][:3]


# ─── Human-in-the-loop Gate ──────────────────────────────────────────────────

def human_approval_gate(post: dict) -> bool:
    """HUMAN_GATE=true 시 발행 전 터미널 승인 요구."""
    if os.environ.get("HUMAN_GATE", "true").lower() != "true":
        return True

    print("\n" + "=" * 60)
    print("📋 GitHub Pages 발행 전 승인 요청")
    print("=" * 60)
    print(f"제목   : {post.get('title', 'N/A')}")
    print(f"카테고리: {post.get('category', 'N/A')}")
    print(f"태그   : {post.get('tags', [])}")
    score = post.get("review_result", {}).get("total_score", "N/A")
    print(f"검수점수: {score}/100")
    print(f"초안   : {post.get('draft_path', 'N/A')}")
    print("=" * 60)

    answer = input("GitHub Pages에 발행하시겠습니까? (y/n/skip): ").strip().lower()
    if answer == "y":
        logger.info(f"✅ 승인: '{post.get('title')}'")
        return True
    elif answer == "skip":
        logger.info(f"⏭️  스킵: '{post.get('title')}'")
        return False
    else:
        logger.info(f"❌ 거절: '{post.get('title')}'")
        return False


# ─── 발행 기록 저장 ───────────────────────────────────────────────────────────

def save_publish_record(post: dict, github_result: dict) -> str:
    """발행 완료 기록을 output/published/ 에 JSON으로 저장."""
    published_dir = ROOT / "output" / "published"
    published_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(KST).strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r"[^\w가-힣]", "_", post.get("title", "post"))[:30]

    record = {
        "published_at": datetime.now(KST).isoformat(),
        "platform": "github_pages",
        "title": post.get("title"),
        "file_name": github_result.get("file_name"),
        "file_path": github_result.get("file_path"),
        "commit_sha": github_result.get("commit_sha"),
        "commit_url": github_result.get("commit_url"),
        "blog_url": github_result.get("blog_url"),
        "review_score": post.get("review_result", {}).get("total_score"),
        "tags": post.get("tags", []),
        "word_count": post.get("word_count", 0),
    }

    record_path = published_dir / f"{timestamp}_{safe_title}.json"
    record_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"발행 기록 저장: {record_path}")
    return str(record_path)


# ─── 레포지토리 초기화 유틸 ──────────────────────────────────────────────────

def init_github_repo(config: dict, dry_run: bool = False) -> bool:
    """
    GitHub 레포지토리에 Jekyll 기본 파일이 없으면 자동으로 업로드.
    github_pages/ 폴더의 파일들을 레포지토리에 커밋.
    """
    if dry_run:
        print("[dry-run] GitHub 연결 생략 — init_github_repo 스킵")
        return None

    g = Github(auth=Auth.Token(config["token"]))
    repo = g.get_repo(config["repo_name"])
    branch = config["branch"]

    jekyll_dir = ROOT / "github_pages"
    if not jekyll_dir.exists():
        logger.warning("github_pages/ 폴더 없음 — 초기화 스킵")
        return False

    uploaded = []
    skipped = []

    for file_path in jekyll_dir.rglob("*"):
        if file_path.is_dir():
            continue
        # __pycache__ 등 제외
        if any(p in str(file_path) for p in ["__pycache__", ".pytest_cache"]):
            continue

        relative = str(file_path.relative_to(jekyll_dir))
        content = file_path.read_bytes()

        try:
            existing = repo.get_contents(relative, ref=branch)
            # 이미 존재하면 스킵 (강제 덮어쓰기 원하면 update_file 사용)
            skipped.append(relative)
        except GithubException as e:
            if e.status == 404:
                try:
                    repo.create_file(
                        path=relative,
                        message=f"init: add {relative}",
                        content=content,
                        branch=branch,
                    )
                    uploaded.append(relative)
                    logger.info(f"  업로드: {relative}")
                except Exception as upload_err:
                    logger.error(f"  업로드 실패 {relative}: {upload_err}")
            else:
                logger.error(f"  확인 실패 {relative}: {e}")

    logger.info(f"레포 초기화: {len(uploaded)}개 업로드, {len(skipped)}개 스킵")
    return True


# ─── 메인 발행 함수 ───────────────────────────────────────────────────────────

def run_github_publisher(posts: list[dict], dry_run: bool = False) -> list[dict]:
    """
    검수 완료 포스트 리스트를 GitHub Pages에 단일 커밋으로 일괄 발행.

    Args:
        posts:   reviewer_agent에서 반환된 포스트 리스트
        dry_run: True이면 마크다운 변환까지만 수행, GitHub 커밋 차단

    Returns:
        발행 결과 리스트
    """
    logger.info("=== GitHub Pages Publisher 시작 ===" + (" [DRY-RUN]" if dry_run else ""))

    if not posts:
        print("[WARN] 발행할 포스트 없음")
        return []

    # 환경변수 확인
    try:
        config = get_github_config()
    except EnvironmentError as e:
        logger.error(str(e))
        return [{"error": str(e), "platform": "github_pages"}]

    # STEP 1: 필터링 + 마크다운 변환
    ready_files = []

    for post in posts:
        if post.get("error"):
            logger.warning(f"오류 포스트 스킵: {post.get('title')}")
            continue

        if not post.get("review_result", {}).get("pass"):
            score = post.get("review_result", {}).get("total_score", 0)
            logger.warning(f"검수 미합격 스킵: '{post.get('title')}' (점수: {score})")
            continue

        if not human_approval_gate(post):
            logger.info(f"사용자 거절/스킵: '{post.get('title')}'")
            continue

        file_name, md_content = post_to_jekyll_markdown(post)
        file_path = f"{config['posts_path']}/{file_name}"
        logger.info(f"마크다운 변환 완료: {file_name} ({len(md_content)}자)")
        ready_files.append({
            "file_path": file_path,
            "file_name": file_name,
            "content": md_content,
            "post": post,
        })

    if not ready_files:
        print("[WARN] 커밋할 파일 없음")
        return [{"error": "발행 대상 없음", "platform": "github_pages"}]

    # STEP 2: dry-run 차단
    if dry_run:
        results = []
        for f in ready_files:
            logger.info(f"[dry-run] 커밋 차단: {f['file_path']}")
            print(f"[DRY-RUN] {f['post'].get('title', '')}: {f['file_path']}")
            result = {
                "file_path": f["file_path"],
                "file_name": f["file_name"],
                "commit_sha": "dry-run-no-commit",
                "commit_url": "(dry-run)",
                "blog_url": "(dry-run)",
                "action": "dry-run",
            }
            save_publish_record(f["post"], result)
            results.append(result)
        logger.info(f"GitHub Pages Publisher 완료: {len(results)}/{len(posts)}개 (dry-run)")
        return results

    # STEP 3: Git Tree API 일괄 커밋
    today = datetime.now(KST).strftime("%Y-%m-%d")

    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(config["repo_name"])

    ref = repo.get_git_ref(f"heads/{config['branch']}")
    base_tree = repo.get_git_tree(ref.object.sha)

    tree_elements = []
    for f in ready_files:
        blob = repo.create_git_blob(f["content"], "utf-8")
        tree_elements.append(InputGitTreeElement(
            path=f["file_path"],
            mode="100644",
            type="blob",
            sha=blob.sha,
        ))

    if not tree_elements:
        print("[WARN] 커밋할 파일 없음")
        return [{"error": "tree_elements 비어있음", "platform": "github_pages"}]

    commit_msg = (
        f"docs: auto-post {len(ready_files)}개 포스트 발행 ({today})\n\n"
        + "\n".join(f"- {f['file_name']}" for f in ready_files)
    )

    try:
        new_tree = repo.create_git_tree(tree_elements, base_tree)
        parent = repo.get_git_commit(ref.object.sha)
        new_commit = repo.create_git_commit(commit_msg, new_tree, [parent])
        ref.edit(new_commit.sha)
    except GithubException as e:
        logger.error(f"일괄 커밋 실패: {e.status} {e.data}")
        return [{"error": f"GitHub API {e.status}: {e.data}", "platform": "github_pages"}]
    except Exception as e:
        logger.error(f"일괄 커밋 실패: {e}")
        return [{"error": str(e), "platform": "github_pages"}]

    commit_sha = new_commit.sha
    username = config["repo_name"].split("/")[0]
    blog_url = f"https://{username}.github.io"
    commit_url = f"https://github.com/{config['repo_name']}/commit/{commit_sha}"

    print(f"[SUCCESS] {len(ready_files)}개 포스트 일괄 커밋: {commit_sha[:7]}")
    print(f"   커밋   : {commit_url}")
    print(f"   블로그 : {blog_url}")
    for f in ready_files:
        print(f"   - {f['file_name']}")
    print(f"   ※ GitHub Actions 빌드 후 1~3분 내 반영됩니다.")

    # STEP 4: 결과 구성 + 발행 기록 저장
    results = []
    for f in ready_files:
        result = {
            "file_path": f["file_path"],
            "file_name": f["file_name"],
            "commit_sha": commit_sha,
            "commit_url": commit_url,
            "blog_url": blog_url,
            "action": "일괄 커밋",
        }
        save_publish_record(f["post"], result)
        results.append(result)

    logger.info(f"GitHub Pages Publisher 완료: {len(results)}/{len(posts)}개 발행")
    return results


if __name__ == "__main__":
    import sys as _sys
    logging.basicConfig(level=logging.INFO)
    dry_run = "--dry-run" in _sys.argv

    print("GitHub Pages Publisher - 환경변수 확인")
    try:
        cfg = get_github_config()
        print(f"  repo     : {cfg['repo_name']}")
        print(f"  branch   : {cfg['branch']}")
        print(f"  dry-run  : {dry_run}")
        print("  [OK] 환경변수 확인 완료")
    except EnvironmentError as e:
        print(f"  [ERROR] {e}")
        _sys.exit(1)

    if dry_run:
        print()
        print("[dry-run] 샘플 포스트 1건으로 publish 경로 테스트")
        sample = [{
            "title": "dry-run 테스트 포스트",
            "content": "# 테스트\n\nDry-run 확인용 포스트입니다.",
            "category": "스마트팩토리",
            "tags": ["테스트"],
            "filename": "2099-01-01-dry-run-test.md",
            "review_result": {"pass": True, "total_score": 100},
        }]
        results = run_github_publisher(sample, dry_run=True)
        for r in results:
            print(f"  status : {r.get('github_status', 'unknown')}")
            print(f"  path   : {r.get('github_path', '-')}")
    else:
        print()
        print("단독 실행 시에는 --dry-run 옵션을 사용하거나 run_agent.py 를 통해 실행하세요.")
