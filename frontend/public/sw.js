const CACHE_VERSION = "v1";
const SHELL_CACHE = `ce-aleg-shell-${CACHE_VERSION}`;
const STATIC_CACHE = `ce-aleg-static-${CACHE_VERSION}`;
const PRODUCT_IMAGE_CACHE = `ce-aleg-product-images-${CACHE_VERSION}`;
const CURRENT_CACHES = new Set([
  SHELL_CACHE,
  STATIC_CACHE,
  PRODUCT_IMAGE_CACHE,
]);
const OFFLINE_URL = "/offline.html";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.add(new Request(OFFLINE_URL, { cache: "reload" })))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => !CURRENT_CACHES.has(key))
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

async function cacheResponse(cacheName, request, response, maxEntries) {
  if (!(response.ok || response.type === "opaque")) return;

  const cache = await caches.open(cacheName);
  await cache.put(request, response);

  if (!maxEntries) return;
  const keys = await cache.keys();
  await Promise.all(
    keys.slice(0, Math.max(0, keys.length - maxEntries)).map((key) =>
      cache.delete(key)
    )
  );
}

async function cacheFirst(request, cacheName, maxEntries) {
  const cached = await caches.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  await cacheResponse(cacheName, request, response.clone(), maxEntries).catch(
    () => undefined
  );
  return response;
}

async function staleWhileRevalidate(event, request, cacheName) {
  const cached = await caches.match(request);
  const networkResponse = fetch(request);
  const updateCache = networkResponse.then((response) =>
    cacheResponse(cacheName, request, response.clone())
  );
  event.waitUntil(updateCache.catch(() => undefined));

  return cached || networkResponse;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET" || request.headers.has("range")) return;

  const url = new URL(request.url);

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match(OFFLINE_URL).then(
          (fallback) =>
            fallback ||
            new Response("Offline", {
              status: 503,
              headers: { "Content-Type": "text/plain; charset=utf-8" },
            })
        )
      )
    );
    return;
  }

  if (url.origin === self.location.origin && url.pathname.startsWith("/api/")) {
    return;
  }

  if (
    url.origin === self.location.origin &&
    url.pathname.startsWith("/_next/static/")
  ) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  if (
    url.origin === self.location.origin &&
    (/\.(?:avif|css|gif|ico|jpe?g|png|svg|webp|woff2?)$/i.test(url.pathname) ||
      ["/brand/", "/products/", "/stores/"].some((prefix) =>
        url.pathname.startsWith(prefix)
      ))
  ) {
    event.respondWith(staleWhileRevalidate(event, request, STATIC_CACHE));
    return;
  }

  if (url.hostname === "images.openfoodfacts.org") {
    event.respondWith(cacheFirst(request, PRODUCT_IMAGE_CACHE, 200));
  }
});
