/**
 * Owngarnization — Service Worker (PWA + Web Push + Caché Offline)
 */

const CACHE_VERSION = "owngarnization-v8";
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const API_CACHE = `${CACHE_VERSION}-api`;

const STATIC_ASSETS = [
  "/",
  "/m",
  "/download",
  "/static/css/styles.css?v=8",
  "/static/css/variables.css?v=8",
  "/static/css/base.css?v=8",
  "/static/css/layout.css?v=8",
  "/static/css/board.css?v=8",
  "/static/css/calendar.css?v=8",
  "/static/css/modals.css?v=8",
  "/static/css/guide.css?v=8",
  "/static/css/responsive.css?v=8",
  "/static/css/mobile.css?v=8",
  "/static/js/api.js?v=8",
  "/static/js/app.js?v=8",
  "/static/js/board.js?v=8",
  "/static/js/calendar.js?v=8",
  "/static/js/modal.js?v=8",
  "/static/js/task_modal.js?v=8",
  "/static/js/drawer.js?v=8",
  "/static/js/guide.js?v=8",
  "/static/js/pwa.js?v=8",
  "/static/js/push.js?v=8",
  "/static/img/logo.png?v=4",
  "/static/img/favicon.ico?v=4",
  "/static/img/icons/icon-192.png?v=4",
  "/static/img/icons/icon-512.png?v=4",
  "/static/img/icons/badge-72.png"
];

const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sin conexión — Owngarnization</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Inter", sans-serif;
      background: #F5EFE6;
      color: #111111;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      padding: 24px;
      text-align: center;
    }
    .card {
      background: #FFFFFF;
      border: 1px solid #DFD5C5;
      border-radius: 16px;
      padding: 32px 24px;
      max-width: 380px;
      box-shadow: 0 8px 24px rgba(17, 17, 17, 0.08);
    }
    h1 { font-size: 20px; margin: 0 0 10px; }
    p { font-size: 14px; color: #524C44; line-height: 1.5; margin-bottom: 20px; }
    button {
      background: #111111;
      color: #FFFFFF;
      border: none;
      border-radius: 10px;
      padding: 12px 20px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>📡 Estás sin conexión</h1>
    <p>No hemos podido conectar con el servidor de Owngarnization. Comprueba tu conexión a internet e inténtalo de nuevo.</p>
    <button onclick="window.location.reload()">Reintentar</button>
  </div>
</body>
</html>`;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {
        // Ignorar fallos individuales
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== STATIC_CACHE && key !== API_CACHE)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  if (url.pathname.startsWith("/api/occurrences")) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.status === 200) {
            const copy = response.clone();
            caches.open(API_CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.status === 200) {
            const copy = response.clone();
            caches.open(STATIC_CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(async () => {
        const cachedPage = await caches.match(request);
        if (cachedPage) return cachedPage;
        return new Response(OFFLINE_HTML, {
          headers: { "Content-Type": "text/html; charset=utf-8" }
        });
      })
    );
  }
});

self.addEventListener("push", (event) => {
  let payload = {
    title: "⏰ Recordatorio — Owngarnization",
    body: "Tienes una tarea programada.",
    icon: "/static/img/icons/icon-192.png?v=4",
    badge: "/static/img/icons/badge-72.png",
    tag: "owngarnization-reminder",
    data: { url: "/m" }
  };

  if (event.data) {
    try {
      const parsed = event.data.json();
      payload = { ...payload, ...parsed };
    } catch {
      payload.body = event.data.text();
    }
  }

  const options = {
    body: payload.body,
    icon: payload.icon || "/static/img/icons/icon-192.png?v=4",
    badge: payload.badge || "/static/img/icons/badge-72.png",
    tag: payload.tag || "owngarnization-reminder",
    renotify: true,
    requireInteraction: false,
    data: { url: payload.url || payload.data?.url || "/m" },
    vibrate: [150, 70, 150]
  };

  event.waitUntil(self.registration.showNotification(payload.title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/m";

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ("focus" in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }
    })
  );
});
