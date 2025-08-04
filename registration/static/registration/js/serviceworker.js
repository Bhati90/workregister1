// registration/static/registration/js/serviceworker.js

const CACHE_NAME = 'labor-registration-cache-v1'; // Keep this name consistent
const DB_NAME = 'LaborRegistrationDB'; // Must match client-side JS
const DB_VERSION = 2; // Must match client-side JS. Increment this if schema changes!
const STORE_PENDING_REGISTRATIONS = 'pending_registrations'; // Must match client-side JS
const STORE_OFFLINE_IMAGES = 'offline_images'; // Must match client-side JS

const urlsToCache = [
    // Basic app shell URLs
    '/register/', // The entry point for your form
    '/register/?step=1', // Explicitly cache query parameters if they define pages
    '/register/?step=2',
    '/register/?step=3',
    '/success/', // The success page URL as used in the client-side JS
    '/offline.html', // Your offline fallback page

    // Static assets used by your templates
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    '/static/registration/js/multi_step_form_client.js',
    '/static/registration/images/my_app_icon_192.png',
    '/static/registration/images/my_app_icon_512.png',
    '/static/registration/images/splash_screen_480x320.png',
];

// Installation: Cache all essential assets
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] Caching all assets:', urlsToCache);
                return Promise.allSettled(urlsToCache.map(url => cache.add(url)))
                    .then((results) => {
                        results.forEach(result => {
                            if (result.status === 'rejected') {
                                console.warn(`[Service Worker] Failed to cache ${result.reason.url || 'a URL'}: ${result.reason.message}`);
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
        }).then(() => self.clients.claim())
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
    if (event.tag === 'sync-labor-registration') {
        console.log('[Service Worker] Background sync triggered for labor registration!');
        event.waitUntil(syncLaborRegistrations());
    }
});

// Function to send offline registrations from IndexedDB to the server
async function syncLaborRegistrations() {
    console.log('[Service Worker] Attempting to sync offline registrations...');
    const { openDB } = await import('https://cdn.jsdelivr.net/npm/idb@7/+esm');

    let db;
    try {
        db = await openDB(DB_NAME, DB_VERSION);
    } catch (error) {
        console.error('[Service Worker] Failed to open IndexedDB during sync:', error);
        throw error;
    }

    const tx = db.transaction([STORE_PENDING_REGISTRATIONS, STORE_OFFLINE_IMAGES], 'readwrite');
    const pendingStore = tx.objectStore(STORE_PENDING_REGISTRATIONS);
    const imageStore = tx.objectStore(STORE_OFFLINE_IMAGES);

    const registrations = await pendingStore.getAll();

    if (registrations.length === 0) {
        console.log('[Service Worker] No pending registrations to sync.');
        await tx.done;
        return;
    }

    console.log(`[Service Worker] Found ${registrations.length} pending registrations to sync.`);

    for (const reg of registrations) {
        try {
            const formData = new FormData();
            const step1Data = reg.data.step1 || {};
            const step2Data = reg.data.step2 || {};
            const step3Data = reg.data.step3 || {};
            
            // Append all basic_info data
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
                    console.warn(`[Service Worker] Image with ID ${step1Data.photoId} not found in offline_images store during sync.`);
                }
            } else if (step1Data.photoBase64) {
                 try {
                    const blob = await (await fetch(step1Data.photoBase64)).blob();
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

            const response = await fetch('/api/submit-registration/', {
                method: 'POST',
                body: formData,
                // Do not explicitly set Content-Type for FormData
                // The browser will handle the 'multipart/form-data' header automatically
                // No headers are needed for CSRF with @csrf_exempt on the server-side
            });

            if (response.ok) {
                console.log(`[Service Worker] Registration ID ${reg.id} synced successfully!`);
                await pendingStore.delete(reg.id);
                if (step1Data.photoId) {
                    await imageStore.delete(step1Data.photoId);
                }
                self.registration.showNotification('Registration Synced!', {
                    body: `Registration for ${step1Data.full_name || 'an applicant'} has been submitted.`,
                    icon: '/static/registration/images/android-chrome-192x192.png'
                });
            } else {
                const errorText = await response.text();
                console.error(`[Service Worker] Failed to sync registration ID ${reg.id}:`, response.status, errorText);
                throw new Error(`Server responded with status ${response.status}: ${errorText}`);
            }
        } catch (error) {
            console.error(`[Service Worker] Error during sync for registration ID ${reg.id}:`, error);
            throw error;
        }
    }
    await tx.done;
    console.log('[Service Worker] All pending syncs attempted.');
}