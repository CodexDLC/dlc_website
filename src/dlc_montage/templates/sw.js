const CACHE_NAME = 'codex-site-v1';
const STATIC_CACHE = 'codex-static-v1';

// Files for initial caching
const STATIC_ASSETS = [
    '/static/css/app.css',
    '/static/js/base.js',
    '/static/offline.html'
];

// Service Worker Installation
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                return self.skipWaiting();
            })
    );
});

// Activation and cleanup of old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name !== CACHE_NAME && name !== STATIC_CACHE)
                    .map(name => {
                        return caches.delete(name);
                    })
            );
        }).then(() => {
            return self.clients.claim();
        })
    );
});

// Fetch Strategy
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Ignore non-http requests
    if (!url.protocol.startsWith('http')) {
        return;
    }

    // 1. Network Only for Admin and Cabinet
    if (url.pathname.startsWith('/admin/') || url.pathname.startsWith('/cabinet/')) {
        return;
    }

    // 2. Network Only for API
    if (url.pathname.startsWith('/api/')) {
        return;
    }

    // 3. Cache-first for static assets
    const isStaticAsset = url.pathname.startsWith('/static/') &&
        /\.(css|js|woff2?|ttf|eot|png|jpg|jpeg|webp|svg|ico)(\?.*)?$/.test(url.pathname);

    if (isStaticAsset) {
        event.respondWith(
            caches.match(request).then(cached => {
                if (cached) return cached;
                return fetch(request).then(response => {
                    if (request.method === 'GET' && response.status === 200) {
                        const responseClone = response.clone();
                        caches.open(STATIC_CACHE).then(cache => cache.put(request, responseClone));
                    }
                    return response;
                });
            })
        );
        return;
    }

    // 4. Network First for HTML pages
    if (request.mode === 'navigate' || (request.headers.get('accept') && request.headers.get('accept').includes('text/html'))) {
        event.respondWith(
            fetch(request)
                .catch(() => {
                    return caches.match(request).then(cached => {
                        return cached || caches.match('/static/offline.html');
                    });
                })
        );
        return;
    }
});

// Message handling
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});
