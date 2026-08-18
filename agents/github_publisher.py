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


def _clean_secret(value: str | None) -> str:
    """Actions/ENV secret에 섞인 선행·후행 공백/개행을 제거한다."""
    return (value or "").strip()


# 로컬: GITHUB_TOKEN / Actions: BLOG_GITHUB_TOKEN 통합
GITHUB_TOKEN = _clean_secret(
    os.getenv("BLOG_GITHUB_TOKEN") or
    os.getenv("GITHUB_TOKEN")
)

if not GITHUB_TOKEN:
    raise ValueError("GitHub 토큰 없음: BLOG_GITHUB_TOKEN 또는 GITHUB_TOKEN 필요")


def get_github_config() -> dict:
    """환경변수에서 GitHub 설정 읽기."""
    token = _clean_secret(GITHUB_TOKEN)
    repo_name = _clean_secret(os.environ.get("BLOG_REPO") or os.environ.get("GITHUB_REPO"))
    branch = _clean_secret(os.environ.get("GITHUB_BRANCH", "main")) or "main"
    posts_path = _clean_secret(os.environ.get("GITHUB_POSTS_PATH", "_posts")) or "_posts"

    if not repo_name:
        raise EnvironmentError(
            "필수 환경변수 미설정: BLOG_REPO\n"
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
    slug = re.sub(r"[^\w\s가-힣-]", "", title)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = slug[:60]
    return slug


def post_to_jekyll_markdown(post: dict) -> tuple[str, str]:
    now = datetime.now(KST)
    date_str = now.strftime("%Y-%m-%d")
    datetime_str = now.strftime("%Y-%m-%d %H:%M:%S +0900")

    title = post.get("title", "제목 없음")
    slug = make_slug(title)
    file_name = f"{date_str}-{slug}.md"

    raw_content = post.get("content", "")
    if isinstance(raw_content, list):
        safe_content = "\n\n".join(str(c) for c in raw_content)
    elif isinstance(raw_content, dict):
        safe_content = str(raw_content)
    else:
        safe_content = str(raw_content) if raw_content else ""
    safe_content = safe_content.encode("utf-8", errors="ignore").decode("utf-8")

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
        review_score=post.get("review_result", {}).get("total_score", 0),
        generated_at=post.get("generated_at", now.isoformat()),
    )

    md_content = frontmatter.dumps(meta)

    if "<!--more-->" not in md_content:
        lines = md_content.split("\n")
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
                insert_idx = i + 1

        if insert_idx and insert_idx < len(lines):
            lines.insert(insert_idx, "\n<!--more-->\n")
            md_content = "\n".join(lines)

    return file_name, md_content


def _parse_category(category_str: str) -> list[str]:
    if not category_str:
        return ["기술"]
    parts = re.split(r"[/,·]", category_str)
    return [p.strip() for p in parts if p.strip()][:3]


def human_approval_gate(post: dict) -> bool:
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


def save_publish_record(post: dict, github_result: dict) -> str:
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


def init_github_repo(config: dict, dry_run: bool = False) -> bool:
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
        if any(p in str(file_path) for p in ["__pycache__", ".pytest_cache"]):
            continue

        rel_path = file_path.relative_to(jekyll_dir).as_posix()
        content = file_path.read_text(encoding="utf-8")
        try:
            repo.get_contents(rel_path, ref=branch)
            skipped.append(rel_path)
        except GithubException as e:
            if e.status == 404:
                repo.create_file(rel_path, f"Initialize {rel_path}", content, branch=branch)
                uploaded.append(rel_path)
            else:
                raise

    logger.info("GitHub repo init: uploaded=%s skipped=%s", uploaded, skipped)
    return True


def _build_blog_url(repo_name: str, file_name: str) -> str:
    owner, repo = repo_name.split("/", 1)
    slug = file_name[:-3]
    parts = slug.split("-", 3)
    if len(parts) >= 4:
        yyyy, mm, dd, title_slug = parts
        return f"https://{owner}.github.io/{yyyy}/{mm}/{dd}/{title_slug}.html"
    return f"https://{owner}.github.io"


def publish_post_to_github(post: dict, config: dict, dry_run: bool = False) -> dict:
    file_name, md_content = post_to_jekyll_markdown(post)
    file_path = f"{config['posts_path'].rstrip('/')}/{file_name}"

    if dry_run:
        logger.info("[DRY-RUN] GitHub commit blocked: %s", file_path)
        return {
            "file_name": file_name,
            "file_path": file_path,
            "commit_url": "(dry-run)",
            "blog_url": "(dry-run)",
        }

    if not human_approval_gate(post):
        return {"error": "human approval rejected", "file_name": file_name, "file_path": file_path}

    g = Github(auth=Auth.Token(_clean_secret(config["token"])))
    repo = g.get_repo(config["repo_name"])
    branch = config["branch"]

    try:
        existing = repo.get_contents(file_path, ref=branch)
        return {"error": f"duplicate file exists: {file_path}", "file_name": file_name, "file_path": file_path}
    except GithubException as e:
        if e.status != 404:
            raise

    result = repo.create_file(
        file_path,
        f"Publish: {post.get('title', file_name)}",
        md_content,
        branch=branch,
    )

    commit = result.get("commit")
    commit_sha = getattr(commit, "sha", None)
    commit_url = getattr(commit, "html_url", None)
    blog_url = _build_blog_url(config["repo_name"], file_name)

    github_result = {
        "file_name": file_name,
        "file_path": file_path,
        "commit_sha": commit_sha,
        "commit_url": commit_url,
        "blog_url": blog_url,
    }
    save_publish_record(post, github_result)
    return github_result


def run_github_publisher(posts: list[dict], dry_run: bool = False) -> list[dict]:
    config = get_github_config()
    results = []
    for post in posts:
        try:
            results.append(publish_post_to_github(post, config, dry_run=dry_run))
        except Exception as exc:
            logger.exception("GitHub publish failed: %s", exc)
            results.append({"error": str(exc), "title": post.get("title")})
    return results
