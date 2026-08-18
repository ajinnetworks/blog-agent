"""
run_agent.py — 블로그 자동화 에이전트 메인 진입점
Goal → Work → Result 3-tier 오케스트레이션
"""

import argparse
import io
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.trend_agent import run_trend_agent
from agents.writer_agent import run_writer_agent
from agents.content_enricher import enrich_posts
from agents.reviewer_agent import run_reviewer_agent
from agents.content_quality import apply_final_content_gate
from agents.image_selector import assign_batch_images
from agents.publisher_agent import run_publisher_agent
from agents.github_publisher import run_github_publisher, init_github_repo, get_github_config
from agents.publisher_image_bridge import install as install_image_publisher
from agents.recent_topic_guard import guard_and_refill_topics
from agents.tag_policy import normalize_posts_tags

install_image_publisher()

load_dotenv(ROOT / ".env", override=True)

log_level = os.environ.get("LOG_LEVEL", "INFO")
_log_dir = ROOT / "output" / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_log_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("run_agent")


def validate_env(platform: str = "github") -> bool:
    """Validate only hard requirements.

    LLM keys are optional because agents.llm_fallback has a deterministic
    Ajin industrial safe-mode when Gemini/Claude are unavailable.
    """
    required = []
    if platform == "github":
        required += ["BLOG_GITHUB_TOKEN", "BLOG_REPO"]
    elif platform == "wordpress":
        required += ["WORDPRESS_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]

    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        logger.error("필수 환경변수 미설정: %s", missing)
        logger.error("config/.env.sample 참고 후 .env에 입력하세요.")
        return False

    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("외부 LLM 키 없음 -> 아진네트웍스 deterministic safe-mode로 실행")
    return True


def run_full_pipeline(dry_run: bool = False, topic_override: str = None, platform: str = "github") -> dict:
    start_time = datetime.now()
    platform_label = {"github": "GitHub Pages", "wordpress": "WordPress"}.get(platform, platform)

    logger.info("=" * 60)
    logger.info("Blog Agent 시작: %s", start_time.strftime('%Y-%m-%d %H:%M:%S'))
    logger.info("플랫폼: %s | 모드: %s", platform_label, 'DRY-RUN' if dry_run else '실제 발행')
    logger.info("=" * 60)

    result_summary = {"run_at": start_time.isoformat(), "platform": platform, "dry_run": dry_run, "stages": {}}

    logger.info("\n[STAGE 1] 트렌드 수집 & 주제 선정")
    if topic_override:
        topics = [{"keyword": topic_override, "angle": f"{topic_override} 실용 분석", "reason": "수동 지정", "estimated_search_volume": "unknown"}]
    else:
        topics = run_trend_agent()
        guard_days = int(os.environ.get("RECENT_TOPIC_DAYS", "60"))
        guard_threshold = float(os.environ.get("RECENT_TOPIC_THRESHOLD", "0.62"))
        topics, duplicate_topics = guard_and_refill_topics(
            topics,
            days=guard_days,
            threshold=guard_threshold,
            target_count=3,
        )
        result_summary["stages"]["recent_topic_guard"] = {
            "days": guard_days,
            "threshold": guard_threshold,
            "accepted": len(topics),
            "rejected": len(duplicate_topics),
            "duplicates": duplicate_topics,
        }
        logger.info("[TOPIC-GUARD] final=%s rejected=%s", len(topics), len(duplicate_topics))

    if not topics:
        raise RuntimeError("주제 선정 결과가 0개입니다. Trend/Safe-mode 로그를 확인하세요.")

    result_summary["stages"]["trend"] = {"count": len(topics), "topics": [t["keyword"] for t in topics]}
    logger.info("선정 주제: %s", [t['keyword'] for t in topics])

    logger.info("\n[STAGE 2] 포스트 작성")
    posts = run_writer_agent(topics)
    posts = enrich_posts(posts)
    posts = normalize_posts_tags(posts)
    result_summary["stages"]["writer"] = {
        "attempted": len(topics),
        "succeeded": sum(1 for p in posts if not p.get("error")),
        "enriched": sum(1 for p in posts if p.get("content_enriched")),
    }
    logger.info("기술본문 보강: %s개", result_summary['stages']['writer']['enriched'])

    if not posts:
        raise RuntimeError("Writer 결과가 0개입니다. LLM/Safe-mode 로그를 확인하세요.")

    logger.info("\n[STAGE 3] 품질 검수")
    reviewed_posts = run_reviewer_agent(posts)
    passed = [p for p in reviewed_posts if p.get("review_result", {}).get("pass")]
    result_summary["stages"]["reviewer"] = {
        "total": len(reviewed_posts),
        "passed": len(passed),
        "scores": [p.get("review_result", {}).get("total_score") for p in reviewed_posts],
    }

    logger.info("\n[STAGE 4] 이미지 배정 & Final Content Gate")
    reviewed_posts = assign_batch_images(reviewed_posts)
    reviewed_posts = apply_final_content_gate(reviewed_posts)
    final_ready = [p for p in reviewed_posts if p.get("final_quality", {}).get("pass")]
    for post in reviewed_posts:
        fq = post.get("final_quality", {})
        if fq.get("pass"):
            logger.info(
                "[FINAL-GATE] PASS: '%s' | %s자 | 기술어 %s개 | image=%s",
                post.get("title"), fq.get("content_chars"), len(fq.get("technical_hits", [])), post.get("image")
            )
        else:
            logger.warning("[FINAL-GATE] FAIL: '%s' | %s", post.get("title"), fq.get("issues"))

    result_summary["stages"]["final_quality"] = {
        "total": len(reviewed_posts),
        "passed": len(final_ready),
        "images": [p.get("image") for p in final_ready],
        "issues": {p.get("title", "N/A"): p.get("final_quality", {}).get("issues", []) for p in reviewed_posts if not p.get("final_quality", {}).get("pass")},
    }

    if not final_ready:
        raise RuntimeError("Final Content Gate 합격 포스트가 0개입니다. 품질 이슈를 수정한 뒤 재실행하세요.")

    logger.info("\n[STAGE 5] 발행 → %s%s", platform_label, " [DRY-RUN]" if dry_run else "")
    if platform == "github":
        publish_results = run_github_publisher(final_ready, dry_run=dry_run)
        result_summary["stages"]["publisher"] = {
            "platform": "github_pages",
            "dry_run": dry_run,
            "published": len([r for r in publish_results if not r.get("error")]),
            "failed": len([r for r in publish_results if r.get("error")]),
            "commit_urls": [r.get("commit_url") for r in publish_results if r.get("commit_url") and r.get("commit_url") != "(dry-run)"],
            "blog_url": next((r.get("blog_url") for r in publish_results if r.get("blog_url") and r.get("blog_url") != "(dry-run)"), None),
        }
    else:
        publish_results = run_publisher_agent(final_ready)
        result_summary["stages"]["publisher"] = {
            "platform": platform,
            "dry_run": dry_run,
            "published": len([r for r in publish_results if not r.get("error")]),
            "failed": len([r for r in publish_results if r.get("error")]),
            "urls": [r.get("url") for r in publish_results if r.get("url")],
        }

    pub = result_summary["stages"].get("publisher", {})
    if not dry_run and pub.get("published", 0) == 0:
        raise RuntimeError("발행 성공 0개입니다. GitHub token/repo 권한 및 Publisher 로그를 확인하세요.")
    if pub.get("failed", 0):
        logger.error("부분 발행 실패: %s개. 성공한 포스트 재발행 방지를 위해 자동 재시도하지 않습니다.", pub["failed"])

    elapsed = (datetime.now() - start_time).total_seconds()
    result_summary["elapsed_seconds"] = round(elapsed, 1)
    summary_path = _log_dir / f"summary_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
    summary_path.write_text(json.dumps(result_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("\n" + "=" * 60)
    logger.info("  플랫폼: %s", platform_label)
    logger.info("  주제: %s개", result_summary['stages']['trend']['count'])
    logger.info("  작성: %s개", result_summary['stages']['writer']['succeeded'])
    logger.info("  Reviewer 합격: %s개", result_summary['stages']['reviewer']['passed'])
    logger.info("  Final Gate 합격: %s개", result_summary['stages']['final_quality']['passed'])
    label = "[DRY-RUN] 커밋 차단" if dry_run else "발행"
    logger.info("  %s: %s개", label, pub.get('published', 0))
    if pub.get("blog_url"):
        logger.info("  URL : %s", pub['blog_url'])
    logger.info("  시간: %.1f초", elapsed)
    logger.info("=" * 60)
    return result_summary


def main():
    parser = argparse.ArgumentParser(description="Blog Auto-Agent")
    parser.add_argument("--mode", choices=["once", "dry-run", "trend-only", "write-only", "init-repo"], default="dry-run")
    parser.add_argument("--platform", choices=["github", "wordpress", "tistory"], default="github")
    parser.add_argument("--topic", type=str, default=None)
    args = parser.parse_args()

    for d in ["output/drafts", "output/published", "output/logs"]:
        (ROOT / d).mkdir(parents=True, exist_ok=True)

    if args.mode == "init-repo":
        load_dotenv(ROOT / ".env", override=True)
        try:
            cfg = get_github_config()
            logger.info("GitHub 레포 초기화: %s", cfg['repo_name'])
            success = init_github_repo(cfg, dry_run=False)
            if success:
                username = cfg["repo_name"].split("/")[0]
                print(f"\n초기화 완료: https://github.com/{cfg['repo_name']}")
                print(f"블로그 URL : https://{username}.github.io")
            else:
                print("초기화 실패 — 로그 확인")
        except EnvironmentError as e:
            logger.error(str(e))
            sys.exit(1)
        return

    if not validate_env(args.platform):
        sys.exit(1)

    if args.mode == "trend-only":
        topics = run_trend_agent()
        print(json.dumps(topics, ensure_ascii=False, indent=2))
    elif args.mode == "write-only":
        if not args.topic:
            logger.error("--topic 필요. 예: --topic 'AI 물류 자동화'")
            sys.exit(1)
        run_full_pipeline(dry_run=True, topic_override=args.topic, platform=args.platform)
    elif args.mode == "dry-run":
        run_full_pipeline(dry_run=True, platform=args.platform)
    elif args.mode == "once":
        run_full_pipeline(dry_run=False, platform=args.platform)


if __name__ == "__main__":
    main()
