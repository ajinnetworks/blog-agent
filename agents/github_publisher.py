"""
github_publisher.py — GitHub Pages 자동 커밋 발행 에이전트
Goal: 검수 완료 포스트를 Jekyll 마크다운으로 변환 후
      GitHub API를 통해 레포지토리에 자동 커밋 → GitHub Actions 빌드 트리거

의존성: PyGithub, python-frontmatter
설치: pip install PyGithub python-frontmatter
"""

import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import frontmatter                  # python-frontmatter
from github import Github, GithubException   # PyGithub

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")


# ─── 설정 로드 ────────────────────────────────────────────────────────────────

def get_github_config() -> dict:
    """환경변수에서 GitHub 설정 읽기."""
    token = os.environ.get("GITHUB_TOKEN")
    repo_name = os.environ.get("GITHUB_REPO")          # 예: "username/username.github.io"
    branch = os.environ.get("GITHUB_BRANCH", "main")
    posts_path = os.environ.get("GITHUB_POSTS_PATH", "_posts")

    missing = []
    if not token:
        missing.append("GITHUB_TOKEN")
    if not repo_name:
        missing.append("GITHUB_REPO")

    if missing:
        raise EnvironmentError(
            f"필수 환경변수 미설정: {missing}\n"
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


# ─── GitHub 커밋 ──────────────────────────────────────────────────────────────

def commit_post_to_github(
    file_name: str,
    md_content: str,
    config: dict,
    commit_message: str = None,
) -> dict:
    """
    GitHub API를 통해 _posts/ 에 마크다운 파일 커밋.

    Returns:
        { file_path, commit_sha, html_url, blog_url }
    """
    g = Github(config["token"])
    repo = g.get_repo(config["repo_name"])
    branch = config["branch"]
    posts_path = config["posts_path"]

    file_path = f"{posts_path}/{file_name}"
    commit_msg = commit_message or f"docs: auto-post '{file_name}' via AI agent"

    logger.info(f"GitHub 커밋 시도: {config['repo_name']}/{file_path}")

    try:
        # 동일 파일이 이미 존재하는지 확인 (업데이트 vs 신규)
        existing = repo.get_contents(file_path, ref=branch)
        result = repo.update_file(
            path=file_path,
            message=commit_msg,
            content=md_content.encode("utf-8"),
            sha=existing.sha,
            branch=branch,
        )
        action = "업데이트"
    except GithubException as e:
        if e.status == 404:
            # 신규 파일 생성
            result = repo.create_file(
                path=file_path,
                message=commit_msg,
                content=md_content.encode("utf-8"),
                branch=branch,
            )
            action = "신규 생성"
        else:
            raise

    commit_sha = result["commit"].sha
    # GitHub Pages URL 구성 (추측입니다 — 레포 설정에 따라 다를 수 있음)
    username = config["repo_name"].split("/")[0]
    blog_url = f"https://{username}.github.io"

    logger.info(f"✅ 커밋 {action} 완료: {file_path} (sha: {commit_sha[:8]})")
    return {
        "file_path": file_path,
        "file_name": file_name,
        "commit_sha": commit_sha,
        "commit_url": f"https://github.com/{config['repo_name']}/commit/{commit_sha}",
        "blog_url": blog_url,
        "action": action,
    }


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

def init_github_repo(config: dict) -> bool:
    """
    GitHub 레포지토리에 Jekyll 기본 파일이 없으면 자동으로 업로드.
    github_pages/ 폴더의 파일들을 레포지토리에 커밋.
    """
    g = Github(config["token"])
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

def run_github_publisher(posts: list[dict]) -> list[dict]:
    """
    검수 완료 포스트 리스트를 GitHub Pages에 발행.

    Args:
        posts: reviewer_agent에서 반환된 포스트 리스트

    Returns:
        발행 결과 리스트
    """
    logger.info("=== GitHub Pages Publisher 시작 ===")

    # 환경변수 확인
    try:
        config = get_github_config()
    except EnvironmentError as e:
        logger.error(str(e))
        return [{"error": str(e), "platform": "github_pages"}]

    results = []

    for post in posts:
        # 오류 포스트 스킵
        if post.get("error"):
            logger.warning(f"오류 포스트 스킵: {post.get('title')}")
            continue

        # 검수 미합격 스킵
        if not post.get("review_result", {}).get("pass"):
            score = post.get("review_result", {}).get("total_score", 0)
            logger.warning(
                f"검수 미합격 스킵: '{post.get('title')}' (점수: {score})"
            )
            continue

        # Human-in-the-loop 게이트
        if not human_approval_gate(post):
            logger.info(f"사용자 거절/스킵: '{post.get('title')}'")
            continue

        try:
            # 마크다운 변환
            file_name, md_content = post_to_jekyll_markdown(post)
            logger.info(f"마크다운 변환 완료: {file_name} ({len(md_content)}자)")

            # GitHub 커밋
            github_result = commit_post_to_github(
                file_name=file_name,
                md_content=md_content,
                config=config,
            )

            # 발행 기록 저장
            record_path = save_publish_record(post, github_result)
            github_result["record_path"] = record_path

            results.append(github_result)

            print(f"\n🎉 발행 완료!")
            print(f"   파일   : {github_result['file_path']}")
            print(f"   커밋   : {github_result['commit_url']}")
            print(f"   블로그 : {github_result['blog_url']}")
            print(f"   ※ GitHub Actions 빌드 후 1~3분 내 반영됩니다.")

        except GithubException as e:
            logger.error(f"GitHub API 오류 '{post.get('title')}': {e.status} {e.data}")
            results.append({
                "title": post.get("title"),
                "error": f"GitHub API {e.status}: {e.data}",
                "platform": "github_pages",
            })
        except Exception as e:
            logger.error(f"발행 실패 '{post.get('title')}': {e}")
            results.append({
                "title": post.get("title"),
                "error": str(e),
                "platform": "github_pages",
            })

    success = len([r for r in results if not r.get("error")])
    logger.info(f"GitHub Pages Publisher 완료: {success}/{len(posts)}개 발행")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("GitHub Pages Publisher — 단독 실행은 run_agent.py를 통해 사용하세요.")
    print("레포 초기화 테스트:")
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env", override=True)
        cfg = get_github_config()
        print(f"  레포: {cfg['repo_name']}")
        print(f"  브랜치: {cfg['branch']}")
        print("  ✅ 환경변수 확인 완료")
    except EnvironmentError as e:
        print(f"  ❌ {e}")
