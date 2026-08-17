"""Phase 2 image bridge for GitHub Pages publishing.

Installs an image-aware Jekyll serializer without rewriting the legacy publisher.
The generated post front matter carries image, image_alt and og_image so the
site layout, Article schema and social previews can all use the same asset.
"""

from datetime import datetime

import frontmatter

from agents import github_publisher as gp


def _image_aware_post_to_jekyll_markdown(post: dict) -> tuple[str, str]:
    now = datetime.now(gp.KST)
    date_str = now.strftime("%Y-%m-%d")
    datetime_str = now.strftime("%Y-%m-%d %H:%M:%S +0900")

    title = post.get("title", "제목 없음")
    slug = gp.make_slug(title)
    file_name = f"{date_str}-{slug}.md"

    raw_content = post.get("content", "")
    if isinstance(raw_content, list):
        safe_content = "\n\n".join(str(c) for c in raw_content)
    elif isinstance(raw_content, dict):
        safe_content = str(raw_content)
    else:
        safe_content = str(raw_content) if raw_content else ""
    safe_content = safe_content.encode("utf-8", errors="ignore").decode("utf-8")

    image = str(post.get("image") or "/assets/img/og-default.png")
    image_alt = str(post.get("image_alt") or title)
    og_image = str(post.get("og_image") or image)

    meta = frontmatter.Post(
        content=safe_content,
        layout="post",
        title=title,
        date=datetime_str,
        categories=gp._parse_category(post.get("category", "기술")),
        tags=post.get("tags", [])[:10],
        description=post.get("meta_description", "")[:160],
        keywords=post.get("seo_keywords", []),
        author="AI Agent",
        image=image,
        image_alt=image_alt,
        og_image=og_image,
        image_strategy=post.get("image_strategy", "topic-aware-curated-hero"),
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


def install() -> None:
    gp.post_to_jekyll_markdown = _image_aware_post_to_jekyll_markdown
