"""
test_github_publisher.py — GitHub Pages Publisher 단위 테스트
실행: pytest tests/test_github_publisher.py -v
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


class TestSlugGeneration:
    def test_korean_title_slug(self):
        """한글 제목이 슬러그로 변환되어야 함."""
        from agents.github_publisher import make_slug
        slug = make_slug("AI 물류 자동화 2025년 트렌드")
        assert "-" in slug
        assert len(slug) <= 60

    def test_special_chars_removed(self):
        """특수문자가 제거되어야 함."""
        from agents.github_publisher import make_slug
        slug = make_slug("테스트! 제목@ #특수문자$")
        assert "!" not in slug
        assert "@" not in slug
        assert "#" not in slug

    def test_max_length_60(self):
        """슬러그 최대 길이 60자 제한."""
        from agents.github_publisher import make_slug
        long_title = "a" * 100
        slug = make_slug(long_title)
        assert len(slug) <= 60


class TestCategoryParsing:
    def test_slash_separator(self):
        """'기술/자동화' → ['기술', '자동화'] 변환."""
        from agents.github_publisher import _parse_category
        result = _parse_category("기술/자동화")
        assert result == ["기술", "자동화"]

    def test_single_category(self):
        """단일 카테고리는 리스트로 반환."""
        from agents.github_publisher import _parse_category
        result = _parse_category("AI")
        assert result == ["AI"]

    def test_empty_returns_default(self):
        """빈 문자열은 기본값 반환."""
        from agents.github_publisher import _parse_category
        result = _parse_category("")
        assert result == ["기술"]

    def test_max_3_categories(self):
        """최대 3개 카테고리만 반환."""
        from agents.github_publisher import _parse_category
        result = _parse_category("A/B/C/D/E")
        assert len(result) <= 3


class TestJekyllMarkdownConversion:
    SAMPLE_POST = {
        "title": "AI 물류 자동화 테스트",
        "meta_description": "테스트 설명입니다.",
        "tags": ["AI", "자동화", "물류"],
        "category": "기술/AI",
        "content": "## 도입\n\n테스트 본문입니다.\n\n## 결론\n\n마무리입니다.",
        "seo_keywords": ["AI물류", "자동화"],
        "generated_at": "2025-03-23T09:00:00",
        "word_count": 100,
        "review_result": {"total_score": 82, "pass": True},
    }

    def test_file_name_format(self):
        """파일명이 YYYY-MM-DD-slug.md 형식이어야 함."""
        from agents.github_publisher import post_to_jekyll_markdown
        file_name, _ = post_to_jekyll_markdown(self.SAMPLE_POST)
        import re
        assert re.match(r"\d{4}-\d{2}-\d{2}-.+\.md$", file_name)

    def test_front_matter_present(self):
        """Front Matter(---)가 포함되어야 함."""
        from agents.github_publisher import post_to_jekyll_markdown
        _, content = post_to_jekyll_markdown(self.SAMPLE_POST)
        assert content.startswith("---")
        assert content.count("---") >= 2

    def test_title_in_front_matter(self):
        """제목이 Front Matter에 포함되어야 함."""
        from agents.github_publisher import post_to_jekyll_markdown
        _, content = post_to_jekyll_markdown(self.SAMPLE_POST)
        assert "AI 물류 자동화 테스트" in content

    def test_more_tag_inserted(self):
        """<!--more--> 태그가 삽입되어야 함."""
        from agents.github_publisher import post_to_jekyll_markdown
        _, content = post_to_jekyll_markdown(self.SAMPLE_POST)
        assert "<!--more-->" in content

    def test_content_preserved(self):
        """본문 내용이 손실 없이 포함되어야 함."""
        from agents.github_publisher import post_to_jekyll_markdown
        _, content = post_to_jekyll_markdown(self.SAMPLE_POST)
        assert "테스트 본문입니다" in content


class TestGithubConfig:
    def test_missing_token_raises(self, monkeypatch):
        """GITHUB_TOKEN 없으면 EnvironmentError 발생."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_REPO", raising=False)
        from agents.github_publisher import get_github_config
        with pytest.raises(EnvironmentError) as exc_info:
            get_github_config()
        assert "GITHUB_TOKEN" in str(exc_info.value)

    def test_valid_config(self, monkeypatch):
        """유효한 환경변수로 설정 dict 반환."""
        monkeypatch.setenv("GITHUB_TOKEN", "test_token")
        monkeypatch.setenv("GITHUB_REPO", "user/user.github.io")
        from agents.github_publisher import get_github_config
        cfg = get_github_config()
        assert cfg["token"] == "test_token"
        assert cfg["repo_name"] == "user/user.github.io"
        assert cfg["branch"] == "main"


class TestHumanApprovalGate:
    def test_auto_approve_when_gate_off(self, monkeypatch):
        """HUMAN_GATE=false 시 자동 승인."""
        monkeypatch.setenv("HUMAN_GATE", "false")
        from agents.github_publisher import human_approval_gate
        result = human_approval_gate({"title": "테스트"})
        assert result is True


class TestPublisherSkipsInvalidPosts:
    def test_skips_error_posts(self, monkeypatch):
        """error 필드 포스트는 발행 대상에서 제외."""
        monkeypatch.setenv("HUMAN_GATE", "false")
        monkeypatch.setenv("GITHUB_TOKEN", "fake")
        monkeypatch.setenv("GITHUB_REPO", "user/user.github.io")
        from agents.github_publisher import run_github_publisher
        result = run_github_publisher([{"error": "작성 실패", "title": "오류 포스트"}])
        assert result == []

    def test_skips_failed_review(self, monkeypatch):
        """검수 미합격 포스트는 발행 대상에서 제외."""
        monkeypatch.setenv("HUMAN_GATE", "false")
        monkeypatch.setenv("GITHUB_TOKEN", "fake")
        monkeypatch.setenv("GITHUB_REPO", "user/user.github.io")
        from agents.github_publisher import run_github_publisher
        post = {
            "title": "미합격 포스트",
            "content": "내용",
            "review_result": {"pass": False, "total_score": 40},
        }
        result = run_github_publisher([post])
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
