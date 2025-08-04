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
        navigator.serviceWorker.register('/static/registration/js/serviceworker.js')
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
}

// --- UI Initialization and Event Listeners ---
document.addEventListener('DOMContentLoaded', async function() {
    await initDB();

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
        nextBtn.addEventListener('click', handleNextSubmit);
    }
});

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
                document.getElementById('captured_photo_hidden').value = reader.result;
                document.getElementById('camera-section').style.display = 'none';
                document.getElementById('photo-preview').style.display = 'none';
                document.getElementById('photo-confirmed').style.display = 'block';
                document.getElementById('camera-status').innerHTML = '<p class="text-success"><i class="fas fa-check-circle me-2"></i>Photo loaded from offline storage!</p>';
            };
            reader.readAsDataURL(photoBlob);
        }
    } else if (step1Data.photoBase64) {
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
        document.getElementById('location-info').style.display = 'block';
        document.getElementById('location-error').style.display = 'none';
        document.getElementById('get-location').innerHTML = '<i class="fas fa-check me-2"></i>Location Captured';
        document.getElementById('get-location').disabled = false;
        document.getElementById('get-location').className = 'btn btn-success';
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
        transportSelect.dispatchEvent(new Event('change'));
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

// --- Navigation Logic (Updated for IndexedDB) ---
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
        if (element.type === 'checkbox') {
            return element.checked;
        }
        if (element.type === 'radio') {
            const selectedRadio = form.querySelector(`[name="${name}"]:checked`);
            return selectedRadio ? selectedRadio.value : '';
        }
        if (element.tagName === 'SELECT') {
            return element.value;
        }
        return element.value.trim();
    }

    function getCheckboxValues(name) {
        const checkboxes = form.querySelectorAll(`input[name="${name}"]:checked`);
        return Array.from(checkboxes).map(cb => cb.value);
    }

    if (currentStep === 1) {
        const requiredFields = ['full_name', 'mobile_number', 'taluka', 'village', 'category'];
        requiredFields.forEach(fieldName => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                if (!getFieldValue(fieldName)) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            }
        });

        const capturedPhotoHiddenInput = document.getElementById('captured_photo_hidden');
        const uploadedPhotoFiles = document.querySelector('input[name="photo"]').files;

        if (!capturedPhotoHiddenInput.value && uploadedPhotoFiles.length === 0 && !photoBlob) {
            if (!confirm('No photo was captured or uploaded. A photo helps with verification and improves your chances of getting work. Do you want to continue without a photo?')) {
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

        const latitude = getFieldValue('latitude');
        const longitude = getFieldValue('longitude');
        if (!latitude || !longitude) {
            if (!confirm('Location was not captured. This may affect service quality. Do you want to continue without location?')) {
                 isValid = false;
            }
        }

        if (!isValid) {
            event.preventDefault();
            if (!document.querySelector('.is-invalid')) {
                alert('Please fill in all required fields.');
            }
            const firstInvalid = document.querySelector('.is-invalid');
            if (firstInvalid) {
                firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstInvalid.focus();
            }
            return;
        }

        stepData = {
            full_name: getFieldValue('full_name'),
            mobile_number: getFieldValue('mobile_number'),
            category: getFieldValue('category'),
            taluka: getFieldValue('taluka'),
            village: getFieldValue('village'),
            location: latitude ? {
                latitude: parseFloat(latitude),
                longitude: parseFloat(longitude),
                accuracy: parseFloat(getFieldValue('location_accuracy')),
                timestamp: new Date().toISOString()
            } : null,
            photoId: null,
            photoBase64: capturedPhotoHiddenInput.value
        };

        let imageId = null;
        if (photoBlob) {
            imageId = await saveImageBlob(photoBlob, 'captured_image.jpeg', photoBlob.type);
            stepData.photoId = imageId;
            stepData.photoBase64 = null;
        } else if (uploadedPhotoFiles.length > 0) {
            const uploadedFile = uploadedPhotoFiles[0];
            imageId = await saveImageBlob(uploadedFile, uploadedFile.name, uploadedFile.type);
            stepData.photoId = imageId;
            stepData.photoBase64 = null;
        }
        currentRegistration.step1 = stepData;
        await saveCurrentRegistrationData(currentRegistration);

        document.getElementById('currentCategoryHidden').value = stepData.category;
        window.location.href = `?step=${currentStep + 1}&current_category_from_db=${encodeURIComponent(stepData.category)}`;

    } else if (currentStep === 2) {
        const categoryFromStep1 = currentRegistration.step1 ? currentRegistration.step1.category : '';
        const currentCategory = document.getElementById('currentCategorySession').value || categoryFromStep1;

        let requiredFields = [];
        switch(currentCategory) {
            case 'individual_labor':
                requiredFields = [
                    'gender', 'age', 'primary_source_income', 'employment_type',
                    'willing_to_migrate', 'expected_wage', 'availability',
                    'adult_men_seeking_employment', 'adult_women_seeking_employment'
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
                    if (!fieldValue || parseInt(fieldValue) <= 0) {
                        field.classList.add('is-invalid');
                        isValid = false;
                    } else {
                        field.classList.remove('is-invalid');
                    }
                } else if (!fieldValue && (field.type !== 'checkbox' || !field.checked)) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
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
        }

        if (currentCategory === 'mukkadam') {
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
        }

        if (!isValid) {
            event.preventDefault();
            if (!document.querySelector('.is-invalid')) {
                alert('Please fill in all required fields correctly.');
            }
            const firstInvalid = document.querySelector('.is-invalid');
            if (firstInvalid) {
                firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstInvalid.focus();
            }
            return;
        }

        if (currentCategory === 'individual_labor') {
            stepData = {
                gender: getFieldValue('gender'), age: parseInt(getFieldValue('age')), primary_source_income: getFieldValue('primary_source_income'), employment_type: getFieldValue('employment_type'),
                skills: getCheckboxValues('skills'), willing_to_migrate: getFieldValue('willing_to_migrate'), expected_wage: getFieldValue('expected_wage'), availability: getFieldValue('availability'),
                adult_men_seeking_employment: parseInt(getFieldValue('adult_men_seeking_employment')) || 0, adult_women_seeking_employment: parseInt(getFieldValue('adult_women_seeking_employment')) || 0,
                communication_preferences: getCheckboxValues('communication_preferences')
            };
        } else if (currentCategory === 'mukkadam') {
            stepData = {
                providing_labour_count: parseInt(getFieldValue('providing_labour_count')) || 0, total_workers_peak: parseInt(getFieldValue('total_workers_peak')) || 0, expected_charges: getFieldValue('expected_charges'),
                labour_supply_availability: getFieldValue('labour_supply_availability'), arrange_transport: getFieldValue('arrange_transport'), arrange_transport_other: getFieldValue('arrange_transport_other'),
                supply_areas: getFieldValue('supply_areas'), skills: getCheckboxValues('skills'),
            };
        } else if (currentCategory === 'transport') {
            stepData = {
                vehicle_type: getFieldValue('vehicle_type'), people_capacity: parseInt(getFieldValue('people_capacity')) || 0, expected_fair: getFieldValue('expected_fair'),
                availability: getFieldValue('availability'), service_areas: getFieldValue('service_areas'),
            };
        } else if (currentCategory === 'others') {
            stepData = {
                business_name: getFieldValue('business_name'), help_description: getFieldValue('help_description'),
            };
        }
        currentRegistration.step2 = stepData;
        await saveCurrentRegistrationData(currentRegistration);

        const categoryToPass = currentRegistration.step1 ? currentRegistration.step1.category : '';
        document.getElementById('currentCategoryHidden').value = categoryToPass;
        window.location.href = `?step=${currentStep + 1}&current_category_from_db=${encodeURIComponent(categoryToPass)}`;

    } else if (currentStep === 3) {
        const agreement = document.querySelector('input[name="data_sharing_agreement"]');
        if (!agreement.checked) {
            alert('Please accept the data sharing agreement to proceed.');
            event.preventDefault();
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

async function submitFullRegistration() {
    const fullRegistrationData = await getCurrentRegistrationData();
    if (!fullRegistrationData || !fullRegistrationData.step1 || !fullRegistrationData.step2 || !fullRegistrationData.step3) {
        console.error('Incomplete registration data found for submission. Cannot submit.');
        alert('An error occurred. Please ensure all steps are completed before submitting.');
        return;
    }

    console.log('Attempting to submit full registration:', fullRegistrationData);

    const isOnline = navigator.onLine;

    if (isOnline) {
        try {
            console.log('Online, attempting immediate submission.');
            const success = await sendRegistrationToServer(fullRegistrationData);
            if (success) {
                await clearCurrentRegistrationAndImage();
                alert('Registration submitted successfully!');
                window.location.href = '/success/';
            } else {
                console.log('Immediate online submission failed, saving for background sync.');
                await saveForBackgroundSync(fullRegistrationData);
                alert('Submission failed, but your data is saved locally and will try to sync when you are online.');
                // Use a proper redirect to the success page to show the user the process is done
                window.location.href = '/success/';
            }
        } catch (error) {
            console.error('Error during online submission attempt:', error);
            await saveForBackgroundSync(fullRegistrationData);
            alert('An unexpected network error occurred. Your data is saved locally and will try to sync when you are back online.');
            window.location.href = '/success/';
        }
    } else {
        console.log('Offline, saving for background sync.');
        await saveForBackgroundSync(fullRegistrationData);
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
            const registration = await navigator.serviceWorker.ready;
            await registration.sync.register('sync-labor-registration');
            alert('You are offline. Your registration will be submitted when you are back online.');
        } else {
            alert('You are offline, and background sync is not fully supported by your browser. Your data is saved locally, but might be lost if you clear browser data before coming online.');
        }
        await clearCurrentRegistrationAndImage();
        window.location.href = '/success/';
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

async function sendRegistrationToServer(fullRegistrationData) {
    try {
        const formData = new FormData();

        for (const key in fullRegistrationData.step1) {
            if (fullRegistrationData.step1.hasOwnProperty(key) && key !== 'photoId' && key !== 'photoBase64' && key !== 'location') {
                formData.append(key, fullRegistrationData.step1[key]);
            }
        }
        if (fullRegistrationData.step1.location) {
            formData.append('location', JSON.stringify(fullRegistrationData.step1.location));
        }

        if (fullRegistrationData.step1.photoId) {
            const tx = db.transaction(STORE_OFFLINE_IMAGES, 'readonly');
            const imageStore = tx.objectStore(STORE_OFFLINE_IMAGES);
            const imageData = await imageStore.get(fullRegistrationData.step1.photoId);
            if (imageData && imageData.image) {
                formData.append('photo', imageData.image, imageData.name || 'captured_image.jpeg');
            }
        } else if (fullRegistrationData.step1.photoBase64) {
            const response = await fetch(fullRegistrationData.step1.photoBase64);
            const blob = await response.blob();
            formData.append('photo', blob, 'captured_image.jpeg');
        }

        if (fullRegistrationData.step2) {
            for (const key in fullRegistrationData.step2) {
                if (fullRegistrationData.step2.hasOwnProperty(key)) {
                    if (Array.isArray(fullRegistrationData.step2[key]) || (typeof fullRegistrationData.step2[key] === 'object' && fullRegistrationData.step2[key] !== null)) {
                        formData.append(key, JSON.stringify(fullRegistrationData.step2[key]));
                    } else {
                        formData.append(key, fullRegistrationData.step2[key]);
                    }
                }
            }
        }

        if (fullRegistrationData.step3) {
            formData.append('data_sharing_agreement', fullRegistrationData.step3.data_sharing_agreement);
        }

        const response = await fetch('.*/api/submit-registration/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
            },
        });

        if (response.ok) {
            const result = await response.json();
            console.log('Registration submitted successfully to backend:', result);
            return true;
        } else {
            const errorResponse = await response.json();
            console.error('Failed to submit registration:', response.status, errorResponse);
            return false;
        }
        
    } catch (error) {
        console.error('Error sending registration to server:', error);
        return false;
    }
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
                photoBlob = file;
                const reader = new FileReader();
                reader.onload = function(event) {
                    document.getElementById('captured-image').src = event.target.result;
                    document.getElementById('final-image').src = event.target.result;
                    document.getElementById('captured_photo_hidden').value = event.target.result;
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
        uploadFallback.style.display = 'none';

        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
        }

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

        document.getElementById('upload-fallback').style.display = 'block';
        document.querySelector('input[name="photo"]').style.display = 'block';
        document.getElementById('start-camera').style.display = 'none';
        document.getElementById('capture-photo').style.display = 'none';
        document.getElementById('switch-camera').style.display = 'none';
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
        photoBlob = blob;
        capturedImg.src = URL.createObjectURL(photoBlob);

        cameraSection.style.display = 'none';
        previewDiv.style.display = 'block';

        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
            cameraStream = null;
        }
    }, 'image/jpeg', 0.85);
}

function retakePhoto() {
    const cameraSection = document.getElementById('camera-section');
    const previewDiv = document.getElementById('photo-preview');
    const confirmedDiv = document.getElementById('photo-confirmed');

    cameraSection.style.display = 'block';
    previewDiv.style.display = 'none';
    confirmedDiv.style.display = 'none';
    document.getElementById('upload-fallback').style.display = 'none';

    if (document.getElementById('captured-image').src && document.getElementById('captured-image').src.startsWith('blob:')) {
        URL.revokeObjectURL(document.getElementById('captured-image').src);
    }
    photoBlob = null;
    document.getElementById('captured_photo_hidden').value = '';
    document.querySelector('input[name="photo"]').value = '';

    startCamera();
}

function confirmPhoto() {
    const previewDiv = document.getElementById('photo-preview');
    const confirmedDiv = document.getElementById('photo-confirmed');
    const finalImg = document.getElementById('final-image');
    const capturedPhotoInput = document.getElementById('captured_photo_hidden');

    if (photoBlob) {
        const reader = new FileReader();
        reader.onloadend = () => {
            capturedPhotoInput.value = reader.result;
            finalImg.src = reader.result;
            previewDiv.style.display = 'none';
            confirmedDiv.style.display = 'block';
            document.getElementById('camera-status').innerHTML = '<p class="text-success"><i class="fas fa-check-circle me-2"></i>Photo captured and confirmed!</p>';
        };
        reader.readAsDataURL(photoBlob);
    } else if (document.querySelector('input[name="photo"]').files.length > 0) {
          const reader = new FileReader();
          reader.onloadend = () => {
            capturedPhotoInput.value = reader.result;
            finalImg.src = reader.result;
            previewDiv.style.display = 'none';
            confirmedDiv.style.display = 'block';
            document.getElementById('camera-status').innerHTML = '<p class="text-success"><i class="fas fa-check-circle me-2"></i>Photo uploaded and confirmed!</p>';
          };
          reader.readAsDataURL(document.querySelector('input[name="photo"]').files[0]);
    } else {
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
        if (transportSelect.value === 'other') {
            transportOtherField.style.display = 'block';
        }
    }

    document.querySelectorAll('input[type="text"]').forEach(input => {
        if (input.name.includes('mobile_number')) {
            input.addEventListener('input', function(e) {
                let value = e.target.value.replace(/[^\d+]/g, '');
                if (value && !value.startsWith('+') && !value.startsWith('91') && value.length >= 10) {
                    value = '+91' + value;
                } else if (value.startsWith('91') && !value.startsWith('+91')) {
                    value = '+' + value;
                }
                e.target.value = value;
            });
        }
    });
}

async function goBack() {
    const currentStep = parseInt(document.querySelector('input[name="step"]').value);
    const form = document.getElementById('registrationForm');
    let currentRegistration = await getCurrentRegistrationData();
    let stepData = {};

    function getFieldValue(name) {
        const element = form.querySelector(`[name="${name}"]`);
        if (!element) return null;
        if (element.type === 'checkbox') { return element.checked; }
        if (element.type === 'radio') { const selectedRadio = form.querySelector(`[name="${name}"]:checked`); return selectedRadio ? selectedRadio.value : ''; }
        if (element.tagName === 'SELECT') { return element.value; }
        return element.value.trim();
    }
    function getCheckboxValues(name) {
        const checkboxes = form.querySelectorAll(`input[name="${name}"]:checked`);
        return Array.from(checkboxes).map(cb => cb.value);
    }

    if (currentStep === 2) {
        const categoryFromStep1 = currentRegistration.step1 ? currentRegistration.step1.category : '';
        const currentCategory = document.getElementById('currentCategorySession').value || categoryFromStep1;

        if (currentCategory === 'individual_labor') {
            stepData = {
                gender: getFieldValue('gender'), age: parseInt(getFieldValue('age')), primary_source_income: getFieldValue('primary_source_income'), employment_type: getFieldValue('employment_type'),
                skills: getCheckboxValues('skills'), willing_to_migrate: getFieldValue('willing_to_migrate'), expected_wage: getFieldValue('expected_wage'), availability: getFieldValue('availability'),
                adult_men_seeking_employment: parseInt(getFieldValue('adult_men_seeking_employment')) || 0, adult_women_seeking_employment: parseInt(getFieldValue('adult_women_seeking_employment')) || 0,
                communication_preferences: getCheckboxValues('communication_preferences')
            };
        } else if (currentCategory === 'mukkadam') {
            stepData = {
                providing_labour_count: parseInt(getFieldValue('providing_labour_count')) || 0, total_workers_peak: parseInt(getFieldValue('total_workers_peak')) || 0, expected_charges: getFieldValue('expected_charges'),
                labour_supply_availability: getFieldValue('labour_supply_availability'), arrange_transport: getFieldValue('arrange_transport'), arrange_transport_other: getFieldValue('arrange_transport_other'),
                supply_areas: getFieldValue('supply_areas'), skills: getCheckboxValues('skills'),
            };
        } else if (currentCategory === 'transport') {
            stepData = {
                vehicle_type: getFieldValue('vehicle_type'), people_capacity: parseInt(getFieldValue('people_capacity')) || 0, expected_fair: getFieldValue('expected_fair'),
                availability: getFieldValue('availability'), service_areas: getFieldValue('service_areas'),
            };
        } else if (currentCategory === 'others') {
            stepData = {
                business_name: getFieldValue('business_name'), help_description: getFieldValue('help_description'),
            };
        }
        currentRegistration.step2 = stepData;
    } else if (currentStep === 3) {
          stepData = {
            data_sharing_agreement: getFieldValue('data_sharing_agreement')
        };
        currentRegistration.step3 = stepData;
    }

    await saveCurrentRegistrationData(currentRegistration);
    window.location.href = `?step=${currentStep - 1}`;
}

window.addEventListener('beforeunload', function() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
    }
});
