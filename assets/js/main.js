document.addEventListener('DOMContentLoaded', function() {
  // 읽기 시간 계산
  if (typeof calcReadingTime === 'function') calcReadingTime();
  // 목차 생성
  if (typeof buildTOC === 'function') buildTOC();
  // 검색 초기화
  if (typeof initSearch === 'function') initSearch();
  // 읽기 진행바
  if (typeof updateProgress === 'function') {
    window.addEventListener('scroll', updateProgress);
  }
  // 상단 이동 버튼
  if (typeof updateBackToTop === 'function') {
    window.addEventListener('scroll', updateBackToTop);
  }
});

// 읽기 진행 바
function updateProgress() {
  var el = document.getElementById('reading-progress');
  if (!el) return;
  var scrollTop = window.scrollY;
  var docHeight = document.body.scrollHeight - window.innerHeight;
  var progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
  el.style.width = Math.min(progress, 100) + '%';
}

// 상단으로 버튼
function updateBackToTop() {
  var btn = document.getElementById('back-to-top');
  if (!btn) return;
  if (window.scrollY > 400) {
    btn.classList.add('visible');
  } else {
    btn.classList.remove('visible');
  }
}

// 목차 자동 생성
function buildTOC() {
  var postBody = document.querySelector('.post-body');
  var tocBox = document.querySelector('.toc-box');
  if (!postBody || !tocBox) return;
  var headings = postBody.querySelectorAll('h2, h3');
  if (headings.length < 2) { tocBox.style.display = 'none'; return; }
  var list = tocBox.querySelector('.toc-list');
  if (!list) return;
  headings.forEach(function(h, i) {
    var id = 'heading-' + i;
    h.id = id;
    var li = document.createElement('li');
    var a = document.createElement('a');
    a.href = '#' + id;
    a.textContent = h.textContent;
    if (h.tagName === 'H3') { li.style.paddingLeft = '14px'; }
    li.appendChild(a);
    list.appendChild(li);
  });
}

// 읽기 시간 계산
function calcReadingTime() {
  var body = document.querySelector('.post-body');
  var el = document.querySelector('.reading-time');
  if (!body || !el) return;
  var words = body.textContent.trim().split(/\s+/).length;
  var minutes = Math.ceil(words / 200);
  el.textContent = '⏱️ 약 ' + minutes + '분 읽기';
}

// 검색 기능
function initSearch() {
  var trigger = document.querySelector('.search-trigger');
  var overlay = document.getElementById('search-overlay');
  var input = document.getElementById('search-input');
  if (!trigger || !overlay) return;

  trigger.addEventListener('click', function() {
    overlay.classList.add('open');
    if (input) input.focus();
  });
  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) overlay.classList.remove('open');
  });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') overlay.classList.remove('open');
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      overlay.classList.add('open');
      if (input) input.focus();
    }
  });

  if (input) {
    input.addEventListener('input', function() {
      var q = this.value.toLowerCase().trim();
      var results = document.getElementById('search-results');
      if (!results) return;
      results.innerHTML = '';
      if (q.length < 1) return;
      var items = document.querySelectorAll('[data-post-title]');
      var found = 0;
      items.forEach(function(item) {
        var title = (item.dataset.postTitle || '').toLowerCase();
        var desc = (item.dataset.postDesc || '').toLowerCase();
        if (title.includes(q) || desc.includes(q)) {
          var a = document.createElement('a');
          a.href = item.dataset.postUrl || '#';
          a.className = 'search-result-item';
          a.innerHTML = '<div class="search-result-title">' + item.dataset.postTitle + '</div>' +
                        '<div class="search-result-desc">' + (item.dataset.postDesc || '').substring(0, 80) + '...</div>';
          results.appendChild(a);
          found++;
        }
      });
      if (found === 0) {
        results.innerHTML = '<div style="text-align:center;padding:20px;color:#5f6368;font-size:14px">검색 결과가 없습니다</div>';
      }
    });
  }
}

// URL 복사
function copyURL() {
  navigator.clipboard.writeText(window.location.href).then(function() {
    var btn = document.querySelector('.share-copy');
    if (btn) { btn.textContent = '✅ 복사됨!'; setTimeout(function(){ btn.textContent = '🔗 URL 복사'; }, 2000); }
  });
}

// 모바일 메뉴
function toggleMobileMenu() {
  var nav = document.querySelector('.nav-links');
  var btn = document.querySelector('.nav-hamburger');
  var isOpen = nav.classList.toggle('open');
  btn.textContent = isOpen ? '×' : '☰';
}

document.addEventListener('click', function(e) {
  if (!e.target.closest('.site-header')) {
    var nav = document.querySelector('.nav-links');
    var btn = document.querySelector('.nav-hamburger');
    if (nav && nav.classList.contains('open')) {
      nav.classList.remove('open');
      btn.textContent = '☰';
    }
  }
});
