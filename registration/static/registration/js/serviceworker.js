// File: registration/static/registration/js/serviceworker.js

const CACHE_NAME = 'labor-registration-cache-v2'; // Incremented version
const DB_NAME = 'LaborRegistrationDB';
const DB_VERSION = 2;
const STORE_PENDING_REGISTRATIONS = 'pending_registrations';
const STORE_OFFLINE_IMAGES = 'offline_images';

const urlsToCache = [
    '/register/',
    '/register/registration/',
    '/register/success/',
    '/offline.html',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/idb@7/+esm',
    '/static/registration/js/multi_step_form_client.js',
    // Add other essential static assets like icons
    '/static/images/android-chrome-192x192.png',
    '/static/images/android-chrome-512x512.png',
];

// --- Install: Cache all essential assets ---
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] Caching all essential assets');
                return cache.addAll(urlsToCache);
            })
            .then(() => self.skipWaiting())
            .catch(error => {
                console.error('[Service Worker] Install failed:', error);
            })
    );
});

// --- Activate: Clean up old caches ---
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activating...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('[Service Worker] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            console.log('[Service Worker] Activated and claiming clients');
            return self.clients.claim();
        })
    );
});

// --- Fetch: Serve from cache or network (Cache-first strategy) ---
self.addEventListener('fetch', (event) => {
    if (event.request.method === 'GET') {
        event.respondWith(
            caches.match(event.request)
                .then((response) => {
                    // Cache hit - return response
                    if (response) {
                        return response;
                    }
                    // Not in cache - fetch from network
                    return fetch(event.request).catch(() => {
                        // If network fails (offline), and it's a navigation request, show offline page
                        if (event.request.mode === 'navigate') {
                            return caches.match('/offline.html');
                        }
                    });
                })
        );
    }
});

// --- Sync: Handle offline form submissions ---
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-labor-registration') {
        console.log('[Service Worker] Background sync triggered!');
        event.waitUntil(syncLaborRegistrations());
    }
});

// --- MODIFIED: Function to sync all pending registrations ---
async function syncLaborRegistrations() {
    // Import the idb library within the function scope
    const { openDB } = await import('https://cdn.jsdelivr.net/npm/idb@7/+esm');
    
    try {
        const db = await openDB(DB_NAME, DB_VERSION);
        const registrations = await db.getAll(STORE_PENDING_REGISTRATIONS);

        if (registrations.length === 0) {
            console.log('[Service Worker] No pending registrations to sync.');
            return;
        }
        
        console.log(`[Service Worker] Found ${registrations.length} pending registrations.`);
        
        let syncedCount = 0;
        let duplicateCount = 0;
        let failedCount = 0;

        const syncPromises = registrations.map(async (reg) => {
            try {
                const result = await syncSingleRegistration(reg, db);
                if (result === 'synced') syncedCount++;
                if (result === 'duplicate') duplicateCount++;
            } catch (error) {
                failedCount++;
                console.error(`[Service Worker] Sync failed for registration ID ${reg.id}, will retry later.`, error);
            }
        });

        await Promise.all(syncPromises);

        let notificationBody = '';
        if (syncedCount > 0) notificationBody += `${syncedCount} registration(s) successfully submitted. `;
        if (duplicateCount > 0) notificationBody += `${duplicateCount} duplicate(s) were cleared. `;
        
        if (notificationBody) {
            self.registration.showNotification('Registrations Synced!', {
                body: notificationBody.trim(),
                icon: '/static/images/android-chrome-192x192.png',
            });
        }
        
        console.log(`[Service Worker] Sync complete. Success: ${syncedCount}, Duplicates: ${duplicateCount}, Failed (will retry): ${failedCount}`);
        
    } catch (error) {
        console.error('[Service Worker] A critical error occurred during the sync process:', error);
        // Throwing here will cause the sync manager to retry the entire sync event later
        throw error;
    }
}

// --- MODIFIED: Function to process one registration, handles duplicates ---
async function syncSingleRegistration(reg, db) {
    const formData = new FormData();
    const allSteps = { ...reg.data.step1, ...reg.data.step2, ...reg.data.step3 };

    // Build FormData from all steps
    for (const key in allSteps) {
        if (Object.prototype.hasOwnProperty.call(allSteps, key)) {
            const value = allSteps[key];
            if (key !== 'photoId' && key !== 'photoBase64') {
                 if (Array.isArray(value) || (typeof value === 'object' && value !== null)) {
                    formData.append(key, JSON.stringify(value));
                } else if (value !== null && value !== undefined) {
                    formData.append(key, value);
                }
            }
        }
    }

    // Handle photo file from IndexedDB
    if (allSteps.photoId) {
        const imageData = await db.get(STORE_OFFLINE_IMAGES, allSteps.photoId);
        if (imageData && imageData.image) {
            formData.append('photo', imageData.image, imageData.name || 'captured_image.jpeg');
        }
    }
    
    const response = await fetch('/register/api/submit-registration/', {
        method: 'POST',
        body: formData,
    });
    
    const cleanup = async () => {
        const tx = db.transaction([STORE_PENDING_REGISTRATIONS, STORE_OFFLINE_IMAGES], 'readwrite');
        await tx.objectStore(STORE_PENDING_REGISTRATIONS).delete(reg.id);
        if (allSteps.photoId) {
            await tx.objectStore(STORE_OFFLINE_IMAGES).delete(allSteps.photoId);
        }
        await tx.done;
    };

    if (response.ok) {
        console.log(`[Service Worker] Synced registration ID ${reg.id}`);
        await cleanup();
        return 'synced';
    }

    if (response.status === 409) { // 409 Conflict for duplicates
        console.warn(`[Service Worker] Registration ID ${reg.id} is a duplicate. Clearing from device.`);
        await cleanup();
        return 'duplicate'; // This is a "handled" state, not a failure to be retried.
    }
    
    // For other server errors (5xx) or temporary network issues, throw an error
    // This will cause the sync manager to retry this specific item later.
    const errorText = await response.text();
    throw new Error(`Server responded with status ${response.status}: ${errorText}`);
}

// --- Message handler for manual sync trigger from client ---
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SYNC_NOW') {
        console.log('[Service Worker] Manual sync requested from client');
        syncLaborRegistrations().catch(error => {
            console.error('[Service Worker] Manual sync failed:', error);
        });
    }
});

// --- Notification click handler ---
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(clients.openWindow('/register/success/'));
});