/**
 * Service Worker - PWA & Caching
 * 
 * Bietet offline functionality und caching für den Sprachassistent
 * - Asset Caching (HTML, CSS, JS)
 * - API Response Caching
 * - Background Sync für Nachrichten
 * - Push Notifications Support
 */

const CACHE_VERSION = 'va-cache-v1.0.0';
const CACHE_NAME = `voice-assistant-${CACHE_VERSION}`;

/**
 * Cache Configuration
 */
const CacheConfig = {
  // Static assets to cache immediately
  staticAssets: [
    '/',
    '/index.html',
    '/index.js',
    '/core/dom-helpers.js',
    '/core/backend.js',
    '/core/audio.js',
    '/core/events.js',
    '/core/ws-utils.js',
    '/ui/sidebar.js',
    '/ui/hotkeys.js',
    '/workers/audio-streaming-worklet.js',
    '/manifest.json'
  ],
  
  // API patterns to cache
  apiPatterns: [
    /\/api\/.*$/,
    /\/health$/,
    /\/handshake$/
  ],
  
  // Cache strategies
  strategies: {
    static: 'cache-first',      // HTML, CSS, JS
    api: 'network-first',       // API calls
    audio: 'cache-first',       // Audio files
    images: 'cache-first'       // Images, icons
  },
  
  // Cache expiration times (milliseconds)
  maxAge: {
    static: 7 * 24 * 60 * 60 * 1000,   // 7 days
    api: 5 * 60 * 1000,                // 5 minutes
    audio: 30 * 24 * 60 * 60 * 1000,   // 30 days
    images: 30 * 24 * 60 * 60 * 1000   // 30 days
  }
};

/**
 * Install Event - Cache static assets
 */
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(CacheConfig.staticAssets);
      })
      .then(() => {
        console.log('[SW] Static assets cached successfully');
        // Force immediate activation
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Failed to cache static assets:', error);
      })
  );
});

/**
 * Activate Event - Clean old caches
 */
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    // Clean old caches
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME && cacheName.startsWith('voice-assistant-')) {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('[SW] Service worker activated');
        // Take control immediately
        return self.clients.claim();
      })
      .catch((error) => {
        console.error('[SW] Activation failed:', error);
      })
  );
});

/**
 * Fetch Event - Handle requests with caching strategies
 */
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);
  
  // Skip non-GET requests and chrome-extension requests
  if (request.method !== 'GET' || url.protocol === 'chrome-extension:') {
    return;
  }
  
  // Determine cache strategy based on request type
  const strategy = getCacheStrategy(request);
  
  event.respondWith(
    handleRequest(request, strategy)
      .catch((error) => {
        console.error('[SW] Request failed:', request.url, error);
        return getFallbackResponse(request);
      })
  );
});

/**
 * Determine cache strategy for request
 * @param {Request} request 
 * @returns {string}
 */
function getCacheStrategy(request) {
  const url = new URL(request.url);
  const pathname = url.pathname;
  
  // API requests
  if (CacheConfig.apiPatterns.some(pattern => pattern.test(pathname))) {
    return CacheConfig.strategies.api;
  }
  
  // Audio files
  if (pathname.match(/\.(mp3|wav|ogg|m4a)$/i)) {
    return CacheConfig.strategies.audio;
  }
  
  // Images
  if (pathname.match(/\.(png|jpg|jpeg|gif|svg|webp|ico)$/i)) {
    return CacheConfig.strategies.images;
  }
  
  // Static assets (JS, CSS, HTML)
  if (pathname.match(/\.(js|css|html)$/i) || pathname === '/') {
    return CacheConfig.strategies.static;
  }
  
  // Default to network-first
  return 'network-first';
}

/**
 * Handle request with specified strategy
 * @param {Request} request 
 * @param {string} strategy 
 * @returns {Promise<Response>}
 */
async function handleRequest(request, strategy) {
  switch (strategy) {
    case 'cache-first':
      return await cacheFirst(request);
    
    case 'network-first':
      return await networkFirst(request);
    
    case 'cache-only':
      return await cacheOnly(request);
    
    case 'network-only':
      return await networkOnly(request);
    
    default:
      return await networkFirst(request);
  }
}

/**
 * Cache First Strategy
 * @param {Request} request 
 * @returns {Promise<Response>}
 */
async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
    console.log('[SW] Cache hit:', request.url);
    return cachedResponse;
  }
  
  console.log('[SW] Cache miss, fetching:', request.url);
  const networkResponse = await fetch(request);
  
  // Cache successful responses
  if (networkResponse.ok) {
    cache.put(request, networkResponse.clone());
  }
  
  return networkResponse;
}

/**
 * Network First Strategy
 * @param {Request} request 
 * @returns {Promise<Response>}
 */
async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  
  try {
    console.log('[SW] Network first:', request.url);
    const networkResponse = await fetch(request);
    
    // Cache successful responses
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    throw error;
  }
}

/**
 * Cache Only Strategy
 * @param {Request} request 
 * @returns {Promise<Response>}
 */
async function cacheOnly(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  throw new Error(`No cached response for ${request.url}`);
}

/**
 * Network Only Strategy
 * @param {Request} request 
 * @returns {Promise<Response>}
 */
async function networkOnly(request) {
  return await fetch(request);
}

/**
 * Get fallback response for failed requests
 * @param {Request} request 
 * @returns {Response}
 */
function getFallbackResponse(request) {
  const url = new URL(request.url);
  const pathname = url.pathname;
  
  // HTML fallback
  if (request.headers.get('accept')?.includes('text/html')) {
    return new Response(
      generateOfflineHtml(),
      {
        status: 200,
        headers: { 'Content-Type': 'text/html' }
      }
    );
  }
  
  // API fallback
  if (CacheConfig.apiPatterns.some(pattern => pattern.test(pathname))) {
    return new Response(
      JSON.stringify({
        error: 'Offline - no cached response available',
        offline: true,
        timestamp: Date.now()
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
  
  // Generic fallback
  return new Response('Service temporarily unavailable', {
    status: 503,
    headers: { 'Content-Type': 'text/plain' }
  });
}

/**
 * Generate offline HTML fallback
 * @returns {string}
 */
function generateOfflineHtml() {
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>KI-Sprachassistent - Offline</title>
      <style>
        body {
          font-family: -apple-system, sans-serif;
          background: linear-gradient(135deg, #0a0a0f, #151520);
          color: white;
          margin: 0;
          padding: 40px;
          text-align: center;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
        }
        .offline-message {
          max-width: 400px;
          background: rgba(255,255,255,0.05);
          padding: 40px;
          border-radius: 20px;
          border: 1px solid rgba(255,255,255,0.1);
        }
        .offline-icon {
          font-size: 4rem;
          margin-bottom: 20px;
          opacity: 0.7;
        }
        h1 { color: #6366f1; margin-bottom: 10px; }
        p { color: #a1a1aa; line-height: 1.6; }
        .retry-btn {
          background: #6366f1;
          border: none;
          padding: 12px 24px;
          border-radius: 8px;
          color: white;
          cursor: pointer;
          margin-top: 20px;
          font-size: 16px;
        }
        .retry-btn:hover {
          background: #5855eb;
        }
      </style>
    </head>
    <body>
      <div class="offline-message">
        <div class="offline-icon">📱</div>
        <h1>Offline Modus</h1>
        <p>Der Sprachassistent ist momentan nicht verfügbar. 
           Bitte prüfen Sie Ihre Internetverbindung.</p>
        <button class="retry-btn" onclick="window.location.reload()">
          Erneut versuchen
        </button>
      </div>
    </body>
    </html>
  `;
}

/**
 * Background Sync - Queue failed requests
 */
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);
  
  if (event.tag === 'voice-message-sync') {
    event.waitUntil(syncVoiceMessages());
  }
});

/**
 * Sync queued voice messages
 */
async function syncVoiceMessages() {
  try {
    // Get queued messages from IndexedDB or cache
    const queuedMessages = await getQueuedMessages();
    
    for (const message of queuedMessages) {
      try {
        const response = await fetch('/api/voice-message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(message)
        });
        
        if (response.ok) {
          await removeQueuedMessage(message.id);
          console.log('[SW] Synced message:', message.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync message:', message.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Background sync failed:', error);
  }
}

/**
 * Push Notifications
 */
self.addEventListener('push', (event) => {
  console.log('[SW] Push message received');
  
  const options = {
    body: 'Neue Nachricht vom Sprachassistenten',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    vibrate: [200, 100, 200],
    data: {
      timestamp: Date.now(),
      url: '/'
    },
    actions: [
      {
        action: 'open',
        title: 'Öffnen',
        icon: '/icons/open-icon.png'
      },
      {
        action: 'dismiss',
        title: 'Schließen',
        icon: '/icons/close-icon.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(
      'KI-Sprachassistent',
      options
    )
  );
});

/**
 * Notification Click Handler
 */
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.action);
  event.notification.close();
  
  if (event.action === 'open' || !event.action) {
    event.waitUntil(
      self.clients.matchAll().then((clients) => {
        // Focus existing window if available
        for (const client of clients) {
          if (client.url.includes('/') && 'focus' in client) {
            return client.focus();
          }
        }
        
        // Open new window
        if (self.clients.openWindow) {
          return self.clients.openWindow('/');
        }
      })
    );
  }
});

/**
 * Message Handler - Communication with main thread
 */
self.addEventListener('message', (event) => {
  const { type, data } = event.data;
  
  switch (type) {
    case 'skip-waiting':
      self.skipWaiting();
      break;
      
    case 'cache-audio':
      cacheAudioFile(data.url);
      break;
      
    case 'clear-cache':
      clearCache();
      break;
      
    case 'get-cache-size':
      getCacheSize().then(size => {
        event.ports[0].postMessage({ type: 'cache-size', size });
      });
      break;
      
    default:
      console.log('[SW] Unknown message type:', type);
  }
});

/**
 * Cache specific audio file
 * @param {string} url 
 */
async function cacheAudioFile(url) {
  try {
    const cache = await caches.open(CACHE_NAME);
    const response = await fetch(url);
    if (response.ok) {
      await cache.put(url, response);
      console.log('[SW] Audio cached:', url);
    }
  } catch (error) {
    console.error('[SW] Failed to cache audio:', url, error);
  }
}

/**
 * Clear all caches
 */
async function clearCache() {
  try {
    const cacheNames = await caches.keys();
    await Promise.all(
      cacheNames.map(name => caches.delete(name))
    );
    console.log('[SW] All caches cleared');
  } catch (error) {
    console.error('[SW] Failed to clear cache:', error);
  }
}

/**
 * Get total cache size
 * @returns {Promise<number>}
 */
async function getCacheSize() {
  try {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const estimate = await navigator.storage.estimate();
      return estimate.usage || 0;
    }
    return 0;
  } catch (error) {
    console.error('[SW] Failed to get cache size:', error);
    return 0;
  }
}

// Placeholder functions for background sync (would need IndexedDB implementation)
async function getQueuedMessages() {
  return [];
}

async function removeQueuedMessage(id) {
  // Implementation would remove message from IndexedDB
  console.log('[SW] Message removed from queue:', id);
}

// Error handler for unhandled service worker errors
self.addEventListener('error', (event) => {
  console.error('[SW] Service worker error:', event.error);
});

self.addEventListener('unhandledrejection', (event) => {
  console.error('[SW] Unhandled promise rejection:', event.reason);
});

console.log(`[SW] Service Worker ${CACHE_VERSION} loaded`);
