const CACHE = 'idea-agent-v8';

// Only cache static assets, never cache HTML or API
// We pre-cache nothing at install time; all caching is runtime with cache-control

self.addEventListener('install', e => {
  // Skip waiting immediately to take control
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => {
      // Delete ALL old caches on activation
      console.log('SW activate: deleting all old caches, keys:', keys);
      return Promise.all(keys.map(k => caches.delete(k)));
    }).then(() => {
      console.log('SW activate: all caches cleared, claiming clients');
      return clients.claim();
    })
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // API requests: always network, never cache
  if (url.pathname.includes('/api/')) {
    e.respondWith(
      fetch(e.request, { cache: 'no-store' })
        .catch(() => new Response(JSON.stringify({offline: true}), {status: 503}))
    );
    return;
  }

  // Navigation requests (HTML pages): ALWAYS network, NEVER cache
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request, { cache: 'no-store' }).catch(() => {
        // If offline, try to serve the last known page (if any in cache)
        return caches.match(e.request).then(r => r || caches.match('/'));
      })
    );
    return;
  }

  // Static assets: cache-first, but use cache-busting via query params
  e.respondWith(
    caches.match(e.request).then(r => {
      if (r) return r;
      return fetch(e.request, { cache: 'no-store' }).then(resp => {
        // Only cache static assets, icons, manifest, and sw.js itself
        if (resp.ok && (
          url.pathname.startsWith('/static/') ||
          url.pathname === '/manifest.json' ||
          url.pathname === '/sw.js'
        )) {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return resp;
      });
    })
  );
});

// ====== Notification Handling ======

self.addEventListener('push', e => {
  let data = { title: '灵感管家', body: '你有新的提醒', icon: '/static/icons/icon-192.png' };
  try {
    if (e.data) {
      const parsed = e.data.json();
      data = { ...data, ...parsed };
    }
  } catch (err) {}
  e.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon,
      tag: data.tag || 'idea-reminder',
      requireInteraction: true,
      vibrate: [200, 100, 200],
      data: { url: data.url || '/' }
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const targetUrl = (e.notification.data && e.notification.data.url) || '/';
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
      for (const client of windowClients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          return client.focus().then(c => {
            if (c.navigate) c.navigate(targetUrl);
            return c;
          });
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});

// Listen for messages from the client
self.addEventListener('message', e => {
  if (e.data && e.data.type === 'show-notification') {
    const d = e.data;
    self.registration.showNotification(d.title || '灵感管家', {
      body: d.body || '',
      icon: '/static/icons/icon-192.png',
      tag: d.tag || 'idea-reminder',
      requireInteraction: true,
      vibrate: [200, 100, 200],
      data: { url: d.url || '/' }
    });
  }
  if (e.data && e.data.type === 'skip-waiting') {
    self.skipWaiting();
  }
});