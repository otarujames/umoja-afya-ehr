const RELEASE = '10.16.3-20260802-1';
const CACHE_NAME = `umoja-${RELEASE}`;

const STATIC_ASSETS = [
  '/styles.css',
  '/assets/umoja-logo-mark.png',
  '/assets/umoja-logo-full.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys =>
        Promise.all(
          keys
            .filter(key => key.startsWith('umoja-') && key !== CACHE_NAME)
            .map(key => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;

  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);

  if (url.origin !== self.location.origin) {
    return;
  }

  /*
   * Never serve authentication, APIs, HTML or application JavaScript
   * from an old cache.
   */
  const networkOnly =
    url.pathname.startsWith('/api/') ||
    url.pathname === '/' ||
    url.pathname === '/index.html' ||
    url.pathname === '/app.js' ||
    url.pathname === '/offline.js' ||
    url.pathname === '/service-worker.js' ||
    request.mode === 'navigate';

  if (networkOnly) {
    event.respondWith(
      fetch(request, { cache: 'no-store' })
        .catch(() => {
          if (request.mode === 'navigate') {
            return new Response(
              'Umoja Afya is temporarily unavailable. Please reconnect.',
              {
                status: 503,
                headers: {
                  'Content-Type': 'text/plain; charset=utf-8'
                }
              }
            );
          }

          throw new Error('Network unavailable');
        })
    );

    return;
  }

  /*
   * Static visual assets use stale-while-revalidate.
   */
  event.respondWith(
    caches.match(request).then(cached => {
      const network = fetch(request).then(response => {
        if (response.ok) {
          const copy = response.clone();

          caches.open(CACHE_NAME).then(cache => {
            cache.put(request, copy);
          });
        }

        return response;
      });

      return cached || network;
    })
  );
});
