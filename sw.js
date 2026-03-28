const CACHE_NAME = 'ajin-blog-' + new Date().toISOString().slice(0,10).replace(/-/g,'');
const STATIC_ASSETS = [
  '/',
  '/assets/css/style.css',
  '/assets/images/ajin_logo.webp',
  '/assets/images/ajin_logo_footer_white.webp',
  '/assets/images/icon-192x192.png',
  '/manifest.json'
];

// 설치 단계 - 핵심 파일 캐시
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// 활성화 단계 - 구버전 캐시 삭제
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// 요청 처리 - Network First 전략
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    fetch(event.request)
      .then(res => {
        const clone = res.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return res;
      })
      .catch(() => caches.match(event.request))
  );
});
