const CACHE = 'idea-agent-v2';
const URLS = ['/', '/static/css/app.css', '/static/js/app.js', '/static/icons/icon-192.png', '/static/icons/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(URLS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(clients.claim());
});

self.addEventListener('fetch', e => {
  if (e.request.url.includes('/api/')) {
    e.respondWith(fetch(e.request).catch(() => new Response(JSON.stringify({offline: true}), {status: 503})));
  } else {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
  }
});

// ====== Notification Handling ======

// Display notification when received from client or server push
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
      // If app is already open, focus it
      for (const client of windowClients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          return client.focus().then(c => {
            if (c.navigate) c.navigate(targetUrl);
            return c;
          });
        }
      }
      // Otherwise open a new window
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