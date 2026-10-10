// INVENTIQ Service Worker - Progressive Web App
// Version: inventiq-pwa-v1
const CACHE_NAME = 'inventiq-pwa-v1';

const PRECACHE_URLS = [
  '/offline/',
  '/manifest.webmanifest',
  '/static/css/style.css',
  '/static/images/waxis_w.png',
  '/static/images/waxis-logo.png',
  '/static/images/pwa/icon-192.png',
  '/static/images/pwa/icon-512.png',
  '/static/images/pwa/apple-touch-icon.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js'
];

// 1. INSTALL: Pre-cache app shell assets & activate immediately
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Use Promise.allSettled or cache individually so one failing CDN doesn't abort install
      return Promise.allSettled(
        PRECACHE_URLS.map((url) =>
          cache.add(new Request(url, { cache: 'reload' })).catch((err) => {
            console.warn('[SW] Failed to pre-cache:', url, err);
          })
        )
      );
    }).then(() => self.skipWaiting())
  );
});

// 2. ACTIVATE: Purge stale caches & take control immediately
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            console.log('[SW] Deleting legacy cache:', name);
            return caches.delete(name);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// 3. FETCH: Smart caching strategy
self.addEventListener('fetch', (event) => {
  const request = event.request;

  // Never intercept non-GET requests (e.g. POST deductions, PO dispatch, logins)
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);

  // A. Navigation Requests (HTML pages): Network-First with Offline Fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // If valid response, clone into cache for offline review
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(async () => {
          // Network failed: try cache first
          const cachedPage = await caches.match(request);
          if (cachedPage) {
            return cachedPage;
          }
          // If not in cache, fallback to branded offline page
          const offlinePage = await caches.match('/offline/');
          return offlinePage || new Response('Offline - No connection', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'text/plain' }
          });
        })
    );
    return;
  }

  // B. Static Assets (CSS, JS, Fonts, Images): Stale-While-Revalidate
  const isStaticAsset =
    url.pathname.startsWith('/static/') ||
    url.hostname.includes('cdn.jsdelivr.net') ||
    url.hostname.includes('unpkg.com') ||
    url.hostname.includes('fonts.googleapis.com') ||
    url.hostname.includes('fonts.gstatic.com');

  if (isStaticAsset) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        const fetchPromise = fetch(request)
          .then((networkResponse) => {
            if (networkResponse && networkResponse.status === 200) {
              const clone = networkResponse.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
            }
            return networkResponse;
          })
          .catch(() => null);

        // Return cached asset immediately if available, otherwise wait for network
        return cachedResponse || fetchPromise;
      })
    );
    return;
  }

  // C. Default: Normal network fetch
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});
