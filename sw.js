/**
 * NQ Unified — Service Worker
 * Estrategias (decididas en Fase 0, decisión 6):
 *   cache-first        → HTML, CSS, JS, fuentes, manifest, iconos, Chart.js CDN
 *   stale-while-reval  → manengis_tactico.json, datos_radar.json
 *   network-only+fallb → /api/live-tactico (datos live, nunca servir cacheado como fresco)
 */

const CACHE = 'nq-unified-v4';

// Recursos a pre-cachear en el install
const PRECACHE = [
  '/',
  '/index.html',
  '/manifest.json',
  '/fixtures/manengis_sample.json',
  '/fixtures/radar_sample.json',
  'https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=JetBrains+Mono:wght@300;400;500;600&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js',
];

// URLs que usan stale-while-revalidate (solo manengis, no datos_radar)
const SWR_PATTERNS = [
  /manengis_tactico\.json/,
  /nq-proxy.*\/main\/manengis/,
];

// URLs que usan network-first (datos que cambian frecuentemente + index.html)
const NETWORK_FIRST_PATTERNS = [
  /datos_radar\.json/,
  /\/index\.html$/,
  /nq-unified\.vercel\.app\/?$/,
  /nq-unified\.vercel\.app\/\?/,
];

// URL del live (network-only con fallback)
const LIVE_PATTERN = /\/api\/live-tactico/;

// ── Esquemas que el SW no puede cachear (chrome-extension, moz-extension, etc.) ──
function isCacheableRequest(request) {
  return request.url.startsWith('http://') || request.url.startsWith('https://');
}

// ── INSTALL: pre-cachear activos estáticos ──────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE).then(cache => {
      return Promise.allSettled(
        PRECACHE.map(url => cache.add(url).catch(e => console.warn('[SW] No cacheado:', url, e.message)))
      );
    }).then(() => self.skipWaiting())
  );
});

// ── ACTIVATE: limpiar caches viejos ────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
     .then(() => {
       // Forzar recarga de todos los clientes cuando el SW se activa
       return self.clients.matchAll({ type: 'window' }).then(clients => {
         clients.forEach(client => client.postMessage({ type: 'SW_UPDATED_RELOAD' }));
       });
     })
  );
});

// ── FETCH: interceptar peticiones ──────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = request.url;

  // Solo interceptar GET con esquema http/https
  if (request.method !== 'GET') return;
  if (!isCacheableRequest(request)) return;

  // 1. Live API → network-only con timeout 4 s y fallback a cache
  if (LIVE_PATTERN.test(url)) {
    event.respondWith(networkWithFallback(request, 4000));
    return;
  }

  // 2a. datos_radar.json → network-first (siempre datos frescos)
  if (NETWORK_FIRST_PATTERNS.some(p => p.test(url))) {
    event.respondWith(networkFirst(request));
    return;
  }

  // 2b. manengis_tactico.json → stale-while-revalidate
  if (SWR_PATTERNS.some(p => p.test(url))) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  // 3. Todo lo demás → cache-first
  event.respondWith(cacheFirst(request));
});

// ── Estrategia: cache-first ─────────────────────────────────────────────────
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (_) {
    return new Response('Sin conexión y sin cache para este recurso.', {
      status: 503,
      headers: { 'Content-Type': 'text/plain; charset=utf-8' },
    });
  }
}

// ── Estrategia: network-first con fallback a caché ─────────────────────────
async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request, { cache: 'no-store' });
    if (response.ok) {
      cache.put(request, response.clone());
      notifyClients({ type: 'DATA_UPDATED', url: request.url });
    }
    return response;
  } catch (_) {
    // Sin red → usar caché como último recurso
    const cached = await cache.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: 'sin red y sin cache' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// ── Estrategia: stale-while-revalidate ─────────────────────────────────────
async function staleWhileRevalidate(request) {
  const cache  = await caches.open(CACHE);
  const cached = await cache.match(request);

  // Revalidar en background (no await)
  const fetchPromise = fetch(request).then(response => {
    if (response.ok) {
      cache.put(request, response.clone());
      // Notificar a los clientes que hay datos nuevos
      notifyClients({ type: 'DATA_UPDATED', url: request.url });
    }
    return response;
  }).catch(() => null);

  // Devolver el caché al instante si existe; si no, esperar la red
  return cached || await fetchPromise || offlinePage();
}

// ── Estrategia: network-only con timeout y fallback ─────────────────────────
async function networkWithFallback(request, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(request, { signal: controller.signal });
    clearTimeout(timer);
    if (response.ok) {
      const cache = await caches.open(CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (_) {
    clearTimeout(timer);
    // Fallback: último live cacheado (stale)
    const cached = await caches.match(request);
    if (cached) {
      // Clonar y añadir header para que el cliente sepa que es stale
      const headers = new Headers(cached.headers);
      headers.set('X-SW-Stale', 'true');
      const body = await cached.text();
      return new Response(body, { status: 200, headers });
    }
    return new Response(JSON.stringify({ error: 'sin red y sin cache live' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// ── Notificar a todos los clientes ──────────────────────────────────────────
async function notifyClients(message) {
  const clients = await self.clients.matchAll({ type: 'window' });
  clients.forEach(client => client.postMessage(message));
}

// ── Página offline de emergencia ────────────────────────────────────────────
function offlinePage() {
  return new Response(
    `<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>NQ Unified — Sin conexión</title>
    <style>body{background:#080810;color:#9896b8;font-family:monospace;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;text-align:center;gap:16px;margin:0}
    h1{color:#f0eeff;font-size:20px}code{color:#8b7fff}</style></head>
    <body><h1>Sin conexión</h1><p>Mostrando últimos datos cacheados.</p>
    <p>Cuando vuelvas a tener red, <a href="/" style="color:#8b7fff">recarga la app</a>.</p></body></html>`,
    { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
  );
}
