// Oddiy service worker: ilova "qobig'i" tez ochiladi. API (/api) HECH QACHON keshlanmaydi,
// shuning uchun ma'lumotlar doim yangi. Yangi versiya chiqsa eski kesh o'zi o'chadi.
const CACHE = 'zavod-shell-v1';

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(['/', '/manifest.webmanifest', '/icon-192.png'])));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api')) return;

  if (req.mode === 'navigate') {
    // Sahifa: avval tarmoq (yangi versiya), internet yo'q bo'lsa keshdagi qobiq
    e.respondWith(fetch(req).catch(() => caches.match('/')));
    return;
  }
  // /assets/* fayllar nomida hash bor - kesh-birinchi
  e.respondWith(
    caches.match(req).then((hit) => hit || fetch(req).then((res) => {
      if (res.ok && url.pathname.startsWith('/assets/')) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
      }
      return res;
    })),
  );
});
