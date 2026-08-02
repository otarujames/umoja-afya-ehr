const CACHE = 'umoja-afya-shell-v11.0.0-brand1';
const CORE = [
  '/',
  '/styles.css',
  '/offline.js',
  '/app.js',
  '/manifest.json',
  '/assets/umoja-logo-full.png',
  '/assets/umoja-logo-mark.png',
  '/assets/icons/favicon.ico',
  '/assets/icons/apple-touch-icon.png',
  '/assets/icons/umoja-192.png',
  '/assets/icons/umoja-512.png',
  '/assets/icons/umoja-maskable-512.png',
  '/assets/avatars/neema-k.png',
  '/assets/avatars/juma-ally-mwangi.png',
  '/assets/tanzania-coat-of-arms.png',
  '/assets/kenya-ministry-health.png',
  '/assets/nigeria-ministry-health.png',
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(CORE)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

async function shellResponse(request) {
  try {
    const response = await fetch(request, { cache: 'no-store' });
    if (response.ok) {
      const cache = await caches.open(CACHE);
      await cache.put(request, response.clone());
    }
    return response;
  } catch (_) {
    return (await caches.match(request)) || (await caches.match('/'));
  }
}

async function assetResponse(request) {
  const cached = await caches.match(request);
  const update = fetch(request, { cache: 'no-store' }).then(async response => {
    if (response.ok) {
      const cache = await caches.open(CACHE);
      await cache.put(request, response.clone());
    }
    return response;
  }).catch(() => null);
  return cached || (await update) || Response.error();
}

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;

  // API data is deliberately never placed in Cache Storage. The application
  // stores approved responses inside its PIN-protected AES-GCM IndexedDB vault.
  if (url.pathname.startsWith('/api/')) return;
  if (request.mode === 'navigate') {
    event.respondWith(shellResponse(request));
    return;
  }
  if (CORE.includes(url.pathname) || url.pathname.startsWith('/assets/')) {
    event.respondWith(assetResponse(request));
  }
});

self.addEventListener('sync', event => {
  if (event.tag !== 'umoja-afya-sync') return;
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clients => {
    clients.forEach(client => client.postMessage({ type: 'UMOJA_SYNC_REQUEST' }));
  }));
});

self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
});
