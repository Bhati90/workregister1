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
    '/registration-success/', // Your success page
    '/offline.html', // Your offline fallback page

    // Static assets used by your templates
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    // Assuming your main JS is moved to a separate file within your static folder
    '/static/registration/js/multi_step_form_client.js',
    '/static/registration/images/my_app_icon_192.png',
    '/static/registration/images/my_app_icon_512.png',
    '/static/registration/images/splash_screen_480x320.png',
    // Add other common static assets like your custom CSS file if you have one
    // '/static/registration/css/style.css',
];

// Installation: Cache all essential assets
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] Caching all assets:', urlsToCache);
                // Use Promise.allSettled to ensure all are attempted, even if some fail
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
            .then(() => self.skipWaiting()) // Activates the new service worker immediately
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
        }).then(() => self.clients.claim()) // Takes control of existing clients immediately
    );
});

// Fetch: Serve from cache or network
self.addEventListener('fetch', (event) => {
    // Only handle GET requests for navigation and static assets
    if (event.request.method === 'GET') {
        event.respondWith(
            caches.match(event.request)
                .then((response) => {
                    // Cache hit - return response
                    if (response) {
                        return response;
                    }
                    // No cache hit - fetch from network
                    return fetch(event.request)
                        .then((networkResponse) => {
                            // Check if we received a valid response
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
                            // If network fails for a navigation request, serve offline fallback
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
        throw error; // Re-throw to make the sync event retry
    }

    const tx = db.transaction([STORE_PENDING_REGISTRATIONS, STORE_OFFLINE_IMAGES], 'readwrite');
    const pendingStore = tx.objectStore(STORE_PENDING_REGISTRATIONS);
    const imageStore = tx.objectStore(STORE_OFFLINE_IMAGES);

    const registrations = await pendingStore.getAll();

    if (registrations.length === 0) {
        console.log('[Service Worker] No pending registrations to sync.');
        return;
    }

    console.log(`[Service Worker] Found ${registrations.length} pending registrations to sync.`);

    // Process each registration one by one
    for (const reg of registrations) {
        try {
            const formData = new FormData();

            // Get nested step data
            const step1Data = reg.data.step1 || {};
            const step2Data = reg.data.step2 || {};
            const step3Data = reg.data.step3 || {};

            // Append all basic_info data
            for (const key in step1Data) {
                if (step1Data.hasOwnProperty(key) && key !== 'photoId' && key !== 'photoBase64' && key !== 'location') {
                    formData.append(key, step1Data[key]);
                }
            }
            if (step1Data.location) { // Location object
                formData.append('location', JSON.stringify(step1Data.location));
            }

            // Handle photo file
            if (step1Data.photoId) {
                const imageData = await imageStore.get(step1Data.photoId);
                if (imageData && imageData.image) {
                    formData.append('photo', imageData.image, imageData.name || 'captured_image.jpeg');
                    console.log(`[Service Worker] Appending image ID ${step1Data.photoId} to form data.`);
                } else {
                    console.warn(`[Service Worker] Image with ID ${step1Data.photoId} not found in offline_images store during sync.`);
                }
            } else if (step1Data.photoBase64) {
                // Fallback for base64 if it was stored this way
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
                    // Convert arrays (like skills, comm_preferences) and other objects to JSON strings
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

            // Attempt to fetch a CSRF token from a cached page.
            const csrfToken = await getCsrfTokenFromCachedPage('/register/');
            const headers = {};
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            console(`[Service Worker] Sending registration ID ${reg.id} to server...`);
            const response = await fetch('/register/api/submit-registration/', {
                method: 'POST',
                body: formData,
                headers: headers
            });

            if (response.ok) {
                console.log(`[Service Worker] Registration ID ${reg.id} synced successfully!`);
                await pendingStore.delete(reg.id); // Remove from pending store
                if (step1Data.photoId) { // Also remove the image if it was associated and uploaded
                    await imageStore.delete(step1Data.photoId);
                }
                self.registration.showNotification('Registration Synced!', {
                    body: `Registration for ${step1Data.full_name || 'an applicant'} has been submitted.`,
                    icon: '/static/registration/images/my_app_icon_192.png'
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

// Helper to try and get CSRF token from a cached page
async function getCsrfTokenFromCachedPage(pageUrl) {
    try {
        const cache = await caches.open(CACHE_NAME);
        const response = await cache.match(pageUrl);
        if (response) {
            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const csrfInput = doc.querySelector('input[name="csrfmiddlewaretoken"]');
            return csrfInput ? csrfInput.value : null;
        }
    } catch (error) {
        console.warn('[Service Worker] Could not retrieve CSRF token from cache for URL:', pageUrl, error);
    }
    return null;
}