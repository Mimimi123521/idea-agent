const CACHE = 'idea-agent-v5';
const STATIC_URLS = ['/static/icons/icon-192.png', '/static/icons/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC_URLS).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(k => k !== CACHE).map(k => caches.delete(k))
      );
    }).then(() => clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // API requests: always network, fallback to offline response
  if (url.pathname.includes('/api/')) {
    e.respondWith(fetch(e.request).catch(() => new Response(JSON.stringify({offline: true}), {status: 503})));
    return;
  }

  // Navigation requests (HTML pages): network-first, fallback to cache
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then(resp => {
          // Cache the latest page
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
          return resp;
        })
        .catch(() => caches.match(e.request).then(r => r || caches.match('/')))
    );
    return;
  }

  // Static assets: cache-first, fallback to network
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request).then(resp => {
      // Cache new static assets
      if (resp.ok && (url.pathname.startsWith('/static/') || url.pathname === '/manifest.json' || url.pathname === '/sw.js')) {
        const clone = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
      }
      return resp;
    }))
  );
});

// ====== Notification Handling ======

// Display notification when received from server push
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

// Handle notification click - open/focus the app
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

// Listen for messages from the client to show notifications
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
});

// Allow page to trigger immediate SW update
self.addEventListener('message', e => {
  if (e.data && e.data.type === 'skip-waiting') {
    self.skipWaiting();
  }
});