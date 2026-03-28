import os
from github import Auth, Github
from dotenv import load_dotenv

load_dotenv(r'E:\아진네트웍스\Claude Code\블로그 제작\blog_agent\.env', override=True)
auth = Auth.Token(os.environ['GITHUB_TOKEN'])
g = Github(auth=auth)
repo = g.get_repo('ajinnetworks/ajinnetworks.github.io')

# ── 1. home.html 수정 ─────────────────────────
f = repo.get_contents('_layouts/home.html', ref='main')
content = f.decoded_content.decode('utf-8')

# 사이드바 카테고리 위젯 → 별도 페이지 이동 방식으로 교체
old_cat_widget = '''      <!-- 카테고리 위젯 -->
      <div class="widget">
        <h3 class="widget-title">📂 카테고리</h3>
        <ul class="category-list">
          {% assign sorted_cats = site.categories | sort %}
          {% for category in sorted_cats %}
            <li class="cat-item">
              <a href="#" onclick="filterPosts('{{ category[0] }}'); return false;">
                <span class="cat-name">{{ category[0] }}</span>
                <span class="cat-count">{{ category[1] | size }}</span>
              </a>
            </li>
          {% endfor %}
        </ul>
      </div>'''

new_cat_widget = '''      <!-- 카테고리 위젯 (별도 페이지 이동) -->
      <div class="widget">
        <h3 class="widget-title">📂 카테고리</h3>
        <ul class="category-list">
          {% assign sorted_cats = site.categories | sort %}
          {% for category in sorted_cats %}
            <li class="cat-item">
              <a href="{{ site.baseurl }}/category/{{ category[0] | uri_escape }}/">
                <span class="cat-name">{{ category[0] }}</span>
                <span class="cat-count">{{ category[1] | size }}</span>
              </a>
            </li>
          {% endfor %}
        </ul>
      </div>'''

if old_cat_widget in content:
    content = content.replace(old_cat_widget, new_cat_widget)
    print('사이드바 카테고리 링크 수정 완료')
else:
    print('사이드바 블록 미발견 - 수동 확인 필요')

repo.update_file(
    '_layouts/home.html',
    'fix: sidebar category links to separate pages',
    content,
    f.sha,
    branch='main'
)
print('home.html 업데이트 완료')

# ── 2. 카테고리 페이지 레이아웃 생성 ──────────
cat_layout = '''---
layout: default
---
<div class="blog-container">
  <div class="category-header">
    <h1>📂 {{ page.category }}</h1>
    <p>{{ page.category }} 카테고리의 포스트 목록입니다.</p>
    <a href="{{ site.baseurl }}/" class="btn-back">← 전체 목록으로</a>
  </div>
  <div class="post-grid">
    {% assign cat_posts = site.categories[page.category] %}
    {% for post in cat_posts %}
      <article class="post-card">
        <div class="post-card-header">
          <span class="post-cat-badge">{{ post.categories[0] }}</span>
          <span class="post-read-time">⏱ 약 {{ post.content | number_of_words | divided_by: 200 | plus: 1 }}분</span>
        </div>
        <h2 class="post-title">
          <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
        </h2>
        {% if post.description %}
          <p class="post-desc">{{ post.description | truncate: 120 }}</p>
        {% elsif post.excerpt %}
          <p class="post-desc">{{ post.excerpt | strip_html | truncate: 120 }}</p>
        {% endif %}
        <div class="post-meta">
          <span class="post-date">📅 {{ post.date | date: "%Y년 %m월 %d일" }}</span>
        </div>
        <a href="{{ post.url | relative_url }}" class="read-more">더 읽기 →</a>
      </article>
    {% endfor %}
  </div>
</div>'''

try:
    existing = repo.get_contents('_layouts/category.html', ref='main')
    repo.update_file(
        '_layouts/category.html',
        'feat: add category layout',
        cat_layout,
        existing.sha,
        branch='main'
    )
except:
    repo.create_file(
        '_layouts/category.html',
        'feat: add category layout',
        cat_layout,
        branch='main'
    )
print('category.html 레이아웃 생성 완료')

# ── 3. 카테고리별 페이지 생성 ─────────────────
categories = ['공장자동화', '딥러닝비전', '스마트팩토리', '물류자동화', '제어SW']

for cat in categories:
    page_content = f'''---
layout: category
title: {cat}
category: {cat}
permalink: /category/{cat}/
---'''
    path = f'category/{cat}/index.html'
    try:
        existing = repo.get_contents(path, ref='main')
        repo.update_file(path, f'feat: category page {cat}', page_content, existing.sha, branch='main')
    except:
        repo.create_file(path, f'feat: category page {cat}', page_content, branch='main')
    print(f'카테고리 페이지 생성: /category/{cat}/')

print('\n모든 작업 완료')
print('1~3분 후 아래 URL에서 확인하세요:')
for cat in categories:
    print(f'  https://ajinnetworks.github.io/category/{cat}/')
