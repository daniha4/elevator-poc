/* sw.js — Offline-first PWA for elevator fault codes
 *
 * Strategy:
 *   Core files  → Cache-first (always available offline)
 *   PDFs        → Cache-on-demand (cached after first view)
 *   Network     → Fallback when cache misses
 *
 * To enable auth in future: add auth check here before context.next()
 */

var CACHE_CORE = 'elevator-core-v9';
var CACHE_PDF  = 'elevator-docs-v9';

var PRECACHE = [
  './',
  './index.html',
  './fault-index.js',
  './data/fault_index.json',
  './data/mrl_index.json',
  './manifest.json',
  './apple-touch-icon.png',
  './icon-192.png',
  './icon-512.png',
];

/* ── Install: cache all core files ── */
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_CORE).then(function(cache) {
      return cache.addAll(PRECACHE);
    }).then(function() {
      return self.skipWaiting();
    })
  );
});

/* ── Activate: remove old caches ── */
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys
          .filter(function(k) { return k !== CACHE_CORE && k !== CACHE_PDF; })
          .map(function(k) { return caches.delete(k); })
      );
    }).then(function() { return self.clients.claim(); })
  );
});

/* ── Messages from app ── */
self.addEventListener('message', function(event) {
  if (!event.data) return;

  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  /* Cache a specific PDF on demand */
  if (event.data.type === 'CACHE_PDF' && event.data.url) {
    caches.open(CACHE_PDF).then(function(cache) {
      fetch(event.data.url).then(function(res) {
        if (res.ok) cache.put(event.data.url, res);
      });
    });
  }

  /* Cache all PDFs (call from settings/future admin page) */
  if (event.data.type === 'CACHE_ALL_PDFS' && event.data.urls) {
    caches.open(CACHE_PDF).then(function(cache) {
      event.data.urls.forEach(function(url) {
        fetch(url).then(function(res) {
          if (res.ok) cache.put(url, res);
        }).catch(function() {});
      });
    });
  }
});

/* ── Fetch: core = cache-first, PDFs = cache-on-demand, rest = network-first ── */
self.addEventListener('fetch', function(event) {
  if (event.request.method !== 'GET') return;

  var url = event.request.url;
  var isPdf = url.indexOf('/pdfs/') !== -1 || url.indexOf('/mrl/') !== -1;
  var isCore = PRECACHE.some(function(p) {
    return url.endsWith(p.replace('./', '/')) || url.endsWith('/');
  });

  if (isPdf) {
    /* PDF: serve from cache if available, otherwise fetch and cache */
    event.respondWith(
      caches.open(CACHE_PDF).then(function(cache) {
        return cache.match(event.request).then(function(cached) {
          if (cached) return cached;
          return fetch(event.request).then(function(res) {
            if (res.ok) cache.put(event.request, res.clone());
            return res;
          });
        });
      })
    );
    return;
  }

  if (isCore || url.indexOf('/data/') !== -1) {
    /* Core + data: network-first, cache fallback */
    event.respondWith(
      fetch(event.request)
        .then(function(res) {
          caches.open(CACHE_CORE).then(function(cache) {
            cache.put(event.request, res.clone());
          });
          return res;
        })
        .catch(function() {
          return caches.match(event.request);
        })
    );
    return;
  }

  /* Everything else: network-first */
  event.respondWith(
    fetch(event.request).catch(function() {
      return caches.match(event.request);
    })
  );
});
