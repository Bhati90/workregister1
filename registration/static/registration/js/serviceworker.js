// registration/static/registration/js/serviceworker.js

const CACHE_NAME = 'labor-registration-cache-v1';
const DB_NAME = 'LaborRegistrationDB';
const DB_VERSION = 2;
const STORE_PENDING_REGISTRATIONS = 'pending_registrations';
const STORE_OFFLINE_IMAGES = 'offline_images';

const urlsToCache = [
    '/register/',
    '/register/registration/',
    '/register/registration/?step=1',
    '/register/registration/?step=2',
    '/register/registration/?step=3',
    '/register/success/',
    '/offline.html',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/idb@7/+esm', // Cache the idb library
    '/static/registration/js/multi_step_form_client.js',
    '/static/registration/images/my_app_icon_192.png',
    '/static/registration/images/my_app_icon_512.png',
    '/static/registration/images/splash_screen_480x320.png',
    '/static/images/android-chrome-192x192.png',
    '/static/images/android-chrome-512x512.png',
];

// Import idb at the top level (cached version)
let idbModule = null;

async function getIDB() {
    if (!idbModule) {
        try {
            idbModule = await import('https://cdn.jsdelivr.net/npm/idb@7/+esm');
        } catch (error) {
            console.error('[Service Worker] Failed to import idb:', error);
            throw error;
        }
    }
    return idbModule;
}

// Installation: Cache all essential assets
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] Caching all assets:', urlsToCache);
                return Promise.allSettled(urlsToCache.map(url => cache.add(url)))
                    .then((results) => {
                        results.forEach((result, index) => {
                            if (result.status === 'rejected') {
                                console.warn(`[Service Worker] Failed to cache ${urlsToCache[index]}: ${result.reason.message}`);
                            }
                        });
                        console.log('[Service Worker] Initial caching complete.');
                    });
            })
            .then(() => self.skipWaiting())
            .catch(error => {
                console.error('[Service Worker] Install failed:', error);
            })
    );
});

// Activation: Clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activating...');
    const cacheWhitelist = [CACHE_NAME];
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheWhitelist.indexOf(cacheName) === -1) {
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

// Fetch: Serve from cache or network
self.addEventListener('fetch', (event) => {
    if (event.request.method === 'GET') {
        event.respondWith(
            caches.match(event.request)
                .then((response) => {
                    if (response) {
                        return response;
                    }
                    return fetch(event.request)
                        .then((networkResponse) => {
                            if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                                return networkResponse;
                            }
                            const responseToCache = networkResponse.clone();
                            caches.open(CACHE_NAME)
                                .then((cache) => {
                                    cache.put(event.request, responseToCache);
                                });
                            return networkResponse;
                        })
                        .catch(() => {
                            if (event.request.mode === 'navigate') {
                                return caches.match('/offline.html');
                            }
                            return new Response('<p>You are offline and this content is not available.</p>', {
                                headers: { 'Content-Type': 'text/html' }
                            });
                        });
                })
        );
    }
});

// Background Sync: Handle offline form submissions
self.addEventListener('sync', (event) => {
    console.log('[Service Worker] Sync event received with tag:', event.tag);
    
    if (event.tag === 'sync-labor-registration') {
        console.log('[Service Worker] Background sync triggered for labor registration!');
        event.waitUntil(syncLaborRegistrations());
    }
});

// Function to send offline registrations from IndexedDB to the server
async function syncLaborRegistrations() {
    console.log('[Service Worker] Attempting to sync offline registrations...');
    
    try {
        // Check if we're online
        if (!navigator.onLine) {
            console.log('[Service Worker] Still offline, sync will retry later');
            throw new Error('Still offline');
        }

        const { openDB } = await getIDB();
        
        const db = await openDB(DB_NAME, DB_VERSION, {
            upgrade(db) {
                // Create stores if they don't exist
                if (!db.objectStoreNames.contains(STORE_PENDING_REGISTRATIONS)) {
                    db.createObjectStore(STORE_PENDING_REGISTRATIONS, { keyPath: 'id' });
                }
                if (!db.objectStoreNames.contains(STORE_OFFLINE_IMAGES)) {
                    db.createObjectStore(STORE_OFFLINE_IMAGES, { keyPath: 'id' });
                }
            }
        });
        
        const tx = db.transaction([STORE_PENDING_REGISTRATIONS, STORE_OFFLINE_IMAGES], 'readwrite');
        const pendingStore = tx.objectStore(STORE_PENDING_REGISTRATIONS);
        const imageStore = tx.objectStore(STORE_OFFLINE_IMAGES);
        
        const registrations = await pendingStore.getAll();
        
        if (registrations.length === 0) {
            console.log('[Service Worker] No pending registrations to sync.');
            return;
        }
        
        console.log(`[Service Worker] Found ${registrations.length} pending registrations to sync.`);
        
        let syncedCount = 0;
        let failedCount = 0;
        
        for (const reg of registrations) {
            try {
                await syncSingleRegistration(reg, pendingStore, imageStore);
                syncedCount++;
                console.log(`[Service Worker] Registration ID ${reg.id} synced successfully! (${syncedCount}/${registrations.length})`);
            } catch (error) {
                failedCount++;
                console.error(`[Service Worker] Failed to sync registration ID ${reg.id}:`, error);
                // Continue with other registrations instead of stopping
            }
        }
        
        // Show notification based on results
        if (syncedCount > 0) {
            self.registration.showNotification('Registrations Synced!', {
                body: `${syncedCount} registration(s) successfully submitted.${failedCount > 0 ? ` ${failedCount} failed.` : ''}`,
                icon: '/static/images/android-chrome-192x192.png',
                badge: '/static/images/android-chrome-192x192.png',
                tag: 'sync-complete',
                requireInteraction: true
            });
        }
        
        console.log(`[Service Worker] Sync complete. Success: ${syncedCount}, Failed: ${failedCount}`);
        
    } catch (error) {
        console.error('[Service Worker] Sync failed:', error);
        throw error; // Re-throw to trigger retry
    }
}

async function syncSingleRegistration(reg, pendingStore, imageStore) {
    const formData = new FormData();
    const step1Data = reg.data.step1 || {};
    const step2Data = reg.data.step2 || {};
    const step3Data = reg.data.step3 || {};
    
    // Append step 1 data
    for (const key in step1Data) {
        if (step1Data.hasOwnProperty(key) && key !== 'photoId' && key !== 'photoBase64' && key !== 'location') {
            formData.append(key, step1Data[key]);
        }
    }
    
    if (step1Data.location) {
        formData.append('location', JSON.stringify(step1Data.location));
    }
    
    // Handle photo file from IndexedDB
    if (step1Data.photoId) {
        const imageData = await imageStore.get(step1Data.photoId);
        if (imageData && imageData.image) {
            formData.append('photo', imageData.image, imageData.name || 'captured_image.jpeg');
            console.log(`[Service Worker] Appending image ID ${step1Data.photoId} to form data.`);
        } else {
            console.warn(`[Service Worker] Image with ID ${step1Data.photoId} not found in offline_images store.`);
        }
    } else if (step1Data.photoBase64) {
        try {
            const response = await fetch(step1Data.photoBase64);
            const blob = await response.blob();
            formData.append('photo', blob, 'captured_image.jpeg');
            console.log('[Service Worker] Appending base64 image to form data.');
        } catch (e) {
            console.warn('[Service Worker] Failed to convert base64 to Blob for sync:', e);
        }
    }
    
    // Append step 2 data
    for (const key in step2Data) {
        if (step2Data.hasOwnProperty(key)) {
            if (Array.isArray(step2Data[key]) || (typeof step2Data[key] === 'object' && step2Data[key] !== null)) {
                formData.append(key, JSON.stringify(step2Data[key]));
            } else {
                formData.append(key, step2Data[key]);
            }
        }
    }
    
    // Append step 3 data
    if (step3Data.data_sharing_agreement !== undefined) {
        formData.append('data_sharing_agreement', step3Data.data_sharing_agreement);
    }
    
    // Submit to server
    const response = await fetch('/register/api/submit-registration/', {
        method: 'POST',
        body: formData,
    });
    
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Server responded with status ${response.status}: ${errorText}`);
    }
    
    // If successful, remove from pending store and clean up images
    await pendingStore.delete(reg.id);
    if (step1Data.photoId) {
        await imageStore.delete(step1Data.photoId);
    }
}

// Handle messages from client
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SYNC_NOW') {
        console.log('[Service Worker] Manual sync requested from client');
        // Manually trigger sync
        syncLaborRegistrations().catch(error => {
            console.error('[Service Worker] Manual sync failed:', error);
        });
    }
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    if (event.notification.tag === 'sync-complete') {
        // Open the app when notification is clicked
        event.waitUntil(
            clients.openWindow('/register/success/')
        );
    }
});
