// registration/static/registration/js/multi_step_form_client.js

// Import idb library for easier IndexedDB access
import { openDB } from 'https://cdn.jsdelivr.net/npm/idb@7/+esm';

// Global variables for camera, photo, and IndexedDB instance
let cameraStream = null;
let photoBlob = null; // Store the captured photo as a Blob directly
let currentFacingMode = 'environment'; // Start with back camera (better for general photos)
let availableCameras = [];

// IndexedDB related constants and instance
let db;
const DB_NAME = 'LaborRegistrationDB'; // Name of your IndexedDB database
const DB_VERSION = 2; // IMPORTANT: Increment this version number whenever you change the database schema
const STORE_CURRENT_REGISTRATION = 'current_registration_form'; // Store for the single ongoing, multi-step form data (draft)
const STORE_PENDING_REGISTRATIONS = 'pending_registrations'; // Store for completed forms awaiting synchronization
const STORE_OFFLINE_IMAGES = 'offline_images'; // Store for captured image Blobs

// --- PWA Service Worker Registration ---
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Register the service worker as a module to allow for import statements
        navigator.serviceWorker.register('/static/registration/js/serviceworker.js', { type: 'module' })
            .then(registration => {
                console.log('Service Worker registered successfully:', registration.scope);
            })
            .catch(error => {
                console.error('Service Worker registration failed:', error);
            });
    });
}

// --- IndexedDB Initialization ---
async function initDB() {
    db = await openDB(DB_NAME, DB_VERSION, {
        upgrade(db, oldVersion, newVersion, transaction) {
            console.log(`IndexedDB upgrade: oldVersion=${oldVersion}, newVersion=${newVersion}`);
            if (oldVersion < 1) {
                db.createObjectStore(STORE_CURRENT_REGISTRATION, { keyPath: 'id' });
                db.createObjectStore(STORE_PENDING_REGISTRATIONS, { keyPath: 'id', autoIncrement: true });
                db.createObjectStore(STORE_OFFLINE_IMAGES, { keyPath: 'id', autoIncrement: true });
            }
            if (oldVersion < 2) {
                // Example of schema upgrade: add an index if needed in the future
                // const pendingStore = transaction.objectStore(STORE_PENDING_REGISTRATIONS);
                // pendingStore.createIndex('timestamp', 'timestamp');
            }
        },
    });
    console.log('IndexedDB initialized.');
}

// --- Data Storage/Retrieval Functions (IndexedDB) ---
async function saveCurrentRegistrationData(data) {
    if (!db) await initDB();
    const tx = db.transaction(STORE_CURRENT_REGISTRATION, 'readwrite');
    const store = tx.objectStore(STORE_CURRENT_REGISTRATION);
    await store.put({ id: 'current_draft', data: data });
    await tx.done;
    console.log('Current registration data saved to IndexedDB.');
}

async function getCurrentRegistrationData() {
    if (!db) await initDB();
    const tx = db.transaction(STORE_CURRENT_REGISTRATION, 'readonly');
    const store = tx.objectStore(STORE_CURRENT_REGISTRATION);
    const record = await store.get('current_draft');
    return record ? record.data : {};
}

async function getPendingRegistrationsCount() {
    if (!db) await initDB();
    const tx = db.transaction(STORE_PENDING_REGISTRATIONS, 'readonly');
    const store = tx.objectStore(STORE_PENDING_REGISTRATIONS);
    return await store.count();
}

async function saveImageBlob(blob, fileName, mimeType) {
    if (!db) await initDB();
    const tx = db.transaction(STORE_OFFLINE_IMAGES, 'readwrite');
    const store = tx.objectStore(STORE_OFFLINE_IMAGES);
    const imageId = await store.add({ image: blob, name: fileName, type: mimeType });
    await tx.done;
    console.log('Image Blob saved to IndexedDB with ID:', imageId);
    return imageId;
}

async function saveForBackgroundSync(fullRegistrationData) {
    if (!db) await initDB();
    const tx = db.transaction(STORE_PENDING_REGISTRATIONS, 'readwrite');
    const store = tx.objectStore(STORE_PENDING_REGISTRATIONS);
    await store.add({
        data: fullRegistrationData,
        timestamp: Date.now(),
        attemptedSync: 0
    });
    await tx.done;
    console.log('Full registration saved for background sync.');
    await updateSyncStatusUI(); // Update UI after saving
}

// --- UI Initialization and Event Listeners ---
document.addEventListener('DOMContentLoaded', async function() {
    await initDB();
    await updateSyncStatusUI(); // Initial check for pending forms

    const currentStep = parseInt(document.querySelector('input[name="step"]').value);

    if (currentStep === 1) {
        initializeCameraAndLocation();
        await loadStep1Data();
    } else if (currentStep === 2) {
        await loadStep2Data();
        initializeFormElements();
    } else if (currentStep === 3) {
        await loadStep3Data();
    }

    const prevBtn = document.getElementById('prevStepBtn');
    const nextBtn = document.getElementById('nextStepBtn');

    if (prevBtn) {
        prevBtn.addEventListener('click', goBack);
    }
    if (nextBtn) {
        // IMPORTANT: Attach event listener to the button, not the form submit event directly
        // The handleNextSubmit will prevent default and control navigation
        nextBtn.addEventListener('click', handleNextSubmit);
    }
});

// --- Sync Status UI Management ---
async function updateSyncStatusUI() {
    const pendingCount = await getPendingRegistrationsCount();
    const container = document.getElementById('sync-status-container');
    if (!container) return;

    if (pendingCount > 0) {
        container.innerHTML = `
            <div id="sync-banner" class="alert alert-warning d-flex align-items-center justify-content-between p-3 mt-3 shadow">
                <span>
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>Pending Submissions:</strong> You have ${pendingCount} registration(s) waiting to be submitted.
                </span>
                <button id="sync-now-btn" class="btn btn-primary btn-sm">Sync Now</button>
            </div>
        `;
        document.getElementById('sync-now-btn').addEventListener('click', syncNowHandler);
    } else {
        container.innerHTML = ''; // Clear the banner if no pending submissions
    }
}

async function syncNowHandler() {
    const syncButton = document.getElementById('sync-now-btn');
    if (!syncButton) return;

    const originalText = syncButton.innerHTML;
    syncButton.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div> Syncing...';
    syncButton.disabled = true;

    const db = await openDB(DB_NAME, DB_VERSION);
    const pendingRegistrations = await db.getAll(STORE_PENDING_REGISTRATIONS);

    if (pendingRegistrations.length === 0) {
        alert('No pending registrations to sync!');
        updateSyncStatusUI();
        syncButton.innerHTML = originalText;
        syncButton.disabled = false;
        return;
    }

    const isOnline = navigator.onLine;

    if (isOnline) {
        console.log('Online, attempting immediate sync of all pending registrations.');
        let syncedCount = 0;
        let failedCount = 0;

        for (const reg of pendingRegistrations) {
            try {
                // This is the critical line that needs to be updated.
                const success = await processAndSendRegistration(reg.data, reg.id);
                if (success) {
                    syncedCount++;
                } else {
                    failedCount++;
                }
            } catch (error) {
                console.error(`Error submitting pending registration ID ${reg.id}:`, error);
                failedCount++;
            }
        }

        if (syncedCount > 0) {
            alert(`Sync complete! Successfully submitted ${syncedCount} registration(s).`);
        }
        if (failedCount > 0) {
            alert(`Warning: Failed to submit ${failedCount} registration(s). They will remain in offline storage.`);
        }
        updateSyncStatusUI();

    } else {
        // ... (rest of the offline logic remains the same) ...
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
            try {
                const registration = await navigator.serviceWorker.ready;
                await registration.sync.register('sync-labor-registration');
                alert('You are offline. Sync request sent and will be processed when a network connection is available.');
            } catch (error) {
                console.error('Failed to register background sync:', error);
                alert('Failed to start sync. Please check your network connection and try again.');
            }
        } else {
            alert('Your browser does not support background sync. Data is saved locally, but will not auto-sync.');
        }
    }

    syncButton.innerHTML = originalText;
    syncButton.disabled = false;
    updateSyncStatusUI();
}

// --- Load Data from IndexedDB (Pre-fill Forms) ---
async function loadStep1Data() {
    const currentRegistration = await getCurrentRegistrationData();
    const step1Data = currentRegistration.step1 || {};

    document.querySelector('[name="full_name"]').value = step1Data.full_name || '';
    document.querySelector('[name="mobile_number"]').value = step1Data.mobile_number || '';
    document.querySelector('[name="category"]').value = step1Data.category || '';
    document.querySelector('[name="taluka"]').value = step1Data.taluka || '';
    document.querySelector('[name="village"]').value = step1Data.village || '';

    if (step1Data.category) {
        document.getElementById('currentCategoryHidden').value = step1Data.category;
    }

    // Load photo from IndexedDB if photoId exists, otherwise from base64 (older format)
    if (step1Data.photoId) {
        const tx = db.transaction(STORE_OFFLINE_IMAGES, 'readonly');
        const imageStore = tx.objectStore(STORE_OFFLINE_IMAGES);
        const imageData = await imageStore.get(step1Data.photoId);
        if (imageData && imageData.image) {
            photoBlob = imageData.image;
            const reader = new FileReader();
            reader.onloadend = () => {
                document.getElementById('captured-image').src = reader.result;
                document.getElementById('final-image').src = reader.result;
                document.getElementById('captured_photo_hidden').value = reader.result; // Still store base64 for submission convenience
                document.getElementById('camera-section').style.display = 'none';
                document.getElementById('photo-preview').style.display = 'none';
                document.getElementById('photo-confirmed').style.display = 'block';
                document.getElementById('camera-status').innerHTML = '<p class="text-success"><i class="fas fa-check-circle me-2"></i>Photo loaded from offline storage!</p>';
            };
            reader.readAsDataURL(photoBlob);
        }
    } else if (step1Data.photoBase64) {
        // Fallback for older data or if photoBlob was not saved correctly
        document.getElementById('captured-image').src = step1Data.photoBase64;
        document.getElementById('final-image').src = step1Data.photoBase64;
        document.getElementById('captured_photo_hidden').value = step1Data.photoBase64;
        document.getElementById('camera-section').style.display = 'none';
        document.getElementById('photo-preview').style.display = 'none';
        document.getElementById('photo-confirmed').style.display = 'block';
        document.getElementById('camera-status').innerHTML = '<p class="text-success"><i class="fas fa-check-circle me-2"></i>Photo loaded from offline storage!</p>';
    }


    if (step1Data.location) {
        const loc = step1Data.location;
        document.getElementById('latitude_hidden').value = loc.latitude || '';
        document.getElementById('longitude_hidden').value = loc.longitude || '';
        document.getElementById('location_accuracy_hidden').value = loc.accuracy || '';

        document.getElementById('location-coordinates').textContent = `${loc.latitude.toFixed(6)}, ${loc.longitude.toFixed(6)}`;
        document.getElementById('location-accuracy').textContent = `${loc.accuracy.toFixed(0)}m`;

        const locationInfoElement = document.getElementById('location-info');
        if (locationInfoElement) {
            locationInfoElement.style.display = 'block';
        }
        const locationErrorElement = document.getElementById('location-error');
        if (locationErrorElement) {
            locationErrorElement.style.display = 'none';
        }

        const getLocationBtn = document.getElementById('get-location');
        if (getLocationBtn) {
            getLocationBtn.innerHTML = '<i class="fas fa-check me-2"></i>Location Captured';
            getLocationBtn.disabled = false;
            getLocationBtn.className = 'btn btn-success';
        }
    }
}

async function loadStep2Data() {
    const currentRegistration = await getCurrentRegistrationData();
    const step2Data = currentRegistration.step2 || {};
    const categoryFromStep1 = currentRegistration.step1 ? currentRegistration.step1.category : '';

    if (categoryFromStep1) {
        document.getElementById('currentCategoryHidden').value = categoryFromStep1;
        document.getElementById('currentCategorySession').value = categoryFromStep1;
    }

    if (step2Data.gender) document.querySelector('[name="gender"]').value = step2Data.gender;
    if (step2Data.age) document.querySelector('[name="age"]').value = step2Data.age;
    if (step2Data.expected_wage) document.querySelector('[name="expected_wage"]').value = step2Data.expected_wage;

    // Load skills and communication preferences (checkboxes)
    if (step2Data.skills && Array.isArray(step2Data.skills)) {
        step2Data.skills.forEach(skill => {
            const checkbox = document.querySelector(`input[name="skills"][value="${skill}"]`);
            if (checkbox) checkbox.checked = true;
        });
    }
    if (step2Data.communication_preferences && Array.isArray(step2Data.communication_preferences)) {
        step2Data.communication_preferences.forEach(pref => {
            const checkbox = document.querySelector(`input[name="communication_preferences"][value="${pref}"]`);
            if (checkbox) checkbox.checked = true;
        });
    }

    const transportSelect = document.querySelector('select[name="arrange_transport"]');
    if (transportSelect && step2Data.arrange_transport) {
        transportSelect.value = step2Data.arrange_transport;
        transportSelect.dispatchEvent(new Event('change')); // Trigger change to show/hide 'other' field
    }
    if (step2Data.arrange_transport_other) {
        document.querySelector('[name="arrange_transport_other"]').value = step2Data.arrange_transport_other;
    }

    if (step2Data.providing_labour_count) document.querySelector('[name="providing_labour_count"]').value = step2Data.providing_labour_count;
    if (step2Data.total_workers_peak) document.querySelector('[name="total_workers_peak"]').value = step2Data.total_workers_peak;
    if (step2Data.expected_charges) document.querySelector('[name="expected_charges"]').value = step2Data.expected_charges;
    if (step2Data.labour_supply_availability) document.querySelector('[name="labour_supply_availability"]').value = step2Data.labour_supply_availability;
    if (step2Data.supply_areas) document.querySelector('[name="supply_areas"]').value = step2Data.supply_areas;

    if (step2Data.vehicle_type) document.querySelector('[name="vehicle_type"]').value = step2Data.vehicle_type;
    if (step2Data.people_capacity) document.querySelector('[name="people_capacity"]').value = step2Data.people_capacity;
    if (step2Data.expected_fair) document.querySelector('[name="expected_fair"]').value = step2Data.expected_fair;
    if (step2Data.service_areas) document.querySelector('[name="service_areas"]').value = step2Data.service_areas;

    if (step2Data.business_name) document.querySelector('[name="business_name"]').value = step2Data.business_name;
    if (step2Data.help_description) document.querySelector('[name="help_description"]').value = step2Data.help_description;
}

async function loadStep3Data() {
    const currentRegistration = await getCurrentRegistrationData();
    const step3Data = currentRegistration.step3 || {};
    if (step3Data.data_sharing_agreement) {
        document.querySelector('input[name="data_sharing_agreement"]').checked = step3Data.data_sharing_agreement;
    }
    const categoryFromStep1 = currentRegistration.step1 ? currentRegistration.step1.category : '';
    if (categoryFromStep1) {
        document.getElementById('currentCategoryHidden').value = categoryFromStep1;
    }
}


async function clearCurrentRegistrationAndImage() {
    if (!db) await initDB();
    const currentRegistration = await getCurrentRegistrationData();
    const tx = db.transaction([STORE_CURRENT_REGISTRATION, STORE_OFFLINE_IMAGES], 'readwrite');
    await tx.objectStore(STORE_CURRENT_REGISTRATION).delete('current_draft');
    if (currentRegistration && currentRegistration.step1 && currentRegistration.step1.photoId) {
        await tx.objectStore(STORE_OFFLINE_IMAGES).delete(currentRegistration.step1.photoId);
    }
    await tx.done;
    console.log('Current registration and associated image cleared from IndexedDB.');
}




function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function initializeCameraAndLocation() {
    setTimeout(() => {
        getCurrentLocation();
    }, 1000);

    const startCameraBtn = document.getElementById('start-camera');
    const capturePhotoBtn = document.getElementById('capture-photo');
    const switchCameraBtn = document.getElementById('switch-camera');
    const retakePhotoBtn = document.getElementById('retake-photo');
    const confirmPhotoBtn = document.getElementById('confirm-photo');
    const changePhotoBtn = document.getElementById('change-photo');
    const getLocationBtn = document.getElementById('get-location');

    if (startCameraBtn) {
        startCameraBtn.addEventListener('click', startCamera);
    }
    if (capturePhotoBtn) {
        capturePhotoBtn.addEventListener('click', capturePhoto);
    }
    if (switchCameraBtn) {
        switchCameraBtn.addEventListener('click', switchCamera);
    }
    if (retakePhotoBtn) {
        retakePhotoBtn.addEventListener('click', retakePhoto);
    }
    if (confirmPhotoBtn) {
        confirmPhotoBtn.addEventListener('click', confirmPhoto);
    }
    if (changePhotoBtn) {
        changePhotoBtn.addEventListener('click', changePhoto);
    }
    if (getLocationBtn) {
        getLocationBtn.addEventListener('click', getCurrentLocation);
    }

    checkAvailableCameras();

    const fileInput = document.querySelector('input[name="photo"]');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                photoBlob = file; // Store as blob for submission/indexedDB
                const reader = new FileReader();
                reader.onload = function(event) {
                    document.getElementById('captured-image').src = event.target.result;
                    document.getElementById('final-image').src = event.target.result;
                    document.getElementById('captured_photo_hidden').value = event.target.result; // For form hidden field
                    document.getElementById('upload-fallback').style.display = 'none';
                    document.getElementById('camera-section').style.display = 'none';
                    document.getElementById('photo-preview').style.display = 'none';
                    document.getElementById('photo-confirmed').style.display = 'block';
                    document.getElementById('camera-status').innerHTML = '<p class="text-success"><i class="fas fa-check-circle me-2"></i>Photo uploaded successfully!</p>';
                };
                reader.readAsDataURL(file);
            }
        });
    }
}

async function checkAvailableCameras() {
    try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        availableCameras = devices.filter(device => device.kind === 'videoinput');
        const switchBtn = document.getElementById('switch-camera');
        if (availableCameras.length <= 1) {
            if (switchBtn) {
                switchBtn.style.display = 'none';
            }
        } else {
            if (switchBtn) {
                switchBtn.style.display = 'inline-block';
            }
        }
    } catch (error) {
        console.log('Could not enumerate devices:', error);
    }
}

async function startCamera() {
    const video = document.getElementById('camera-stream');
    const startBtn = document.getElementById('start-camera');
    const captureBtn = document.getElementById('capture-photo');
    const switchBtn = document.getElementById('switch-camera');
    const statusDiv = document.getElementById('camera-status');
    const cameraInfo = document.getElementById('camera-info');
    const uploadFallback = document.getElementById('upload-fallback');

    try {
        const constraints = {
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: currentFacingMode
            }
        };

        statusDiv.innerHTML = '<div class="loading-spinner"></div>Starting camera...';
        uploadFallback.style.display = 'none'; // Hide fallback if camera starts

        stopCameraStream(); // Stop any existing stream before starting a new one

        cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = cameraStream;

        startBtn.style.display = 'none';
        captureBtn.style.display = 'inline-block';

        if (availableCameras.length > 1) {
            switchBtn.style.display = 'inline-block';
        }

        cameraInfo.style.display = 'block';
        updateCameraInfo();

        statusDiv.innerHTML = '<p class="text-info"><i class="fas fa-info-circle me-2"></i>Camera ready! Position yourself properly and click capture.</p>';

    } catch (error) {
        console.error('Camera error:', error);

        let errorMessage = 'Camera access denied or not available.';
        if (error.name === 'NotAllowedError') {
            errorMessage = 'Camera permission denied. Please allow camera access and try again.';
        } else if (error.name === 'NotFoundError') {
            errorMessage = 'No camera found on this device.';
        } else if (error.name === 'NotReadableError') {
            errorMessage = 'Camera is being used by another application.';
        }

        statusDiv.innerHTML = `<p class="text-danger"><i class="fas fa-exclamation-triangle me-2"></i>${errorMessage}</p>`;

        // Show upload fallback in case of camera error
        document.getElementById('upload-fallback').style.display = 'block';
        document.querySelector('input[name="photo"]').style.display = 'block';
        document.getElementById('start-camera').style.display = 'none';
        document.getElementById('capture-photo').style.display = 'none';
        document.getElementById('switch-camera').style.display = 'none';
    }
}

function stopCameraStream() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
}


async function switchCamera() {
    currentFacingMode = currentFacingMode === 'user' ? 'environment' : 'user';
    await startCamera();
}

function updateCameraInfo() {
    const currentCameraSpan = document.getElementById('current-camera');
    const switchButton = document.getElementById('switch-camera');
    const switchText = switchButton ? switchButton.querySelector('.camera-switch-text') : null;

    if (currentCameraSpan) {
        const cameraName = currentFacingMode === 'environment' ? 'Back Camera' : 'Front Camera';
        currentCameraSpan.textContent = cameraName;

        if (switchText) {
            const switchTo = currentFacingMode === 'environment' ? 'Front' : 'Back';
            switchText.textContent = `Switch to ${switchTo}`;
        }
    }
}

function capturePhoto() {
    const video = document.getElementById('camera-stream');
    const canvas = document.getElementById('photo-canvas');
    const cameraSection = document.getElementById('camera-section');
    const previewDiv = document.getElementById('photo-preview');
    const capturedImg = document.getElementById('captured-image');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
        photoBlob = blob; // Store the captured photo as a Blob
        capturedImg.src = URL.createObjectURL(photoBlob); // Display from Blob URL

        cameraSection.style.display = 'none';
        previewDiv.style.display = 'block';

        stopCameraStream(); // Stop the stream after capturing the photo
    }, 'image/jpeg', 0.85);
}

function retakePhoto() {
    const cameraSection = document.getElementById('camera-section');
    const previewDiv = document.getElementById('photo-preview');
    const confirmedDiv = document.getElementById('photo-confirmed');

    cameraSection.style.display = 'block';
    previewDiv.style.display = 'none';
    confirmedDiv.style.display = 'none';
    document.getElementById('upload-fallback').style.display = 'none'; // Hide upload fallback when retaking

    if (document.getElementById('captured-image').src && document.getElementById('captured-image').src.startsWith('blob:')) {
        URL.revokeObjectURL(document.getElementById('captured-image').src); // Clean up Blob URL
    }
    photoBlob = null; // Clear the stored blob
    document.getElementById('captured_photo_hidden').value = ''; // Clear hidden input
    document.querySelector('input[name="photo"]').value = ''; // Clear file input

    startCamera();
}

function confirmPhoto() {
    const previewDiv = document.getElementById('photo-preview');
    const confirmedDiv = document.getElementById('photo-confirmed');
    const finalImg = document.getElementById('final-image');
    const capturedPhotoInput = document.getElementById('captured_photo_hidden');

    // Ensure photoBlob is populated (from camera or file input)
    if (photoBlob) {
        const reader = new FileReader();
        reader.onloadend = () => {
            capturedPhotoInput.value = reader.result; // Store base64 in hidden input
            finalImg.src = reader.result;
            previewDiv.style.display = 'none';
            confirmedDiv.style.display = 'block';
            document.getElementById('camera-status').innerHTML = '<p class="text-success"><i class="fas fa-check-circle me-2"></i>Photo captured and confirmed!</p>';
        };
        reader.readAsDataURL(photoBlob);
    } else {
        // Fallback in case photoBlob is somehow empty but an image is displayed
        finalImg.src = document.getElementById('captured-image').src;
        previewDiv.style.display = 'none';
        confirmedDiv.style.display = 'block';
        document.getElementById('camera-status').innerHTML = '<p class="text-success"><i class="fas fa-check-circle me-2"></i>Photo confirmed!</p>';
    }
}

function changePhoto() {
    retakePhoto();
}

function getCurrentLocation() {
    const locationBtn = document.getElementById('get-location');
    const locationInfo = document.getElementById('location-info');
    const locationError = document.getElementById('location-error');
    const coordinatesSpan = document.getElementById('location-coordinates');
    const accuracySpan = document.getElementById('location-accuracy');
    const latitudeHidden = document.getElementById('latitude_hidden');
    const longitudeHidden = document.getElementById('longitude_hidden');
    const accuracyHidden = document.getElementById('location_accuracy_hidden');

    if (!navigator.geolocation) {
        showLocationError('Geolocation is not supported by this browser.');
        return;
    }

    locationBtn.innerHTML = '<div class="loading-spinner"></div>Getting location...';
    locationBtn.disabled = true;
    locationError.style.display = 'none';

    const options = {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000
    };

    navigator.geolocation.getCurrentPosition(
        function(position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            const accuracy = position.coords.accuracy;

            latitudeHidden.value = lat;
            longitudeHidden.value = lng;
            accuracyHidden.value = accuracy;

            coordinatesSpan.textContent = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
            accuracySpan.textContent = `${accuracy.toFixed(0)}m`;

            locationInfo.style.display = 'block';
            locationError.style.display = 'none';

            locationBtn.innerHTML = '<i class="fas fa-check me-2"></i>Location Captured';
            locationBtn.disabled = false;
            locationBtn.className = 'btn btn-success';
        },
        function(error) {
            let errorMessage = 'Unable to retrieve location.';
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorMessage = 'Location access denied by user.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorMessage = 'Location information unavailable.';
                    break;
                case error.TIMEOUT:
                    errorMessage = 'Location request timed out.';
                    break;
            }
            showLocationError(errorMessage);
        },
        options
    );
}

function showLocationError(message) {
    const locationBtn = document.getElementById('get-location');
    const locationError = document.getElementById('location-error');
    const locationInfo = document.getElementById('location-info');
    const errorMessageSpan = document.getElementById('location-error-message');

    errorMessageSpan.textContent = message;
    locationError.style.display = 'block';
    locationInfo.style.display = 'none';

    locationBtn.innerHTML = '<i class="fas fa-crosshairs me-2"></i>Try Again';
    locationBtn.disabled = false;
    locationBtn.className = 'btn btn-warning';
}

function initializeFormElements() {
    const canReferCheckbox = document.querySelector('input[name="can_refer_others"]');
    const referralFields = document.getElementById('referral-fields');

    if (canReferCheckbox && referralFields) {
        canReferCheckbox.addEventListener('change', function() {
            referralFields.style.display = this.checked ? 'block' : 'none';
        });
        // Set initial state on load
        if (canReferCheckbox.checked) {
            referralFields.style.display = 'block';
        }
    }

    const transportSelect = document.querySelector('select[name="arrange_transport"]');
    const transportOtherField = document.getElementById('transport-other-field');

    if (transportSelect && transportOtherField) {
        transportSelect.addEventListener('change', function() {
            transportOtherField.style.display = this.value === 'other' ? 'block' : 'none';
        });
        // Set initial state on load
        if (transportSelect.value === 'other') {
            transportOtherField.style.display = 'block';
        }
    }

    document.querySelectorAll('input[type="text"], input[type="number"], select, textarea').forEach(input => {
        // Add event listener to clear 'is-invalid' class on input
        input.addEventListener('input', function() {
            this.classList.remove('is-invalid');
        });
        input.addEventListener('change', function() {
            this.classList.remove('is-invalid');
        });
    });

    // Specific phone number formatting
    const mobileNumberInput = document.querySelector('[name="mobile_number"]');
    if (mobileNumberInput) {
        mobileNumberInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^\d+]/g, ''); // Allow '+' and digits
            if (value && !value.startsWith('+') && !value.startsWith('91') && value.length >= 10) {
                value = '+91' + value;
            } else if (value.startsWith('91') && !value.startsWith('+91')) {
                value = '+' + value;
            }
            e.target.value = value;
        });
    }
}


async function goBack() {
    const currentStep = parseInt(document.querySelector('input[name="step"]').value);
    const form = document.getElementById('registrationForm');
    let currentRegistration = await getCurrentRegistrationData();
    let stepData = {};

    function getFieldValue(name) {
        const element = form.querySelector(`[name="${name}"]`);
        if (!element) return null;
        if (element.type === 'checkbox' || element.type === 'radio') {
            const selected = form.querySelector(`[name="${name}"]:checked`);
            return selected ? selected.value : (element.type === 'checkbox' ? element.checked : '');
        }
        if (element.tagName === 'SELECT') { return element.value; }
        return element.value.trim();
    }
    function getCheckboxValues(name) {
        const checkboxes = form.querySelectorAll(`input[name="${name}"]:checked`);
        return Array.from(checkboxes).map(cb => cb.value);
    }

    // Save current step's data before navigating back
    if (currentStep === 2) {
        const categoryFromStep1 = currentRegistration.step1 ? currentRegistration.step1.category : '';
        const currentCategory = document.getElementById('currentCategorySession').value || categoryFromStep1;

        if (currentCategory === 'individual_labor') {
            stepData = {
                gender: getFieldValue('gender'), age: parseInt(getFieldValue('age')) || null, primary_source_income: getFieldValue('primary_source_income'), employment_type: getFieldValue('employment_type'),
                skills: getCheckboxValues('skills'), willing_to_migrate: getFieldValue('willing_to_migrate') === 'yes', expected_wage: getFieldValue('expected_wage'), availability: getFieldValue('availability'),
                adult_men_seeking_employment: parseInt(getFieldValue('adult_men_seeking_employment')) || 0, adult_women_seeking_employment: parseInt(getFieldValue('adult_women_seeking_employment')) || 0,
                communication_preferences: getCheckboxValues('communication_preferences')
            };
        } else if (currentCategory === 'mukkadam') {
            stepData = {
                providing_labour_count: parseInt(getFieldValue('providing_labour_count')) || null, total_workers_peak: parseInt(getFieldValue('total_workers_peak')) || null, expected_charges: getFieldValue('expected_charges'),
                labour_supply_availability: getFieldValue('labour_supply_availability'), arrange_transport: getFieldValue('arrange_transport'), arrange_transport_other: getFieldValue('arrange_transport_other'),
                supply_areas: getCheckboxValues('supply_areas'), skills: getCheckboxValues('skills'),
            };
        } else if (currentCategory === 'transport') {
            stepData = {
                vehicle_type: getFieldValue('vehicle_type'), people_capacity: parseInt(getFieldValue('people_capacity')) || null, expected_fair: getFieldValue('expected_fair'),
                availability: getFieldValue('availability'), service_areas: getCheckboxValues('service_areas'),
            };
        } else if (currentCategory === 'others') {
            stepData = {
                business_name: getFieldValue('business_name'), help_description: getFieldValue('help_description'),
            };
        }
        currentRegistration.step2 = stepData;
    } else if (currentStep === 3) {
        stepData = {
            data_sharing_agreement: document.querySelector('input[name="data_sharing_agreement"]').checked
        };
        currentRegistration.step3 = stepData;
    }

    await saveCurrentRegistrationData(currentRegistration);

    // Navigate back
    if (currentStep > 1) {
        const categoryToPass = currentRegistration.step1 ? currentRegistration.step1.category : '';
        window.location.href = `?step=${currentStep - 1}&current_category_from_db=${encodeURIComponent(categoryToPass)}`;
    }
}

window.addEventListener('beforeunload', function() {
    stopCameraStream(); // Clean up camera on page unload
});
window.manualSync = manualSync;
window.registerBackgroundSync = registerBackgroundSync;

// Function to register background sync when storing data offline
async function registerBackgroundSync() {
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
        try {
            const registration = await navigator.serviceWorker.ready;
            await registration.sync.register('sync-labor-registration');
            console.log('[Client] Background sync registered successfully');
            return true;
        } catch (error) {
            console.error('[Client] Failed to register background sync:', error);
            return false;
        }
    } else {
        console.warn('[Client] Background sync not supported');
        return false;
    }
}

// Function to manually trigger sync (useful for testing)
async function manualSync() {
    console.log('[Client] Manual sync requested');
    
    // Show loading state
    const button = event?.target;
    if (button) {
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Syncing...';
    }
    
    if ('serviceWorker' in navigator) {
        try {
            const registration = await navigator.serviceWorker.ready;
            if (registration.active) {
                // Try direct sync first
                registration.active.postMessage({ type: 'SYNC_NOW' });
                
                // Also register background sync as fallback
                if (registration.sync) {
                    await registration.sync.register('sync-labor-registration');
                }
                
                // Show success feedback
                showSyncMessage('Sync initiated! Check for notifications.', 'info');
            } else {
                showSyncMessage('Service worker not active', 'warning');
            }
        } catch (error) {
            console.error('[Client] Failed to request manual sync:', error);
            showSyncMessage('Sync failed: ' + error.message, 'danger');
        }
    } else {
        showSyncMessage('Service workers not supported', 'warning');
    }
    
    // Reset button state
    if (button) {
        setTimeout(() => {
            button.disabled = false;
            button.innerHTML = 'Try Sync Now';
        }, 2000);
    }
}

// Function to show sync messages
function showSyncMessage(message, type = 'info') {
    // Remove existing sync messages
    const existingMessages = document.querySelectorAll('.sync-message');
    existingMessages.forEach(msg => msg.remove());
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `alert alert-${type} sync-message`;
    messageDiv.innerHTML = `
        <i class="fas fa-${type === 'info' ? 'info-circle' : type === 'danger' ? 'exclamation-triangle' : 'exclamation-circle'}"></i>
        ${message}
    `;
    
    // Add to top of page
    document.body.insertBefore(messageDiv, document.body.firstChild);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
    }, 5000);
}

// Function to handle online status and trigger sync
function handleOnlineStatus() {
    if (navigator.onLine) {
        console.log('[Client] Back online, registering sync');
        registerBackgroundSync();
        checkAndSyncPending();
    } else {
        console.log('[Client] Gone offline');
    }
}

// Function to check and sync pending registrations
async function checkAndSyncPending() {
    try {
        const pendingCount = await getPendingRegistrationsCount();
        if (pendingCount > 0) {
            console.log(`[Client] Found ${pendingCount} pending registrations, triggering sync`);
            setTimeout(() => {
                registerBackgroundSync();
            }, 1000); // Small delay to ensure network is stable
        }
    } catch (error) {
        console.error('[Client] Error checking pending registrations:', error);
    }
}



// Add event listeners for online/offline events
window.addEventListener('online', handleOnlineStatus);
window.addEventListener('offline', handleOnlineStatus);

// Modified function to store data offline
async function storeRegistrationOffline(registrationData) {
    try {
        // Your existing IndexedDB storage code here...
        console.log('[Client] Storing registration data offline...');
        
        // After successfully storing the data, register background sync
        const syncRegistered = await registerBackgroundSync();
        
        // Show user feedback
        showOfflineMessage(syncRegistered);
        
    } catch (error) {
        console.error('[Client] Failed to store data offline:', error);
        throw error;
    }
}

// Function to show offline message to user
function showOfflineMessage(syncRegistered = false) {
    // Remove any existing offline messages
    const existing = document.querySelectorAll('.offline-message');
    existing.forEach(msg => msg.remove());
    
    const message = document.createElement('div');
    message.className = 'alert alert-info offline-message position-fixed';
    message.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    message.innerHTML = `
        <i class="fas fa-wifi"></i>
        <strong>Stored Offline:</strong> Your registration has been saved${syncRegistered ? ' and will be submitted automatically when you\'re back online.' : '.'}
        <br>
        <button type="button" class="btn btn-sm btn-outline-primary mt-2" onclick="manualSync()">
            <i class="fas fa-sync"></i> Try Sync Now
        </button>
        <button type="button" class="btn btn-sm btn-outline-secondary mt-2 ms-1" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i> Dismiss
        </button>
    `;
    
    document.body.appendChild(message);
    
    // Auto-remove after 15 seconds
    setTimeout(() => {
        if (message.parentNode) {
            message.parentNode.removeChild(message);
        }
    }, 15000);
}

// Function to check for pending registrations and show status
async function checkPendingRegistrations() {
    try {
        const count = await getPendingRegistrationsCount();
        
        if (count > 0) {
            const statusDiv = document.createElement('div');
            statusDiv.className = 'alert alert-warning pending-status position-fixed';
            statusDiv.style.cssText = 'top: 20px; left: 20px; z-index: 9998; max-width: 400px;';
            statusDiv.innerHTML = `
                <i class="fas fa-clock"></i>
                <strong>Pending Submissions:</strong> You have ${count} registration(s) waiting to be submitted.
                <br>
                ${navigator.onLine ? 
                    '<button type="button" class="btn btn-sm btn-primary mt-2" onclick="manualSync()"><i class="fas fa-sync"></i> Sync Now</button>' : 
                    '<small class="text-muted">Will sync when online.</small>'
                }
                <button type="button" class="btn btn-sm btn-outline-secondary mt-2 ms-1" onclick="this.parentElement.remove()">
                    <i class="fas fa-times"></i> Dismiss
                </button>
            `;
            
            document.body.appendChild(statusDiv);
            
            // Auto-remove after 20 seconds
            setTimeout(() => {
                if (statusDiv.parentNode) {
                    statusDiv.parentNode.removeChild(statusDiv);
                }
            }, 20000);
        }
        
    } catch (error) {
        console.error('[Client] Failed to check pending registrations:', error);
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('[Client] Initializing sync functionality...');
    
    // Check for pending registrations
    checkPendingRegistrations();
    
    // Register sync if online
    if (navigator.onLine) {
        registerBackgroundSync();
    }
    
    // Check if service worker is supported
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.ready.then(registration => {
            console.log('[Client] Service worker ready');
        });
    }
});

// Listen for messages from service worker
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (event) => {
        console.log('[Client] Message from service worker:', event.data);
        
        if (event.data && event.data.type === 'SYNC_COMPLETE') {
            // Remove any offline/pending messages
            const offlineMessages = document.querySelectorAll('.offline-message, .pending-status');
            offlineMessages.forEach(msg => msg.remove());
            
            // Show success message
            showSyncMessage('Your offline registrations have been submitted successfully!', 'success');
            
            // Refresh pending count
            setTimeout(checkPendingRegistrations, 1000);
        }
    });
}

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        manualSync,
        registerBackgroundSync,
        storeRegistrationOffline,
        checkPendingRegistrations
    };
}

// multi_step_form_client.js - Complete implementation with background sync
// registration/static/registration/js/serviceworker.js const CACHE_NAME = 'labor-registration-cache-v1'; const DB_NAME = 'LaborRegistrationDB'; const DB_VERSION = 2; const STORE_PENDING_REGISTRATIONS = 'pending_registrations'; const STORE_OFFLINE_IMAGES = 'offline_images'; const urlsToCac

// Add these functions to your existing multi_step_form_client.js

// Mobile number validation and duplicate check
async function checkMobileNumberDuplicate(mobileNumber) {
    try {
        const response = await fetch('/register/api/check-mobile-number/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                mobile_number: mobileNumber
            })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error checking mobile number:', error);
        return { exists: false, message: 'Unable to check mobile number' };
    }
}

// Function to validate mobile number format
function validateMobileNumber(number) {
    const cleaned = number.replace(/[^\d]/g, '');
    return cleaned.length === 10 && /^[6-9]/.test(cleaned);
}

// Function to show mobile number error
function showMobileNumberError(message) {
    const errorDiv = document.getElementById('mobile-number-error');
    const mobileInput = document.querySelector('[name="mobile_number"]');
    
    if (errorDiv && mobileInput) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        mobileInput.classList.add('is-invalid');
    }
}

// Function to clear mobile number error
function clearMobileNumberError() {
    const errorDiv = document.getElementById('mobile-number-error');
    const mobileInput = document.querySelector('[name="mobile_number"]');
    
    if (errorDiv && mobileInput) {
        errorDiv.style.display = 'none';
        mobileInput.classList.remove('is-invalid');
    }
}

// Function to handle mobile number blur event (check for duplicates)
async function handleMobileNumberBlur(event) {
    const mobileNumber = event.target.value.trim();
    
    if (!mobileNumber) return;
    
    // Clear previous errors
    clearMobileNumberError();
    
    // Validate format first
    if (!validateMobileNumber(mobileNumber)) {
        showMobileNumberError('Please enter a valid 10-digit mobile number');
        return;
    }
    
    // Check for duplicate if online
    if (navigator.onLine) {
        const loadingSpinner = document.createElement('div');
        loadingSpinner.innerHTML = '<small class="text-info"><i class="fas fa-spinner fa-spin me-1"></i>Checking availability...</small>';
        loadingSpinner.id = 'mobile-check-loading';
        
        const mobileInput = document.querySelector('[name="mobile_number"]');
        mobileInput.parentNode.appendChild(loadingSpinner);
        
        try {
            const result = await checkMobileNumberDuplicate(mobileNumber);
            
            if (result.exists) {
                showMobileNumberError('This mobile number is already registered. Please use a different number.');
                
                // Show popup for immediate feedback
                if (confirm('This mobile number is already registered. Would you like to use a different number?')) {
                    event.target.focus();
                    event.target.select();
                }
            }
        } catch (error) {
            console.error('Failed to check mobile number:', error);
        } finally {
            const spinner = document.getElementById('mobile-check-loading');
            if (spinner) spinner.remove();
        }
    }
}

// Function to remove duplicate data from offline storage
async function removeDuplicateFromOffline(mobileNumber) {
    try {
        if (!db) await initDB();
        
        const tx = db.transaction([STORE_PENDING_REGISTRATIONS, STORE_OFFLINE_IMAGES], 'readwrite');
        const pendingStore = tx.objectStore(STORE_PENDING_REGISTRATIONS);
        const imageStore = tx.objectStore(STORE_OFFLINE_IMAGES);
        
        const allRegistrations = await pendingStore.getAll();
        
        for (const registration of allRegistrations) {
            const regMobileNumber = registration.data?.step1?.mobile_number;
            if (regMobileNumber && regMobileNumber.replace(/[^\d]/g, '') === mobileNumber.replace(/[^\d]/g, '')) {
                // Remove the registration
                await pendingStore.delete(registration.id);
                
                // Remove associated image if exists
                if (registration.data?.step1?.photoId) {
                    await imageStore.delete(registration.data.step1.photoId);
                }
                
                console.log(`Removed duplicate registration for mobile number: ${mobileNumber}`);
            }
        }
        
        await tx.done;
        await updateSyncStatusUI(); // Update the UI to reflect changes
        
    } catch (error) {
        console.error('Error removing duplicate from offline storage:', error);
    }
}

// Updated sync function with duplicate checking
async function syncSingleRegistrationWithDuplicateCheck(reg, pendingStore, imageStore) {
    try {
        const mobileNumber = reg.data?.step1?.mobile_number;
        
        // Check for duplicate before syncing if online
        if (mobileNumber && navigator.onLine) {
            const duplicateCheck = await checkMobileNumberDuplicate(mobileNumber);
            if (duplicateCheck.exists) {
                console.warn(`Duplicate mobile number found during sync: ${mobileNumber}`);
                
                // Remove from offline storage
                await pendingStore.delete(reg.id);
                if (reg.data?.step1?.photoId) {
                    await imageStore.delete(reg.data.step1.photoId);
                }
                
                // Show notification about duplicate
                if ('Notification' in window && Notification.permission === 'granted') {
                    new Notification('Duplicate Registration Removed', {
                        body: `Registration with mobile number ${mobileNumber} was removed as it already exists in database.`,
                        icon: '/static/images/android-chrome-192x192.png'
                    });
                }
                
                throw new Error(`Duplicate mobile number: ${mobileNumber}. Registration removed from offline storage.`);
            }
        }
        
        // Proceed with normal sync if no duplicate
        return await syncSingleRegistration(reg, pendingStore, imageStore);
        
    } catch (error) {
        throw error;
    }
}

// Updated processAndSendRegistration with better image handling
async function processAndSendRegistration(fullRegistrationData, dbKey = null) {
    try {
        // Check for duplicate mobile number first
        const mobileNumber = fullRegistrationData.step1?.mobile_number;
        if (mobileNumber && navigator.onLine) {
            const duplicateCheck = await checkMobileNumberDuplicate(mobileNumber);
            if (duplicateCheck.exists) {
                console.warn(`Duplicate mobile number found: ${mobileNumber}`);
                if (dbKey) {
                    await removeDuplicateFromOffline(mobileNumber);
                }
                throw new Error(`Mobile number ${mobileNumber} is already registered.`);
            }
        }
        
        const formData = new FormData();
        console.log('Preparing to send registration data to server:', fullRegistrationData);

        // Append all fields to FormData (excluding photo-related fields)
        const allSteps = { ...fullRegistrationData.step1, ...fullRegistrationData.step2, ...fullRegistrationData.step3 };
        for (const key in allSteps) {
            if (allSteps.hasOwnProperty(key)) {
                if (Array.isArray(allSteps[key]) || (typeof allSteps[key] === 'object' && allSteps[key] !== null && key !== 'location')) {
                    formData.append(key, JSON.stringify(allSteps[key]));
                } else if (key === 'location' && allSteps[key] !== null) {
                    formData.append(key, JSON.stringify(allSteps[key]));
                } else if (key !== 'photoId' && key !== 'photoBase64') {
                    formData.append(key, allSteps[key]);
                }
            }
        }

        // --- CORRECTED IMAGE HANDLING LOGIC ---
        let imageBlob = null;
        let imageName = 'captured_image.jpeg';

        if (fullRegistrationData.step1?.photoId) {
            try {
                const db = await openDB(DB_NAME, DB_VERSION);
                const imageData = await db.get(STORE_OFFLINE_IMAGES, fullRegistrationData.step1.photoId);
                if (imageData && imageData.image instanceof Blob) {
                    imageBlob = imageData.image;
                    imageName = imageData.name || imageName;
                }
            } catch (error) {
                console.error('Error retrieving image from IndexedDB:', error);
            }
        }

        if (!imageBlob && fullRegistrationData.step1?.photoBase64) {
            try {
                const response = await fetch(fullRegistrationData.step1.photoBase64);
                const blob = await response.blob();
                if (blob.size > 0) {
                    imageBlob = blob;
                }
            } catch (error) {
                console.error('Failed to convert base64 to Blob:', error);
            }
        }

        if (imageBlob instanceof Blob && imageBlob.size > 0) {
            formData.append('photo', imageBlob, imageName);
            console.log(`Image appended to FormData successfully. Filename: ${imageName}, Size: ${imageBlob.size} bytes`);
        } else {
            console.warn('No image was found or appended to form data.');
        }

        // Debug FormData contents
        console.log('--- FormData Contents ---');
        for (const pair of formData.entries()) {
            if (pair[0] === 'photo') {
                console.log(`${pair[0]}: [File Blob - ${pair[1].size} bytes, type: ${pair[1].type}]`);
            } else {
                console.log(`${pair[0]}: ${pair[1]}`);
            }
        }
        console.log('--- End FormData Contents ---');

        // Send to server
        const response = await fetch('/register/api/submit-registration/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
            },
        });

        if (response.ok) {
            console.log('Registration submitted successfully.');
            if (dbKey) {
                const db = await openDB(DB_NAME, DB_VERSION);
                const tx = db.transaction([STORE_PENDING_REGISTRATIONS, STORE_OFFLINE_IMAGES], 'readwrite');
                await tx.objectStore(STORE_PENDING_REGISTRATIONS).delete(dbKey);
                if (fullRegistrationData.step1?.photoId) {
                    await tx.objectStore(STORE_OFFLINE_IMAGES).delete(fullRegistrationData.step1.photoId);
                    console.log(`Image ID ${fullRegistrationData.step1.photoId} removed from IndexedDB`);
                }
                await tx.done;
                console.log(`Registration ID ${dbKey} cleaned up from IndexedDB`);
            }
            return true;
        } else {
            const errorResponse = await response.json();
            console.error('Server rejected submission:', response.status, errorResponse);
            if (errorResponse.error_type === 'duplicate_mobile') {
                if (dbKey) {
                    await removeDuplicateFromOffline(mobileNumber);
                }
                throw new Error(errorResponse.message);
            }
            return false;
        }
    } catch (error) {
        console.error('Error in processAndSendRegistration:', error);
        throw error;
    }
}

async function handleNextSubmit(event) {
    event.preventDefault();

    const currentStep = parseInt(document.querySelector('input[name="step"]').value);
    const form = document.getElementById('registrationForm');
    let isValid = true;
    let currentRegistration = await getCurrentRegistrationData();
    let stepData = {};

    function getFieldValue(name) {
        const element = form.querySelector(`[name="${name}"]`);
        if (!element) return null;
        if (element.type === 'checkbox' || element.type === 'radio') {
            const selected = form.querySelector(`[name="${name}"]:checked`);
            return selected ? selected.value : (element.type === 'checkbox' ? element.checked : '');
        }
        if (element.tagName === 'SELECT') { return element.value; }
        return element.value.trim();
    }
    function getCheckboxValues(name) {
        const checkboxes = form.querySelectorAll(`input[name="${name}"]:checked`);
        return Array.from(checkboxes).map(cb => cb.value);
    }
    
    form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

    if (currentStep === 1) {
        const requiredFields = ['full_name', 'mobile_number', 'taluka', 'village', 'category'];
        requiredFields.forEach(fieldName => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (field && !getFieldValue(fieldName)) {
                field.classList.add('is-invalid');
                isValid = false;
            }
        });

        const mobileNumber = getFieldValue('mobile_number');
        if (mobileNumber && !validateMobileNumber(mobileNumber)) {
            showMobileNumberError('Please enter a valid 10-digit mobile number');
            isValid = false;
        } else if (mobileNumber && navigator.onLine) {
            const duplicateCheck = await checkMobileNumberDuplicate(mobileNumber);
            if (duplicateCheck.exists) {
                showMobileNumberError('This mobile number is already registered. Please use a different number.');
                isValid = false;
                setTimeout(() => {
                    alert('This mobile number is already registered. Please change the number to continue.');
                    document.querySelector('[name="mobile_number"]').focus();
                }, 100);
            }
        }

        const capturedPhotoHiddenInput = document.getElementById('captured_photo_hidden');
        const uploadedPhotoFiles = document.querySelector('input[name="photo"]').files;

        // More robust check for photo validity
        const photoAvailable = !!(capturedPhotoHiddenInput.value || uploadedPhotoFiles.length > 0 || photoBlob);
        if (!photoAvailable) {
            if (!confirm('No photo was captured or uploaded. Do you want to continue without a photo?')) {
                isValid = false;
            }
        } else if (capturedPhotoHiddenInput.value) {
            const photoConfirmedDiv = document.getElementById('photo-confirmed');
            const photoPreviewDiv = document.getElementById('photo-preview');
            if (photoPreviewDiv.style.display !== 'none' && photoConfirmedDiv.style.display === 'none') {
                alert('Please confirm your photo by clicking "Use This Photo" or retake it if you\'re not satisfied.');
                isValid = false;
                photoPreviewDiv.scrollIntoView({ behavior: 'smooth' });
            }
        }

        const latitude = document.getElementById('latitude_hidden').value;
        const longitude = document.getElementById('longitude_hidden').value;
        if (!latitude || !longitude) {
            if (!confirm('Location was not captured. Do you want to continue without location?')) {
                isValid = false;
            }
        }

        if (!isValid) {
            const firstInvalid = document.querySelector('.is-invalid');
            if (firstInvalid) {
                firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstInvalid.focus();
            }
            return;
        }
        
        // **CRUCIAL CHANGE:** Save image BEFORE saving the form data
        let imageId = null;
        if (photoBlob) {
            console.log('Attempting to save photoBlob to IndexedDB:', photoBlob);
            try {
                imageId = await saveImageBlob(photoBlob, 'captured_image.jpeg', photoBlob.type);
                console.log('Successfully saved image to IndexedDB with ID:', imageId);
            } catch (e) {
                console.error('Error saving image blob to IndexedDB:', e);
            }
        } else if (uploadedPhotoFiles.length > 0) {
            const uploadedFile = uploadedPhotoFiles[0];
            console.log('Attempting to save uploaded file to IndexedDB:', uploadedFile);
            try {
                imageId = await saveImageBlob(uploadedFile, uploadedFile.name, uploadedFile.type);
                console.log('Successfully saved uploaded file to IndexedDB with ID:', imageId);
            } catch (e) {
                console.error('Error saving uploaded file to IndexedDB:', e);
            }
        }

        // Now, collect stepData and include the imageId if available
        stepData = {
            full_name: getFieldValue('full_name'),
            mobile_number: getFieldValue('mobile_number'),
            category: getFieldValue('category'),
            taluka: getFieldValue('taluka'),
            village: getFieldValue('village'),
            location: (latitude && longitude) ? {
                latitude: parseFloat(latitude),
                longitude: parseFloat(longitude),
                accuracy: parseFloat(document.getElementById('location_accuracy_hidden').value),
                timestamp: new Date().toISOString()
            } : null,
            photoId: imageId, // Link the form data to the image ID
            photoBase64: capturedPhotoHiddenInput.value // Keep this as a fallback
        };

        currentRegistration.step1 = stepData;
        await saveCurrentRegistrationData(currentRegistration);

        const categoryToPass = stepData.category;
        window.location.href = `?step=${currentStep + 1}&current_category_from_db=${encodeURIComponent(categoryToPass)}`;
    }  else if (currentStep === 2) {
        const categoryFromStep1 = currentRegistration.step1 ? currentRegistration.step1.category : '';
        const currentCategory = document.getElementById('currentCategorySession').value || categoryFromStep1;

        let requiredFields = [];
        switch(currentCategory) {
            case 'individual_labor':
                requiredFields = [
                    'gender', 'age', 'primary_source_income', 'employment_type',
                    'willing_to_migrate', 'expected_wage', 'availability'
                ];
                break;
            case 'mukkadam':
                requiredFields = [
                    'providing_labour_count', 'total_workers_peak', 'expected_charges',
                    'labour_supply_availability', 'arrange_transport', 'supply_areas'
                ];
                break;
            case 'transport':
                requiredFields = [
                    'vehicle_type', 'people_capacity', 'expected_fair',
                    'availability', 'service_areas'
                ];
                break;
            case 'others':
                requiredFields = [
                    'business_name', 'help_description'
                ];
                break;
        }

        requiredFields.forEach(fieldName => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                let fieldValue = getFieldValue(fieldName);
                if (field.type === 'number' && ['age', 'providing_labour_count', 'total_workers_peak', 'people_capacity'].includes(fieldName)) {
                    if (!fieldValue || parseInt(fieldValue) <= 0 || isNaN(parseInt(fieldValue))) {
                        field.classList.add('is-invalid');
                        isValid = false;
                    }
                } else if (!fieldValue && (field.type !== 'checkbox' || !field.checked)) {
                    field.classList.add('is-invalid');
                    isValid = false;
                }
            }
        });

        if (currentCategory === 'individual_labor') {
            const skillCheckboxes = getCheckboxValues('skills');
            if (skillCheckboxes.length === 0) {
                if (!confirm('No skills selected. Are you sure you want to continue without specifying any skills?')) {
                    isValid = false;
                }
            }

            const commCheckboxes = getCheckboxValues('communication_preferences');
            if (commCheckboxes.length === 0) {
                if (!confirm('No communication preferences selected. Please select at least one way to contact you.')) {
                    isValid = false;
                }
            }
        } else if (currentCategory === 'mukkadam') {
            const skillCheckboxes = getCheckboxValues('skills');
            if (skillCheckboxes.length === 0) {
                if (!confirm('No skills specified for your workers. Are you sure you want to continue?')) {
                    isValid = false;
                }
            }

            const providingCount = parseInt(getFieldValue('providing_labour_count')) || 0;
            const peakCount = parseInt(getFieldValue('total_workers_peak')) || 0;
            if (peakCount < providingCount) {
                alert('Total workers at peak cannot be less than regular providing labour count.');
                form.querySelector('[name="total_workers_peak"]').classList.add('is-invalid');
                isValid = false;
            }

            const arrangeTransport = getFieldValue('arrange_transport');
            if (arrangeTransport === 'other') {
                const arrangeTransportOther = getFieldValue('arrange_transport_other');
                if (!arrangeTransportOther) {
                    form.querySelector('[name="arrange_transport_other"]').classList.add('is-invalid');
                    isValid = false;
                }
            }
        }

        if (!isValid) {
            const firstInvalid = document.querySelector('.is-invalid');
            if (firstInvalid) {
                firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstInvalid.focus();
            }
            return;
        }

        // Collect step 2 data based on category
        if (currentCategory === 'individual_labor') {
            stepData = {
                gender: getFieldValue('gender'), age: parseInt(getFieldValue('age')) || null, primary_source_income: getFieldValue('primary_source_income'), employment_type: getFieldValue('employment_type'),
                skills: getCheckboxValues('skills'), willing_to_migrate: getFieldValue('willing_to_migrate') === 'yes', expected_wage: getFieldValue('expected_wage'), availability: getFieldValue('availability'),
                adult_men_seeking_employment: parseInt(getFieldValue('adult_men_seeking_employment')) || 0, adult_women_seeking_employment: parseInt(getFieldValue('adult_women_seeking_employment')) || 0,
                communication_preferences: getCheckboxValues('communication_preferences')
            };
        } else if (currentCategory === 'mukkadam') {
            stepData = {
                providing_labour_count: parseInt(getFieldValue('providing_labour_count')) || null, total_workers_peak: parseInt(getFieldValue('total_workers_peak')) || null, expected_charges: getFieldValue('expected_charges'),
                labour_supply_availability: getFieldValue('labour_supply_availability'), arrange_transport: getFieldValue('arrange_transport'), arrange_transport_other: getFieldValue('arrange_transport_other'),
                supply_areas: getCheckboxValues('supply_areas'), skills: getCheckboxValues('skills'),
            };
        } else if (currentCategory === 'transport') {
            stepData = {
                vehicle_type: getFieldValue('vehicle_type'), people_capacity: parseInt(getFieldValue('people_capacity')) || null, expected_fair: getFieldValue('expected_fair'),
                availability: getFieldValue('availability'), 
                // FIX: Use getCheckboxValues for the checkboxes
                service_areas: getCheckboxValues('service_areas'),
            };
        } else if (currentCategory === 'others') {
            stepData = {
                business_name: getFieldValue('business_name'), help_description: getFieldValue('help_description'),
            };
        }
        currentRegistration.step2 = stepData;
        await saveCurrentRegistrationData(currentRegistration);

        const categoryToPass = currentRegistration.step1 ? currentRegistration.step1.category : '';
        window.location.href = `?step=${currentStep + 1}&current_category_from_db=${encodeURIComponent(categoryToPass)}`;

    } else if (currentStep === 3) {
        const agreement = document.querySelector('input[name="data_sharing_agreement"]');
        if (!agreement.checked) {
            alert('Please accept the data sharing agreement to proceed.');
            agreement.focus();
            return;
        }

        stepData = {
            data_sharing_agreement: agreement.checked
        };
        currentRegistration.step3 = stepData;
        await saveCurrentRegistrationData(currentRegistration);

        await submitFullRegistration();
    }
}

// Updated submit full registration with better error handling
async function submitFullRegistration() {
    const fullRegistrationData = await getCurrentRegistrationData();
    if (!fullRegistrationData || !fullRegistrationData.step1 || !fullRegistrationData.step2 || !fullRegistrationData.step3) {
        console.error('Incomplete registration data found for submission. Cannot submit.');
        alert('An error occurred. Please ensure all steps are completed before submitting.');
        return;
    }

    const isOnline = navigator.onLine;

    if (isOnline) {
        console.log('Online, attempting immediate submission.');
        try {
            const success = await processAndSendRegistration(fullRegistrationData);
            if (success) {
                await clearCurrentRegistrationAndImage();
                alert('Registration submitted successfully!');
                window.location.href = '/register/success/';
                return;
            }
        } catch (error) {
            if (error.message.includes('already registered')) {
                alert('This mobile number is already registered in our system. Your offline data has been cleared.');
                await clearCurrentRegistrationAndImage();
                window.location.href = '/register/';
                return;
            }
            console.log('Immediate online submission failed, falling back to background sync.');
        }
    }

    // Store for offline sync
    await saveForBackgroundSync(fullRegistrationData);
    await clearCurrentRegistrationAndImage();

    if ('serviceWorker' in navigator && 'SyncManager' in window) {
        const registration = await navigator.serviceWorker.ready;
        await registration.sync.register('sync-labor-registration');
        alert('You are offline. Your registration will be submitted when you are back online.');
    } else {
        alert('Your data is saved locally. It might be lost if you clear browser data.');
    }
    
    window.location.href = '/register/success/';
}

// Add event listener for mobile number field
document.addEventListener('DOMContentLoaded', function() {
    // ... existing DOMContentLoaded code ...
    
    // Add mobile number blur event listener
    const mobileInput = document.querySelector('[name="mobile_number"]');
    if (mobileInput) {
        mobileInput.addEventListener('blur', handleMobileNumberBlur);
        mobileInput.addEventListener('input', clearMobileNumberError);
    }
});

// Helper functions (add these if not already present)
function getFieldValue(name) {
    const element = document.querySelector(`[name="${name}"]`);
    if (!element) return null;
    if (element.type === 'checkbox' || element.type === 'radio') {
        const selected = document.querySelector(`[name="${name}"]:checked`);
        return selected ? selected.value : '';
    }
    if (element.tagName === 'SELECT') {
        return element.value;
    }
    return element.value.trim();
}

function getCheckboxValues(name) {
    const checkboxes = document.querySelectorAll(`input[name="${name}"]:checked`);
    return Array.from(checkboxes).map(cb => cb.value);
}

