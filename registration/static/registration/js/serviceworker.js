// registration/static/registration/js/serviceworker.js

const CACHE_NAME = 'labor-registration-cache-v2';
const DB_NAME = 'LaborRegistrationDB';
const DB_VERSION = 2;
const STORE_PENDING_REGISTRATIONS = 'pending_registrations';
const STORE_OFFLINE_IMAGES = 'offline_images';

// CLOUDINARY_URL  cloudinary://196762722111821:nKpyWbKl0UAdaqgkjI9W0HpQkR4@df8f5bxfp
// const urlsToCache = [
//     // Core Registration Flow (Existing)
//     '/register/',
//     '/register/registration/',
//     '/register/success/',
//     '/offline.html',

//     // Authentication
//     '/register/login/',

//     // Main User Dashboards
//     '/register/dashboard/',
//     '/register/leader/dashboard/',
//     '/register/mukadam/dashboard/',

//     // Key Leader Views
//     '/register/leader/confirmations/',
//     '/register/leader/ongoing-jobs/',
//     '/register/leader/bids/',

//     // Static Assets (Existing)
//     'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
//     'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
//     'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
//     '/static/registration/js/multi_step_form_client.js',
//     '/static/registration/js/idb.js', // Assuming you have a local copy of idb.js

//     // App Icons (Existing)
//     '/static/images/android-chrome-192x192.png',
//     '/static/images/android-chrome-512x512.png',
// ];
const urlsToCache = [
    // '/register/',
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

/**
 * Converts a Blob to a Base64 string.
 * @param {Blob} blob The blob to convert.
 * @returns {Promise<string>} A promise that resolves with the Base64 string.
 */
function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

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
// async function syncLaborRegistrations() {
//     console.log('[Service Worker] Attempting to sync offline registrations...');
    
//     try {
//         // Check if we're online
//         if (!navigator.onLine) {
//             console.log('[Service Worker] Still offline, sync will retry later');
//             throw new Error('Still offline');
//         }

//         const { openDB } = await getIDB();
        
//         const db = await openDB(DB_NAME, DB_VERSION, {
//             upgrade(db) {
//                 // Create stores if they don't exist
//                 if (!db.objectStoreNames.contains(STORE_PENDING_REGISTRATIONS)) {
//                     db.createObjectStore(STORE_PENDING_REGISTRATIONS, { keyPath: 'id' });
//                 }
//                 if (!db.objectStoreNames.contains(STORE_OFFLINE_IMAGES)) {
//                     db.createObjectStore(STORE_OFFLINE_IMAGES, { keyPath: 'id' });
//                 }
//             }
//         });
        
//         const tx = db.transaction([STORE_PENDING_REGISTRATIONS, STORE_OFFLINE_IMAGES], 'readwrite');
//         const pendingStore = tx.objectStore(STORE_PENDING_REGISTRATIONS);
//         const imageStore = tx.objectStore(STORE_OFFLINE_IMAGES);
        
//         const registrations = await pendingStore.getAll();
        
//         if (registrations.length === 0) {
//             console.log('[Service Worker] No pending registrations to sync.');
//             return;
//         }
        
//         console.log(`[Service Worker] Found ${registrations.length} pending registrations to sync.`);
        
//         let syncedCount = 0;
//         let failedCount = 0;
        
//         for (const reg of registrations) {
//             try {
//                 await syncSingleRegistration(reg, pendingStore, imageStore);
//                 syncedCount++;
//                 console.log(`[Service Worker] Registration ID ${reg.id} synced successfully! (${syncedCount}/${registrations.length})`);
//             } catch (error) {
//                 failedCount++;
//                 console.error(`[Service Worker] Failed to sync registration ID ${reg.id}:`, error);
//                 // Continue with other registrations instead of stopping
//             }
//         }
        
//         // Show notification based on results
//         if (syncedCount > 0) {
//             self.registration.showNotification('Registrations Synced!', {
//                 body: `${syncedCount} registration(s) successfully submitted.${failedCount > 0 ? ` ${failedCount} failed.` : ''}`,
//                 icon: '/static/images/android-chrome-192x192.png',
//                 badge: '/static/images/android-chrome-192x192.png',
//                 tag: 'sync-complete',
//                 requireInteraction: true
//             });
//         }
        
//         console.log(`[Service Worker] Sync complete. Success: ${syncedCount}, Failed: ${failedCount}`);
        
//     } catch (error) {
//         console.error('[Service Worker] Sync failed:', error);
//         throw error; // Re-throw to trigger retry
//     }
// }


async function syncLaborRegistrations() {
    // This function remains largely the same, it just calls the corrected syncSingleRegistration
    try {
        if (!navigator.onLine) throw new Error('Still offline');
        const { openDB } = await getIDB();
        const db = await openDB(DB_NAME, DB_VERSION);
        const tx = db.transaction([STORE_PENDING_REGISTRATIONS, STORE_OFFLINE_IMAGES], 'readwrite');
        const pendingStore = tx.objectStore(STORE_PENDING_REGISTRATIONS);
        const imageStore = tx.objectStore(STORE_OFFLINE_IMAGES);
        const registrations = await pendingStore.getAll();

        if (registrations.length === 0) {
            console.log('[Service Worker] No pending registrations to sync.');
            return;
        }

        console.log(`[Service Worker] Found ${registrations.length} pending registrations.`);
        const syncPromises = registrations.map(reg => syncSingleRegistration(reg, pendingStore, imageStore));
        await Promise.all(syncPromises);

        self.registration.showNotification('Registrations Synced!', {
            body: `${registrations.length} offline registration(s) were successfully submitted.`,
            icon: '/static/images/android-chrome-192x192.png',
        });

    } catch (error) {
        console.error('[Service Worker] Sync failed:', error);
        throw error; // Re-throw to let the browser know it should retry later
    }
}
// async function syncSingleRegistration(reg, pendingStore, imageStore) {
//     const formData = new FormData();
//     const step1Data = reg.data.step1 || {};
//     const step2Data = reg.data.step2 || {};
//     const step3Data = reg.data.step3 || {};
    
//     // Append step 1 data
//     for (const key in step1Data) {
//         if (step1Data.hasOwnProperty(key) && key !== 'photoId' && key !== 'photoBase64' && key !== 'location') {
//             formData.append(key, step1Data[key]);
//         }
//     }
    
//     if (step1Data.location) {
//         formData.append('location', JSON.stringify(step1Data.location));
//     }
    
//     // Handle photo file from IndexedDB
//     if (step1Data.photoId) {
//         const imageData = await imageStore.get(step1Data.photoId);
//         if (imageData && imageData.image) {
//             formData.append('photo', imageData.image, imageData.name || 'captured_image.jpeg');
//             console.log(`[Service Worker] Appending image ID ${step1Data.photoId} to form data.`);
//         } else {
//             console.warn(`[Service Worker] Image with ID ${step1Data.photoId} not found in offline_images store.`);
//         }
//     } else if (step1Data.photoBase64) {
//         try {
//             const response = await fetch(step1Data.photoBase64);
//             const blob = await response.blob();
//             formData.append('photo', blob, 'captured_image.jpeg');
//             console.log('[Service Worker] Appending base64 image to form data.');
//         } catch (e) {
//             console.warn('[Service Worker] Failed to convert base64 to Blob for sync:', e);
//         }
//     }

//        let imageAppended = false;
//     // Try to get image from IndexedDB using photoId
//     if (step1Data.photoId) {
//         try {
//             const imageData = await imageStore.get(step1Data.photoId);
//             if (imageData && imageData.image) {
//                 const imageBlob = imageData.image;
//                 // NEW: Convert the blob to a Base64 string
//                 const base64String = await blobToBase64(imageBlob);
//                 // NEW: Append the base64 string as a text field
//                 formData.append('photo_base64', base64String);
//                 imageAppended = true;
//                 console.log(`[Service Worker] Image (ID: ${step1Data.photoId}) successfully converted to Base64 and appended.`);
//             }
//         } catch (error) {
//             console.error(`[Service Worker] Error processing image ID ${step1Data.photoId}:`, error);
//         }
//     }

//     // Fallback to existing base64 string if photoId method fails
//     if (!imageAppended && step1Data.photoBase64) {
//         formData.append('photo_base64', step1Data.photoBase64);
//        console.log('[Service Worker] Appending existing photoBase64 from draft.');
//     }

//     // --- END OF MODIFIED IMAGE HANDLING ---

//     // Append step 2 data
//     for (const key in step2Data) {
//         if (step2Data.hasOwnProperty(key)) {
//             if (Array.isArray(step2Data[key]) || (typeof step2Data[key] === 'object' && step2Data[key] !== null)) {
//                 formData.append(key, JSON.stringify(step2Data[key]));
//             } else {
//                 formData.append(key, step2Data[key]);
//             }
//         }
//     }
    
//     // Append step 3 data
//     if (step3Data.data_sharing_agreement !== undefined) {
//         formData.append('data_sharing_agreement', step3Data.data_sharing_agreement);
//     }
    
//     // Submit to server
//     const response = await fetch('/register/api/submit-registration/', {
//         method: 'POST',
//         body: formData,
//     });
    
//     if (!response.ok) {
//         const errorText = await response.text();
//         throw new Error(`Server responded with status ${response.status}: ${errorText}`);
//     }
    
//     // If successful, remove from pending store and clean up images
//     await pendingStore.delete(reg.id);
//     if (step1Data.photoId) {
//         await imageStore.delete(step1Data.photoId);
//     }
// }
async function syncSingleRegistration(reg, pendingStore, imageStore) {
    const formData = new FormData();
    const { step1, step2, step3 } = reg.data;

    // Append all text data from all steps
    const allSteps = { ...step1, ...step2, ...step3 };
    for (const key in allSteps) {
        if (Object.prototype.hasOwnProperty.call(allSteps, key) && key !== 'photoId' && key !== 'photoBase64') {
            const value = allSteps[key];
            if (typeof value === 'object' && value !== null) {
                formData.append(key, JSON.stringify(value));
            } else {
                formData.append(key, value);
            }
        }
    }

    // --- CORRECTED IMAGE HANDLING ---
    // This now exclusively uses the reliable Base64 method for offline syncs.
    if (step1.photoId) {
        try {
            const imageData = await imageStore.get(step1.photoId);
            if (imageData && imageData.image) {
                const base64String = await blobToBase64(imageData.image);
                formData.append('photo_base64', base64String);
                console.log(`[Service Worker] Image (ID: ${step1.photoId}) successfully converted to Base64 and appended.`);
            }
        } catch (error) {
            console.error(`[Service Worker] Error processing image for sync:`, error);
        }
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
    if (step1.photoId) {
        await imageStore.delete(step1.photoId);
    }
    console.log(`[Service Worker] Registration ID ${reg.id} synced and cleaned up successfully.`);
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

// Add this function to check mobile number duplicates
async function checkMobileNumberDuplicate(mobileNumber) {
    try {
        const response = await fetch('/register/api/check-mobile-number/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mobile_number: mobileNumber
            })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('[Service Worker] Error checking mobile number:', error);
        return { exists: false, message: 'Unable to check mobile number' };
    }
}

// Updated syncSingleRegistration function
async function syncSingleRegistration(reg, pendingStore, imageStore) {
    const mobileNumber = reg.data.step1?.mobile_number;
    
    // Check for duplicate mobile number before syncing
    if (mobileNumber) {
        console.log(`[Service Worker] Checking duplicate for mobile: ${mobileNumber}`);
        const duplicateCheck = await checkMobileNumberDuplicate(mobileNumber);
        
        if (duplicateCheck.exists) {
            console.warn(`[Service Worker] Duplicate mobile number found: ${mobileNumber}. Removing from offline storage.`);
            
            // Remove from pending store and clean up images
            await pendingStore.delete(reg.id);
            if (reg.data.step1?.photoId) {
                await imageStore.delete(reg.data.step1.photoId);
            }
            
            // Show notification about duplicate removal
            self.registration.showNotification('Duplicate Registration Removed', {
                body: `Registration with mobile number ${mobileNumber} was removed as it already exists in database.`,
                icon: '/static/images/android-chrome-192x192.png',
                badge: '/static/images/android-chrome-192x192.png',
                tag: 'duplicate-removed',
                requireInteraction: true
            });
            
            throw new Error(`Duplicate mobile number: ${mobileNumber}. Registration removed from offline storage.`);
        }
    }
    
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
    
    // Handle image with improved logic
    let imageAppended = false;
    
    // Priority 1: Try to get image from IndexedDB using photoId
    if (step1Data.photoId) {
        try {
            const imageData = await imageStore.get(step1Data.photoId);
            if (imageData && imageData.image) {
                let imageBlob = imageData.image;
                
                // Ensure we have a valid Blob
                if (!(imageBlob instanceof Blob)) {
                    if (typeof imageBlob === 'string' && imageBlob.startsWith('data:')) {
                        // Convert base64 string to Blob
                        const response = await fetch(imageBlob);
                        imageBlob = await response.blob();
                    }
                }
                
                if (imageBlob instanceof Blob && imageBlob.size > 0) {
                    formData.append('photo', imageBlob, imageData.name || 'captured_image.jpeg');
                    imageAppended = true;
                    console.log(`[Service Worker] Image from IndexedDB (ID: ${step1Data.photoId}) appended successfully. Size: ${imageBlob.size} bytes`);
                }
            }
        } catch (error) {
            console.error(`[Service Worker] Error retrieving image ID ${step1Data.photoId} from IndexedDB:`, error);
        }
    }
    
    // Priority 2: Fallback to base64 if no image was appended from IndexedDB
    if (!imageAppended && step1Data.photoBase64) {
        try {
            const response = await fetch(step1Data.photoBase64);
            const blob = await response.blob();
            
            if (blob.size > 0) {
                formData.append('photo', blob, 'captured_image.jpeg');
                imageAppended = true;
                console.log(`[Service Worker] Image from base64 fallback appended successfully. Size: ${blob.size} bytes`);
            }
        } catch (error) {
            console.warn('[Service Worker] Failed to convert base64 to Blob for sync:', error);
        }
    }
    
    if (!imageAppended) {
        console.warn('[Service Worker] No image was found or appended for this registration');
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
    
    // Debug FormData contents
    console.log('[Service Worker] --- FormData Contents ---');
    for (const pair of formData.entries()) {
        if (pair[0] === 'photo') {
            console.log(`[Service Worker] ${pair[0]}: [File Blob - ${pair[1].size} bytes, type: ${pair[1].type}]`);
        } else {
            console.log(`[Service Worker] ${pair[0]}: ${pair[1]}`);
        }
    }
    console.log('[Service Worker] --- End FormData Contents ---');
    
    // Submit to server
    const response = await fetch('/register/api/submit-registration/', {
        method: 'POST',
        body: formData,
    });
    
    if (!response.ok) {
        const errorText = await response.text();
        let errorData;
        
        try {
            errorData = JSON.parse(errorText);
        } catch (e) {
            errorData = { message: errorText };
        }
        
        // Handle duplicate mobile number error from server
        if (errorData.error_type === 'duplicate_mobile') {
            console.warn(`[Service Worker] Server confirmed duplicate mobile number: ${mobileNumber}`);
            
            // Remove from pending store and clean up images
            await pendingStore.delete(reg.id);
            if (step1Data.photoId) {
                await imageStore.delete(step1Data.photoId);
            }
            
            // Show notification about duplicate
            self.registration.showNotification('Duplicate Registration Removed', {
                body: `Registration with mobile number ${mobileNumber} was removed as it already exists in database.`,
                icon: '/static/images/android-chrome-192x192.png',
                badge: '/static/images/android-chrome-192x192.png',
                tag: 'duplicate-removed',
                requireInteraction: true
            });
            
            throw new Error(`Server confirmed duplicate: ${errorData.message}`);
        }
        
        throw new Error(`Server responded with status ${response.status}: ${errorData.message || errorText}`);
    }
    
    // If successful, remove from pending store and clean up images
    await pendingStore.delete(reg.id);
    if (step1Data.photoId) {
        await imageStore.delete(step1Data.photoId);
        console.log(`[Service Worker] Image ID ${step1Data.photoId} cleaned up from IndexedDB`);
    }
    
    console.log(`[Service Worker] Registration for ${step1Data.full_name} synced successfully`);
}

// Updated syncLaborRegistrations function with better error handling
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
        let duplicateCount = 0;
        
        for (const reg of registrations) {
            try {
                await syncSingleRegistration(reg, pendingStore, imageStore);
                syncedCount++;
                console.log(`[Service Worker] Registration ID ${reg.id} synced successfully! (${syncedCount}/${registrations.length})`);
            } catch (error) {
                if (error.message.includes('Duplicate') || error.message.includes('duplicate')) {
                    duplicateCount++;
                    console.log(`[Service Worker] Registration ID ${reg.id} removed as duplicate (${duplicateCount} duplicates found)`);
                } else {
                    failedCount++;
                    console.error(`[Service Worker] Failed to sync registration ID ${reg.id}:`, error);
                }
            }
        }
        
        // Show comprehensive notification
        let notificationTitle = 'Sync Complete!';
        let notificationBody = '';
        
        if (syncedCount > 0) {
            notificationBody += `${syncedCount} registration(s) submitted successfully.`;
        }
        
        if (duplicateCount > 0) {
            if (notificationBody) notificationBody += ' ';
            notificationBody += `${duplicateCount} duplicate(s) removed.`;
        }
        
        if (failedCount > 0) {
            if (notificationBody) notificationBody += ' ';
            notificationBody += `${failedCount} failed to sync.`;
            notificationTitle = 'Sync Partially Complete';
        }
        
        if (syncedCount > 0 || duplicateCount > 0) {
            self.registration.showNotification(notificationTitle, {
                body: notificationBody,
                icon: '/static/images/android-chrome-192x192.png',
                badge: '/static/images/android-chrome-192x192.png',
                tag: 'sync-complete',
                requireInteraction: true
            });
        }
        
        console.log(`[Service Worker] Sync complete. Success: ${syncedCount}, Duplicates Removed: ${duplicateCount}, Failed: ${failedCount}`);
        
    } catch (error) {
        console.error('[Service Worker] Sync failed:', error);
        throw error; // Re-throw to trigger retry
    }
}

// // registration/static/registration/js/serviceworker.js

// const CACHE_NAME = 'labor-registration-cache-v1';
// const DB_NAME = 'LaborRegistrationDB';
// const DB_VERSION = 2;
// const STORE_PENDING_REGISTRATIONS = 'pending_registrations';
// const STORE_OFFLINE_IMAGES = 'offline_images';

// const urlsToCache = [
//     '/register/',
//     '/register/registration/',
//     '/register/registration/?step=1',
//     '/register/registration/?step=2',
//     '/register/registration/?step=3',
//     '/register/success/',
//     '/offline.html',
//     'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
//     'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
//     'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
//     'https://cdn.jsdelivr.net/npm/idb@7/+esm', // Cache the idb library
//     '/static/registration/js/multi_step_form_client.js',
//     '/static/registration/images/my_app_icon_192.png',
//     '/static/registration/images/my_app_icon_512.png',
//     '/static/registration/images/splash_screen_480x320.png',
//     '/static/images/android-chrome-192x192.png',
//     '/static/images/android-chrome-512x512.png',
// ];

// // Import idb at the top level (cached version)
// let idbModule = null;

// /**
//  * Converts a Blob to a Base64 string.
//  * @param {Blob} blob The blob to convert.
//  * @returns {Promise<string>} A promise that resolves with the Base64 string.
//  */
// function blobToBase64(blob) {
//     return new Promise((resolve, reject) => {
//         const reader = new FileReader();
//         reader.onloadend = () => resolve(reader.result);
//         reader.onerror = reject;
//         reader.readAsDataURL(blob);
//     });
// }
// // importScripts('https://unpkg.com/idb@7.1.1/build/index.js'); // Use a CDN or your local path
// // importScripts('/static/registration/js/idb.js'); 
// async function getIDB() {
//     if (!idbModule) {
//         try {
//             idbModule = await import('https://cdn.jsdelivr.net/npm/idb@7/+esm');
//         } catch (error) {
//             console.error('[Service Worker] Failed to import idb:', error);
//             throw error;
//         }
//     }
//     return idbModule;
// }

// // Installation: Cache all essential assets
// self.addEventListener('install', (event) => {
//     console.log('[Service Worker] Installing...');
//     event.waitUntil(
//         caches.open(CACHE_NAME)
//             .then((cache) => {
//                 console.log('[Service Worker] Caching all assets:', urlsToCache);
//                 return Promise.allSettled(urlsToCache.map(url => cache.add(url)))
//                     .then((results) => {
//                         results.forEach((result, index) => {
//                             if (result.status === 'rejected') {
//                                 console.warn(`[Service Worker] Failed to cache ${urlsToCache[index]}: ${result.reason.message}`);
//                             }
//                         });
//                         console.log('[Service Worker] Initial caching complete.');
//                     });
//             })
//             .then(() => self.skipWaiting())
//             .catch(error => {
//                 console.error('[Service Worker] Install failed:', error);
//             })
//     );
// });

// // Activation: Clean up old caches
// self.addEventListener('activate', (event) => {
//     console.log('[Service Worker] Activating...');
//     const cacheWhitelist = [CACHE_NAME];
//     event.waitUntil(
//         caches.keys().then((cacheNames) => {
//             return Promise.all(
//                 cacheNames.map((cacheName) => {
//                     if (cacheWhitelist.indexOf(cacheName) === -1) {
//                         console.log('[Service Worker] Deleting old cache:', cacheName);
//                         return caches.delete(cacheName);
//                     }
//                 })
//             );
//         }).then(() => {
//             console.log('[Service Worker] Activated and claiming clients');
//             return self.clients.claim();
//         })
//     );
// });

// // Fetch: Serve from cache or network
// self.addEventListener('fetch', (event) => {
//     if (event.request.method === 'GET') {
//         event.respondWith(
//             caches.match(event.request)
//                 .then((response) => {
//                     if (response) {
//                         return response;
//                     }
//                     return fetch(event.request)
//                         .then((networkResponse) => {
//                             if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
//                                 return networkResponse;
//                             }
//                             const responseToCache = networkResponse.clone();
//                             caches.open(CACHE_NAME)
//                                 .then((cache) => {
//                                     cache.put(event.request, responseToCache);
//                                 });
//                             return networkResponse;
//                         })
//                         .catch(() => {
//                             if (event.request.mode === 'navigate') {
//                                 return caches.match('/offline.html');
//                             }
//                             return new Response('<p>You are offline and this content is not available.</p>', {
//                                 headers: { 'Content-Type': 'text/html' }
//                             });
//                         });
//                 })
//         );
//     }
// });

// // Background Sync: Handle offline form submissions
// self.addEventListener('sync', (event) => {
//     console.log('[Service Worker] Sync event received with tag:', event.tag);
    
//     if (event.tag === 'sync-labor-registration') {
//         console.log('[Service Worker] Background sync triggered for labor registration!');
//         event.waitUntil(syncLaborRegistrations());
//     }
// });

// async function syncLaborRegistrations() {
//     console.log('[Service Worker] Attempting to sync offline registrations...');
    
//     try {
//         // Check if we're online
//         if (!navigator.onLine) {
//             console.log('[Service Worker] Still offline, sync will retry later');
//             throw new Error('Still offline');
//         }

//         const { openDB } = await getIDB();
        
//         const db = await openDB(DB_NAME, DB_VERSION, {
//             upgrade(db) {
//                 // Create stores if they don't exist
//                 if (!db.objectStoreNames.contains(STORE_PENDING_REGISTRATIONS)) {
//                     db.createObjectStore(STORE_PENDING_REGISTRATIONS, { keyPath: 'id' });
//                 }
//                 if (!db.objectStoreNames.contains(STORE_OFFLINE_IMAGES)) {
//                     db.createObjectStore(STORE_OFFLINE_IMAGES, { keyPath: 'id' });
//                 }
//             }
//         });
        
//         const tx = db.transaction([STORE_PENDING_REGISTRATIONS, STORE_OFFLINE_IMAGES], 'readwrite');
//         const pendingStore = tx.objectStore(STORE_PENDING_REGISTRATIONS);
//         const imageStore = tx.objectStore(STORE_OFFLINE_IMAGES);
        
//         const registrations = await pendingStore.getAll();
        
//         if (registrations.length === 0) {
//             console.log('[Service Worker] No pending registrations to sync.');
//             return;
//         }
        
//         console.log(`[Service Worker] Found ${registrations.length} pending registrations to sync.`);
        
//         let syncedCount = 0;
//         let failedCount = 0;
        
//         for (const reg of registrations) {
//             try {
//                 await syncSingleRegistration(reg, pendingStore, imageStore);
//                 syncedCount++;
//                 console.log(`[Service Worker] Registration ID ${reg.id} synced successfully! (${syncedCount}/${registrations.length})`);
//             } catch (error) {
//                 failedCount++;
//                 console.error(`[Service Worker] Failed to sync registration ID ${reg.id}:`, error);
//                 // Continue with other registrations instead of stopping
//             }
//         }
        
//         // Show notification based on results
//         if (syncedCount > 0) {
//             self.registration.showNotification('Registrations Synced!', {
//                 body: `${syncedCount} registration(s) successfully submitted.${failedCount > 0 ? ` ${failedCount} failed.` : ''}`,
//                 icon: '/static/images/android-chrome-192x192.png',
//                 badge: '/static/images/android-chrome-192x192.png',
//                 tag: 'sync-complete',
//                 requireInteraction: true
//             });
//         }
        
//         console.log(`[Service Worker] Sync complete. Success: ${syncedCount}, Failed: ${failedCount}`);
        
//     } catch (error) {
//         console.error('[Service Worker] Sync failed:', error);
//         throw error; // Re-throw to trigger retry
//     }
// }

// // async function syncSingleRegistration(reg, pendingStore, imageStore) {
// //     const formData = new FormData();
// //     const { step1, step2, step3 } = reg.data;

// //     // Append all text data from all steps
// //     const allSteps = { ...step1, ...step2, ...step3 };
// //     for (const key in allSteps) {
// //         if (Object.prototype.hasOwnProperty.call(allSteps, key) && key !== 'photoId' && key !== 'photoBase64') {
// //             const value = allSteps[key];
// //             if (typeof value === 'object' && value !== null) {
// //                 formData.append(key, JSON.stringify(value));
// //             } else {
// //                 formData.append(key, value);
// //             }
// //         }
// //     }

// //     // --- CORRECTED IMAGE HANDLING ---
// //     // This now exclusively uses the reliable Base64 method for offline syncs.
// //     if (step1.photoId) {
// //         try {
// //             const imageData = await imageStore.get(step1.photoId);
// //             if (imageData && imageData.image) {
// //                 const base64String = await blobToBase64(imageData.image);
// //                 formData.append('photo_base64', base64String);
// //                 console.log(`[Service Worker] Image (ID: ${step1.photoId}) successfully converted to Base64 and appended.`);
// //             }
// //         } catch (error) {
// //             console.error(`[Service Worker] Error processing image for sync:`, error);
// //         }
// //     }

// //     // Submit to server
// //     const response = await fetch('/register/api/submit-registration/', {
// //         method: 'POST',
// //         body: formData,
// //     });

// //     if (!response.ok) {
// //         const errorText = await response.text();
// //         throw new Error(`Server responded with status ${response.status}: ${errorText}`);
// //     }

// //     // If successful, remove from pending store and clean up images
// //     await pendingStore.delete(reg.id);
// //     if (step1.photoId) {
// //         await imageStore.delete(step1.photoId);
// //     }
// //     console.log(`[Service Worker] Registration ID ${reg.id} synced and cleaned up successfully.`);
// // }
// // Handle messages from client


// self.addEventListener('message', (event) => {
//     if (event.data && event.data.type === 'SYNC_NOW') {
//         console.log('[Service Worker] Manual sync requested from client');
//         // Manually trigger sync
//         syncLaborRegistrations().catch(error => {
//             console.error('[Service Worker] Manual sync failed:', error);
//         });
//     }
// });

// // Handle notification clicks
// self.addEventListener('notificationclick', (event) => {
//     event.notification.close();
    
//     if (event.notification.tag === 'sync-complete') {
//         // Open the app when notification is clicked
//         event.waitUntil(
//             clients.openWindow('/register/success/')
//         );
//     }
// });

// // Add this function to check mobile number duplicates
// async function checkMobileNumberDuplicate(mobileNumber) {
//     try {
//         const response = await fetch('/register/api/check-mobile-number/', {
//             method: 'POST',
//             headers: {
//                 'Content-Type': 'application/json',
//             },
//             body: JSON.stringify({
//                 mobile_number: mobileNumber
//             })
//         });
        
//         const data = await response.json();
//         return data;
//     } catch (error) {
//         console.error('[Service Worker] Error checking mobile number:', error);
//         return { exists: false, message: 'Unable to check mobile number' };
//     }
// }

// // Updated syncSingleRegistration function
// async function syncSingleRegistration(reg, pendingStore, imageStore) {
//     const mobileNumber = reg.data.step1?.mobile_number;
    
//     // Check for duplicate mobile number before syncing
//     if (mobileNumber) {
//         console.log(`[Service Worker] Checking duplicate for mobile: ${mobileNumber}`);
//         const duplicateCheck = await checkMobileNumberDuplicate(mobileNumber);
        
//         if (duplicateCheck.exists) {
//             console.warn(`[Service Worker] Duplicate mobile number found: ${mobileNumber}. Removing from offline storage.`);
            
//             // Remove from pending store and clean up images
//             await pendingStore.delete(reg.id);
//             if (reg.data.step1?.photoId) {
//                 await imageStore.delete(reg.data.step1.photoId);
//             }
            
//             // Show notification about duplicate removal
//             self.registration.showNotification('Duplicate Registration Removed', {
//                 body: `Registration with mobile number ${mobileNumber} was removed as it already exists in database.`,
//                 icon: '/static/images/android-chrome-192x192.png',
//                 badge: '/static/images/android-chrome-192x192.png',
//                 tag: 'duplicate-removed',
//                 requireInteraction: true
//             });
            
//             throw new Error(`Duplicate mobile number: ${mobileNumber}. Registration removed from offline storage.`);
//         }
//     }
    
//     const formData = new FormData();
//     const step1Data = reg.data.step1 || {};
//     const step2Data = reg.data.step2 || {};
//     const step3Data = reg.data.step3 || {};
    
//     // Append step 1 data
//     for (const key in step1Data) {
//         if (step1Data.hasOwnProperty(key) && key !== 'photoId' && key !== 'photoBase64' && key !== 'location') {
//             formData.append(key, step1Data[key]);
//         }
//     }
    
//     if (step1Data.location) {
//         formData.append('location', JSON.stringify(step1Data.location));
//     }
    
//     // Handle image with improved logic
//     let imageAppended = false;
    
//     // Priority 1: Try to get image from IndexedDB using photoId
//     if (step1Data.photoId) {
//         try {
//             const imageData = await imageStore.get(step1Data.photoId);
//             if (imageData && imageData.image) {
//                 let imageBlob = imageData.image;
                
//                 // Ensure we have a valid Blob
//                 if (!(imageBlob instanceof Blob)) {
//                     if (typeof imageBlob === 'string' && imageBlob.startsWith('data:')) {
//                         // Convert base64 string to Blob
//                         const response = await fetch(imageBlob);
//                         imageBlob = await response.blob();
//                     }
//                 }
                
//                 if (imageBlob instanceof Blob && imageBlob.size > 0) {
//                     formData.append('photo', imageBlob, imageData.name || 'captured_image.jpeg');
//                     imageAppended = true;
//                     console.log(`[Service Worker] Image from IndexedDB (ID: ${step1Data.photoId}) appended successfully. Size: ${imageBlob.size} bytes`);
//                 }
//             }
//         } catch (error) {
//             console.error(`[Service Worker] Error retrieving image ID ${step1Data.photoId} from IndexedDB:`, error);
//         }
//     }
    
//     // Priority 2: Fallback to base64 if no image was appended from IndexedDB
//     if (!imageAppended && step1Data.photoBase64) {
//         try {
//             const response = await fetch(step1Data.photoBase64);
//             const blob = await response.blob();
            
//             if (blob.size > 0) {
//                 formData.append('photo', blob, 'captured_image.jpeg');
//                 imageAppended = true;
//                 console.log(`[Service Worker] Image from base64 fallback appended successfully. Size: ${blob.size} bytes`);
//             }
//         } catch (error) {
//             console.warn('[Service Worker] Failed to convert base64 to Blob for sync:', error);
//         }
//     }
    
//     if (!imageAppended) {
//         console.warn('[Service Worker] No image was found or appended for this registration');
//     }
    
//     // Append step 2 data
//     for (const key in step2Data) {
//         if (step2Data.hasOwnProperty(key)) {
//             if (Array.isArray(step2Data[key]) || (typeof step2Data[key] === 'object' && step2Data[key] !== null)) {
//                 formData.append(key, JSON.stringify(step2Data[key]));
//             } else {
//                 formData.append(key, step2Data[key]);
//             }
//         }
//     }
    
//     // Append step 3 data
//     if (step3Data.data_sharing_agreement !== undefined) {
//         formData.append('data_sharing_agreement', step3Data.data_sharing_agreement);
//     }
    
//     // Debug FormData contents
//     console.log('[Service Worker] --- FormData Contents ---');
//     for (const pair of formData.entries()) {
//         if (pair[0] === 'photo') {
//             console.log(`[Service Worker] ${pair[0]}: [File Blob - ${pair[1].size} bytes, type: ${pair[1].type}]`);
//         } else {
//             console.log(`[Service Worker] ${pair[0]}: ${pair[1]}`);
//         }
//     }
//     console.log('[Service Worker] --- End FormData Contents ---');
    
//     // Submit to server
//     const response = await fetch('/register/api/submit-registration/', {
//         method: 'POST',
//         body: formData,
//     });
    
//     if (!response.ok) {
//         const errorText = await response.text();
//         let errorData;
        
//         try {
//             errorData = JSON.parse(errorText);
//         } catch (e) {
//             errorData = { message: errorText };
//         }
        
//         // Handle duplicate mobile number error from server
//         if (errorData.error_type === 'duplicate_mobile') {
//             console.warn(`[Service Worker] Server confirmed duplicate mobile number: ${mobileNumber}`);
            
//             // Remove from pending store and clean up images
//             await pendingStore.delete(reg.id);
//             if (step1Data.photoId) {
//                 await imageStore.delete(step1Data.photoId);
//             }
            
//             // Show notification about duplicate
//             self.registration.showNotification('Duplicate Registration Removed', {
//                 body: `Registration with mobile number ${mobileNumber} was removed as it already exists in database.`,
//                 icon: '/static/images/android-chrome-192x192.png',
//                 badge: '/static/images/android-chrome-192x192.png',
//                 tag: 'duplicate-removed',
//                 requireInteraction: true
//             });
            
//             throw new Error(`Server confirmed duplicate: ${errorData.message}`);
//         }
        
//         throw new Error(`Server responded with status ${response.status}: ${errorData.message || errorText}`);
//     }
    
//     // If successful, remove from pending store and clean up images
//     await pendingStore.delete(reg.id);
//     if (step1Data.photoId) {
//         await imageStore.delete(step1Data.photoId);
//         console.log(`[Service Worker] Image ID ${step1Data.photoId} cleaned up from IndexedDB`);
//     }
    
//     console.log(`[Service Worker] Registration for ${step1Data.full_name} synced successfully`);
// }

// // Updated syncLaborRegistrations function with better error handling
// async function syncLaborRegistrations() {
//     console.log('[Service Worker] Attempting to sync offline registrations...');
    
//     try {
//         // Check if we're online
//         if (!navigator.onLine) {
//             console.log('[Service Worker] Still offline, sync will retry later');
//             throw new Error('Still offline');
//         }

//         const { openDB } = await getIDB();
        
//         const db = await openDB(DB_NAME, DB_VERSION, {
//             upgrade(db) {
//                 // Create stores if they don't exist
//                 if (!db.objectStoreNames.contains(STORE_PENDING_REGISTRATIONS)) {
//                     db.createObjectStore(STORE_PENDING_REGISTRATIONS, { keyPath: 'id' });
//                 }
//                 if (!db.objectStoreNames.contains(STORE_OFFLINE_IMAGES)) {
//                     db.createObjectStore(STORE_OFFLINE_IMAGES, { keyPath: 'id' });
//                 }
//             }
//         });
        
//         const tx = db.transaction([STORE_PENDING_REGISTRATIONS, STORE_OFFLINE_IMAGES], 'readwrite');
//         const pendingStore = tx.objectStore(STORE_PENDING_REGISTRATIONS);
//         const imageStore = tx.objectStore(STORE_OFFLINE_IMAGES);
        
//         const registrations = await pendingStore.getAll();
        
//         if (registrations.length === 0) {
//             console.log('[Service Worker] No pending registrations to sync.');
//             return;
//         }
        
//         console.log(`[Service Worker] Found ${registrations.length} pending registrations to sync.`);
        
//         let syncedCount = 0;
//         let failedCount = 0;
//         let duplicateCount = 0;
        
//         for (const reg of registrations) {
//             try {
//                 await syncSingleRegistration(reg, pendingStore, imageStore);
//                 syncedCount++;
//                 console.log(`[Service Worker] Registration ID ${reg.id} synced successfully! (${syncedCount}/${registrations.length})`);
//             } catch (error) {
//                 if (error.message.includes('Duplicate') || error.message.includes('duplicate')) {
//                     duplicateCount++;
//                     console.log(`[Service Worker] Registration ID ${reg.id} removed as duplicate (${duplicateCount} duplicates found)`);
//                 } else {
//                     failedCount++;
//                     console.error(`[Service Worker] Failed to sync registration ID ${reg.id}:`, error);
//                 }
//             }
//         }
        
//         // Show comprehensive notification
//         let notificationTitle = 'Sync Complete!';
//         let notificationBody = '';
        
//         if (syncedCount > 0) {
//             notificationBody += `${syncedCount} registration(s) submitted successfully.`;
//         }
        
//         if (duplicateCount > 0) {
//             if (notificationBody) notificationBody += ' ';
//             notificationBody += `${duplicateCount} duplicate(s) removed.`;
//         }
        
//         if (failedCount > 0) {
//             if (notificationBody) notificationBody += ' ';
//             notificationBody += `${failedCount} failed to sync.`;
//             notificationTitle = 'Sync Partially Complete';
//         }
        
//         if (syncedCount > 0 || duplicateCount > 0) {
//             self.registration.showNotification(notificationTitle, {
//                 body: notificationBody,
//                 icon: '/static/images/android-chrome-192x192.png',
//                 badge: '/static/images/android-chrome-192x192.png',
//                 tag: 'sync-complete',
//                 requireInteraction: true
//             });
//         }
        
//         console.log(`[Service Worker] Sync complete. Success: ${syncedCount}, Duplicates Removed: ${duplicateCount}, Failed: ${failedCount}`);
        
//     } catch (error) {
//         console.error('[Service Worker] Sync failed:', error);
//         throw error; // Re-throw to trigger retry
//     }
// }