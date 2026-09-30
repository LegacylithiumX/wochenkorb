// Offline-Speicher: immer zuerst das Netz (frische Preise), bei Funkloch im Laden die zuletzt geladene Fassung.
const CACHE = 'wochenkorb-v1';
const START = ['./', './index.html', './daten/preise.json', './manifest.webmanifest', './icons/icon-192.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(START)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  e.respondWith(
    fetch(e.request)
      .then(antwort => {
        if (antwort.ok) { const kopie = antwort.clone(); caches.open(CACHE).then(c => c.put(e.request, kopie)); }
        return antwort;
      })
      .catch(() => caches.match(e.request, {ignoreSearch: true}).then(r => r || caches.match('./index.html')))
  );
});
