// registration/static/registration/js/multi_step_form_client.js

// Import idb library for easier IndexedDB access
// Make sure your web server can serve ES modules from CDN, or download idb and serve locally.
import { openDB } from 'https://cdn.jsdelivr.net/npm/idb@7/+esm';

// Global variables for camera, photo, and IndexedDB instance
let cameraStream = null;
let photoBlob = null; // Store the captured photo as a Blob directly, not base64 until needed
let currentFacingMode = 'environment'; // Start with back camera (better for general photos)
let availableCameras = [];

// IndexedDB related constants and instance
let db;
const DB_NAME = 'LaborRegistrationDB'; // Name of your IndexedDB database
const DB_VERSION = 2; // IMPORTANT: Increment this version number whenever you change the database schema (e.g., add new object stores, change key paths, add indexes). This triggers the 'upgrade' event in initDB.
const STORE_CURRENT_REGISTRATION = 'current_registration_form'; // Store for the single ongoing, multi-step form data (draft)
const STORE_PENDING_REGISTRATIONS = 'pending_registrations'; // Store for completed forms awaiting synchronization
const STORE_OFFLINE_IMAGES = 'offline_images'; // Store for captured image Blobs

// --- PWA Service Worker Registration ---
// This part registers your service worker so it can start intercepting network requests
// and handle background sync.
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // The path here must be correct relative to your domain root (e.g., your Render URL)
        // Since it's in static/registration/js/, the path is /static/registration/js/serviceworker.js
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
// This function initializes your IndexedDB. It creates object stores if they don't exist
// or if the DB_VERSION is incremented (for schema upgrades).
async function initDB() {
    db = await openDB(DB_NAME, DB_VERSION, {
        upgrade(db, oldVersion, newVersion, transaction) {
            console.log(`IndexedDB upgrade: oldVersion=${oldVersion}, newVersion=${newVersion}`);
            // This 'if' block runs only when the DB is created or upgraded from a version less than 1
            if (oldVersion < 1) {
                // Creates object stores if they don't exist
                db.createObjectStore(STORE_CURRENT_REGISTRATION, { keyPath: 'id' }); // Stores the single active form draft
                db.createObjectStore(STORE_PENDING_REGISTRATIONS, { keyPath: 'id', autoIncrement: true }); // Stores completed forms waiting to be sent
                db.createObjectStore(STORE_OFFLINE_IMAGES, { keyPath: 'id', autoIncrement: true }); // Stores image Blobs
            }
            // Add more `if (oldVersion < X)` blocks here if you ever need to upgrade your DB schema in the future (e.g., add new indexes, change key paths, etc.)
            // Example for future:
            // if (oldVersion < 2) {
            //     const pendingStore = transaction.objectStore(STORE_PENDING_REGISTRATIONS);
            //     pendingStore.createIndex('timestamp', 'timestamp'); // Example of adding an index
            // }
        },
    });
    console.log('IndexedDB initialized.');
}

// --- Data Storage/Retrieval Functions (IndexedDB) ---

// Saves the entire current multi-step form's data (draft) to IndexedDB.
// It always uses the fixed key 'current_draft' so there's only one active draft.
async function saveCurrentRegistrationData(data) {
    if (!db) await initDB(); // Ensure DB is open
    const tx = db.transaction(STORE_CURRENT_REGISTRATION, 'readwrite'); // Start a transaction for read/write
    const store = tx.objectStore(STORE_CURRENT_REGISTRATION); // Get the object store
    await store.put({ id: 'current_draft', data: data }); // Put (insert or update) the data
    await tx.done; // Wait for the transaction to complete
    console.log('Current registration data saved to IndexedDB.');
}

// Retrieves the entire current multi-step form's data (draft) from IndexedDB.
async function getCurrentRegistrationData() {
    if (!db) await initDB(); // Ensure DB is open
    const tx = db.transaction(STORE_CURRENT_REGISTRATION, 'readonly'); // Read-only transaction
    const store = tx.objectStore(STORE_CURRENT_REGISTRATION);
    const record = await store.get('current_draft'); // Get the record with key 'current_draft'
    return record ? record.data : {}; // Return the 'data' property, or an empty object if no record
}

// Saves an image (as a Blob) to IndexedDB. Returns the ID of the stored image.
async function saveImageBlob(blob, fileName, mimeType) {
    if (!db) await initDB();
    const tx = db.transaction(STORE_OFFLINE_IMAGES, 'readwrite');
    const store = tx.objectStore(STORE_OFFLINE_IMAGES);
    // Add the image Blob with its name and type. IndexedDB will auto-increment the ID.
    const imageId = await store.add({ image: blob, name: fileName, type: mimeType });
    await tx.done;
    console.log('Image Blob saved to IndexedDB with ID:', imageId);
    return imageId; // Return the generated ID to link it with the form data
}

// Stores a *completed* registration form in a separate IndexedDB store,
// ready to be synchronized with the server when online.
async function saveForBackgroundSync(fullRegistrationData) {
    if (!db) await initDB();
    const tx = db.transaction(STORE_PENDING_REGISTRATIONS, 'readwrite');
    const store = tx.objectStore(STORE_PENDING_REGISTRATIONS);
    // Store the complete form data. A unique ID will be auto-generated.
    await store.add({
        data: fullRegistrationData,
        timestamp: Date.now(), // Store timestamp for potential ordering or debugging
        attemptedSync: 0 // Keep track of how many times sync has been attempted (for robust retry logic)
    });
    await tx.done;
    console.log('Full registration saved for background sync.');
}

// --- UI Initialization and Event Listeners ---
document.addEventListener('DOMContentLoaded', async function() {
    await initDB(); // Initialize IndexedDB as soon as the DOM is ready

    const currentStep = parseInt(document.querySelector('input[name="step"]').value); // Get current step from hidden input

    // Conditional initialization and data loading based on the current step
    if (currentStep === 1) {
        initializeCameraAndLocation(); // Setup camera and location functionality
        await loadStep1Data(); // Attempt to load previously saved data for Step 1
    } else if (currentStep === 2) {
        await loadStep2Data(); // Attempt to load previously saved data for Step 2
        initializeFormElements(); // Initialize dynamic form elements (e.g., show/hide fields)
    } else if (currentStep === 3) {
        await loadStep3Data(); // Attempt to load previously saved data for Step 3
    }

    // Register event listeners for the navigation buttons
    const prevBtn = document.getElementById('prevStepBtn');
    const nextBtn = document.getElementById('nextStepBtn');

    if (prevBtn) {
        prevBtn.addEventListener('click', goBack); // Attach goBack function to Previous button
    }
    if (nextBtn) {
        nextBtn.addEventListener('click', handleNextSubmit); // Attach handleNextSubmit to Next/Submit button
    }
});

// --- Load Data from IndexedDB (Pre-fill Forms) ---

// Loads and pre-fills data for Step 1 from IndexedDB.
async function loadStep1Data() {
    const currentRegistration = await getCurrentRegistrationData(); // Get the entire draft
    const step1Data = currentRegistration.step1 || {}; // Get Step 1 specific data, or empty object

    // Populate the form fields with loaded data
    document.querySelector('[name="full_name"]').value = step1Data.full_name || '';
    document.querySelector('[name="mobile_number"]').value = step1Data.mobile_number || '';
    document.querySelector('[name="category"]').value = step1Data.category || '';
    document.querySelector('[name="taluka"]').value = step1Data.taluka || '';
    document.querySelector('[name="village"]').value = step1Data.village || '';

    // Set the hidden input that Django uses to determine the category for rendering subsequent steps
    if (step1Data.category) {
         document.getElementById('currentCategoryHidden').value = step1Data.category;
    }

    // Load and display captured photo if available in IndexedDB
    if (step1Data.photoId) {
        const tx = db.transaction(STORE_OFFLINE_IMAGES, 'readonly');
        const imageStore = tx.objectStore(STORE_OFFLINE_IMAGES);
        const imageData = await imageStore.get(step1Data.photoId); // Retrieve the Blob using its ID
        if (imageData && imageData.image) {
            photoBlob = imageData.image; // Restore the global photoBlob variable
            const reader = new FileReader(); // Use FileReader to convert Blob to Data URL for display
            reader.onloadend = () => {
                document.getElementById('captured-image').src = reader.result;
                document.getElementById('final-image').src = reader.result;
                document.getElementById('captured_photo_hidden').value = reader.result; // Update hidden input for consistency
                // Adjust UI to show confirmed photo state
                document.getElementById('camera-section').style.display = 'none';
                document.getElementById('photo-preview').style.display = 'none';
                document.getElementById('photo-confirmed').style.display = 'block';
                document.getElementById('camera-status').innerHTML = '<p class="text-success"><i class="fas fa-check-circle me-2"></i>Photo loaded from offline storage!</p>';
            };
            reader.readAsDataURL(photoBlob); // Read the Blob as a Data URL
        }
    } else if (step1Data.photoBase64) { // Fallback for cases where base64 was stored directly (less ideal)
        document.getElementById('captured-image').src = step1Data.photoBase64;
        document.getElementById('final-image').src = step1Data.photoBase64;
        document.getElementById('captured_photo_hidden').value = step1Data.photoBase64;
        document.getElementById('camera-section').style.display = 'none';
        document.getElementById('photo-preview').style.display = 'none';
        document.getElementById('photo-confirmed').style.display = 'block';
        document.getElementById('camera-status').innerHTML = '<p class="text-success"><i class="fas fa-check-circle me-2"></i>Photo loaded from offline storage!</p>';
    }

    // Load and display location data if available
    if (step1Data.location) {
        const loc = step1Data.location;
        document.getElementById('latitude_hidden').value = loc.latitude || '';
        document.getElementById('longitude_hidden').value = loc.longitude || '';
        document.getElementById('location_accuracy_hidden').value = loc.accuracy || '';

        document.getElementById('location-coordinates').textContent = `${loc.latitude.toFixed(6)}, ${loc.longitude.toFixed(6)}`;
        document.getElementById('location-accuracy').textContent = `${loc.accuracy.toFixed(0)}m`;
        // Adjust UI to show confirmed location state
        document.getElementById('location-info').style.display = 'block';
        document.getElementById('location-error').style.display = 'none';
        document.getElementById('get-location').innerHTML = '<i class="fas fa-check me-2"></i>Location Captured';
        document.getElementById('get-location').disabled = false;
        document.getElementById('get-location').className = 'btn btn-success';
    }
}

// Loads and pre-fills data for Step 2 from IndexedDB.
async function loadStep2Data() {
    const currentRegistration = await getCurrentRegistrationData();
    const step2Data = currentRegistration.step2 || {};
    // Get category from Step 1 data to correctly pre-fill category-specific fields
    const categoryFromStep1 = currentRegistration.step1 ? currentRegistration.step1.category : '';

    // Set the hidden input for Django to correctly render category_forms.html
    if (categoryFromStep1) {
        document.getElementById('currentCategoryHidden').value = categoryFromStep1;
        document.getElementById('currentCategorySession').value = categoryFromStep1; // For JS internal use if needed
    }

    // Populate fields based on the category-specific data
    // You must add specific lines for each of your form fields from category_forms.html here.
    // Example fields are shown below.
    if (step2Data.gender) document.querySelector('[name="gender"]').value = step2Data.gender;
    if (step2Data.age) document.querySelector('[name="age"]').value = step2Data.age;
    if (step2Data.expected_wage) document.querySelector('[name="expected_wage"]').value = step2Data.expected_wage;

    // Handle checkbox lists (e.g., skills, communication_preferences)
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

    // Handle dropdowns and associated 'other' fields (e.g., for Mukkadam transport)
    const transportSelect = document.querySelector('select[name="arrange_transport"]');
    if (transportSelect && step2Data.arrange_transport) {
        transportSelect.value = step2Data.arrange_transport;
        transportSelect.dispatchEvent(new Event('change')); // Trigger change to show/hide 'other' field
    }
    if (step2Data.arrange_transport_other) {
        document.querySelector('[name="arrange_transport_other"]').value = step2Data.arrange_transport_other;
    }

    // Add similar pre-filling logic for other category-specific fields:
    // Mukkadam fields:
    if (step2Data.providing_labour_count) document.querySelector('[name="providing_labour_count"]').value = step2Data.providing_labour_count;
    if (step2Data.total_workers_peak) document.querySelector('[name="total_workers_peak"]').value = step2Data.total_workers_peak;
    if (step2Data.expected_charges) document.querySelector('[name="expected_charges"]').value = step2Data.expected_charges;
    if (step2Data.labour_supply_availability) document.querySelector('[name="labour_supply_availability"]').value = step2Data.labour_supply_availability;
    if (step2Data.supply_areas) document.querySelector('[name="supply_areas"]').value = step2Data.supply_areas;

    // Transport fields:
    if (step2Data.vehicle_type) document.querySelector('[name="vehicle_type"]').value = step2Data.vehicle_type;
    if (step2Data.people_capacity) document.querySelector('[name="people_capacity"]').value = step2Data.people_capacity;
    if (step2Data.expected_fair) document.querySelector('[name="expected_fair"]').value = step2Data.expected_fair;
    if (step2Data.service_areas) document.querySelector('[name="service_areas"]').value = step2Data.service_areas;

    // Others fields:
    if (step2Data.business_name) document.querySelector('[name="business_name"]').value = step2Data.business_name;
    if (step2Data.help_description) document.querySelector('[name="help_description"]').value = step2Data.help_description;
}

// Loads and pre-fills data for Step 3 from IndexedDB.
async function loadStep3Data() {
    const currentRegistration = await getCurrentRegistrationData();
    const step3Data = currentRegistration.step3 || {};
    // Pre-fill the agreement checkbox
    if (step3Data.data_sharing_agreement) {
        document.querySelector('input[name="data_sharing_agreement"]').checked = step3Data.data_sharing_agreement;
    }
    // Ensure category is passed for the context in Step 3 if needed for rendering
    const categoryFromStep1 = currentRegistration.step1 ? currentRegistration.step1.category : '';
    if (categoryFromStep1) {
        document.getElementById('currentCategoryHidden').value = categoryFromStep1;
    }
}


// --- Navigation Logic (Updated for IndexedDB) ---

// Handles "Next" button click for all steps, including final submission.
async function handleNextSubmit(event) {
    event.preventDefault(); // Prevent default form submission to handle it via JS

    const currentStep = parseInt(document.querySelector('input[name="step"]').value);
    const form = document.getElementById('registrationForm');
    let isValid = true; // Flag for form validation
    let currentRegistration = await getCurrentRegistrationData(); // Get the current draft from IndexedDB
    let stepData = {}; // Data object for the current step being processed

    // Helper to get a field's value, accounting for different input types (text, checkbox, radio, select)
    function getFieldValue(name) {
        const element = form.querySelector(`[name="${name}"]`);
        if (!element) return null; // Field not found on this step
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
        return element.value.trim(); // For text inputs, trim whitespace
    }

    // Helper to get values from a group of checkboxes (e.g., skills, communication_preferences)
    function getCheckboxValues(name) {
        const checkboxes = form.querySelectorAll(`input[name="${name}"]:checked`);
        return Array.from(checkboxes).map(cb => cb.value);
    }

    // --- Validation and Data Collection per Step ---
    if (currentStep === 1) {
        const requiredFields = ['full_name', 'mobile_number', 'taluka', 'village', 'category'];
        requiredFields.forEach(fieldName => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                if (!getFieldValue(fieldName)) { // Check if required field is empty
                    field.classList.add('is-invalid'); // Add Bootstrap validation class
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            }
        });

        // Photo validation logic: Check if a photo is confirmed (either captured or uploaded)
        const capturedPhotoHiddenInput = document.getElementById('captured_photo_hidden');
        const uploadedPhotoFiles = document.querySelector('input[name="photo"]').files;

        if (!capturedPhotoHiddenInput.value && uploadedPhotoFiles.length === 0 && !photoBlob) {
            // No photo captured or uploaded. Ask for confirmation to proceed without it.
            if (!confirm('No photo was captured or uploaded. A photo helps with verification and improves your chances of getting work. Do you want to continue without a photo?')) {
                isValid = false; // User chose not to continue without photo
            }
        } else if (capturedPhotoHiddenInput.value) {
            // A photo exists, but check if it's in the 'confirmed' state
            const photoConfirmedDiv = document.getElementById('photo-confirmed');
            const photoPreviewDiv = document.getElementById('photo-preview');

            if (photoPreviewDiv.style.display !== 'none' && photoConfirmedDiv.style.display === 'none') {
                // Photo captured, but not yet confirmed by clicking "Use This Photo"
                alert('Please confirm your photo by clicking "Use This Photo" or retake it if you\'re not satisfied.');
                isValid = false;
                photoPreviewDiv.scrollIntoView({ behavior: 'smooth' }); // Scroll to prompt user
            }
        }

        // Location validation logic: Check if location is captured
        const latitude = getFieldValue('latitude');
        const longitude = getFieldValue('longitude');
        if (!latitude || !longitude) {
            if (!confirm('Location was not captured. This may affect service quality. Do you want to continue without location?')) {
                 isValid = false; // User chose not to continue without location
            }
        }

        // If any validation failed, prevent form progression
        if (!isValid) {
            event.preventDefault();
            // Show a general alert if no specific fields are highlighted (e.g., for photo/location warnings)
            if (!document.querySelector('.is-invalid')) {
                alert('Please fill in all required fields.');
            }
            // Scroll to the first invalid field for better UX
            const firstInvalid = document.querySelector('.is-invalid');
            if (firstInvalid) {
                firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstInvalid.focus();
            }
            return; // Stop function execution
        }

        // Collect data specific to Step 1
        stepData = {
            full_name: getFieldValue('full_name'),
            mobile_number: getFieldValue('mobile_number'),
            category: getFieldValue('category'),
            taluka: getFieldValue('taluka'),
            village: getFieldValue('village'),
            location: latitude ? { // Store location as an object
                latitude: parseFloat(latitude),
                longitude: parseFloat(longitude),
                accuracy: parseFloat(getFieldValue('location_accuracy')),
                timestamp: new Date().toISOString() // Store timestamp for location capture
            } : null,
            photoId: null, // Will store IndexedDB ID if photoBlob is saved
            photoBase64: capturedPhotoHiddenInput.value // Fallback to store base64 string if no Blob was primarily handled
        };

        // Handle image storage: Prioritize Blob, then fallback to uploaded file.
        // Save the image Blob to IndexedDB and get its ID to link it with form data.
        let imageId = null;
        if (photoBlob) {
            imageId = await saveImageBlob(photoBlob, 'captured_image.jpeg', photoBlob.type);
            stepData.photoId = imageId; // Link the image ID to step1Data
            stepData.photoBase64 = null; // Clear base64 if Blob is used
        } else if (uploadedPhotoFiles.length > 0) {
            const uploadedFile = uploadedPhotoFiles[0];
            imageId = await saveImageBlob(uploadedFile, uploadedFile.name, uploadedFile.type);
            stepData.photoId = imageId;
            stepData.photoBase64 = null;
        }

        currentRegistration.step1 = stepData; // Update the full draft in memory
        await saveCurrentRegistrationData(currentRegistration); // Save the updated draft to IndexedDB
        window.location.href = `?step=${currentStep + 1}`; // Navigate to the next step

    } else if (currentStep === 2) {
        // Get the category from previously saved step 1 data
        const categoryFromStep1 = currentRegistration.step1 ? currentRegistration.step1.category : '';
        // Also check hidden input (from Django context or JS set)
        const currentCategory = document.getElementById('currentCategorySession').value || categoryFromStep1;

        let requiredFields = [];
        // Define required fields based on the identified category
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
            default:
                console.warn('Unknown category for step 2 validation. Proceeding with basic check.');
                break;
        }

        // Validate required fields for the current category
        requiredFields.forEach(fieldName => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                let fieldValue = getFieldValue(fieldName);
                // Special validation for number fields that must be greater than 0
                if (field.type === 'number' && ['age', 'providing_labour_count', 'total_workers_peak', 'people_capacity'].includes(fieldName)) {
                    if (!fieldValue || parseInt(fieldValue) <= 0) {
                        field.classList.add('is-invalid');
                        isValid = false;
                    } else {
                        field.classList.remove('is-invalid');
                    }
                } else if (!fieldValue && (field.type !== 'checkbox' || !field.checked)) { // Ensure checkbox is checked if required
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            }
        });

        // Additional specific validations for Individual Labor category
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

        // Additional specific validations for Mukkadam category
        if (currentCategory === 'mukkadam') {
            const skillCheckboxes = getCheckboxValues('skills'); // Assuming Mukkadam also has skills checkboxes
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

        // If any validation failed, prevent form progression
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

        // Collect data specific to Step 2 based on the category
        if (currentCategory === 'individual_labor') {
            stepData = {
                gender: getFieldValue('gender'),
                age: parseInt(getFieldValue('age')),
                primary_source_income: getFieldValue('primary_source_income'),
                employment_type: getFieldValue('employment_type'),
                skills: getCheckboxValues('skills'), // Stored as an array of selected values
                willing_to_migrate: getFieldValue('willing_to_migrate'),
                expected_wage: getFieldValue('expected_wage'),
                availability: getFieldValue('availability'),
                adult_men_seeking_employment: parseInt(getFieldValue('adult_men_seeking_employment')) || 0,
                adult_women_seeking_employment: parseInt(getFieldValue('adult_women_seeking_employment')) || 0,
                communication_preferences: getCheckboxValues('communication_preferences') // Stored as an array
            };
        } else if (currentCategory === 'mukkadam') {
            stepData = {
                providing_labour_count: parseInt(getFieldValue('providing_labour_count')) || 0,
                total_workers_peak: parseInt(getFieldValue('total_workers_peak')) || 0,
                expected_charges: getFieldValue('expected_charges'),
                labour_supply_availability: getFieldValue('labour_supply_availability'),
                arrange_transport: getFieldValue('arrange_transport'),
                arrange_transport_other: getFieldValue('arrange_transport_other'),
                supply_areas: getFieldValue('supply_areas'),
                skills: getCheckboxValues('skills'),
            };
        } else if (currentCategory === 'transport') {
            stepData = {
                vehicle_type: getFieldValue('vehicle_type'),
                people_capacity: parseInt(getFieldValue('people_capacity')) || 0,
                expected_fair: getFieldValue('expected_fair'),
                availability: getFieldValue('availability'),
                service_areas: getFieldValue('service_areas'),
            };
        } else if (currentCategory === 'others') {
            stepData = {
                business_name: getFieldValue('business_name'),
                help_description: getFieldValue('help_description'),
            };
        }
        currentRegistration.step2 = stepData; // Update the full draft
        await saveCurrentRegistrationData(currentRegistration); // Save to IndexedDB
        window.location.href = `?step=${currentStep + 1}`; // Navigate to next step

    } else if (currentStep === 3) {
        // Validation for the data sharing agreement checkbox
        const agreement = document.querySelector('input[name="data_sharing_agreement"]');
        if (!agreement.checked) {
            alert('Please accept the data sharing agreement to proceed.');
            event.preventDefault();
            agreement.focus();
            return;
        }

        // Collect data specific to Step 3
        stepData = {
            data_sharing_agreement: agreement.checked
        };
        currentRegistration.step3 = stepData; // Update the full draft
        await saveCurrentRegistrationData(currentRegistration); // Save to IndexedDB

        // If all steps are complete and validated, initiate the final submission process
        await submitFullRegistration();
    }
}

// Function to handle the final submission of the entire form data.
async function submitFullRegistration() {
    const fullRegistrationData = await getCurrentRegistrationData(); // Retrieve the complete form draft

    // Basic check to ensure all steps have some data (more robust validation happens at each step)
    if (!fullRegistrationData || !fullRegistrationData.step1 || !fullRegistrationData.step2 || !fullRegistrationData.step3) {
        console.error('Incomplete registration data found for submission. Cannot submit.');
        alert('An error occurred. Please ensure all steps are completed before submitting.');
        return;
    }

    console.log('Attempting to submit full registration:', fullRegistrationData);

    // Check if the user is currently online
    if (navigator.onLine) {
        console.log('Online, attempting immediate submission.');
        const success = await sendRegistrationToServer(fullRegistrationData); // Try to send to server immediately
        if (success) {
            await clearCurrentRegistrationAndImage(); // Clear local draft if successful
            alert('Registration submitted successfully!');
            window.location.href = '/registration-success/'; // Redirect to success page
        } else {
            // If immediate online submission fails (e.g., server error), save for background sync
            console.log('Immediate online submission failed, saving for background sync.');
            await saveForBackgroundSync(fullRegistrationData); // Save to pending queue
            alert('Submission failed, but your data is saved locally and will try to sync when you are online.');
            window.location.href = '/registration-success/'; // Redirect anyway for user experience
        }
    } else {
        // If offline, directly save for background sync
        console.log('Offline, saving for background sync.');
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
            // Ensure background sync API is supported
            await saveForBackgroundSync(fullRegistrationData); // Save to pending queue
            const registration = await navigator.serviceWorker.ready;
            await registration.sync.register('sync-labor-registration'); // Register a sync tag with the service worker
            alert('You are offline. Your registration will be submitted when you are back online.');
        } else {
            // Fallback for browsers that don't support Background Sync API
            alert('You are offline, and background sync is not fully supported by your browser. Your data is saved locally, but might be lost if you clear browser data before coming online.');
        }
        await clearCurrentRegistrationAndImage(); // Clear local draft after queuing for sync
        window.location.href = '/registration-success/'; // Redirect anyway for user experience
    }
}

// Clears the current draft registration and its associated image from IndexedDB.
// Called after a successful submission or after queuing for background sync.
async function clearCurrentRegistrationAndImage() {
    if (!db) await initDB();
    const currentRegistration = await getCurrentRegistrationData(); // Get the current draft to retrieve photoId
    const tx = db.transaction([STORE_CURRENT_REGISTRATION, STORE_OFFLINE_IMAGES], 'readwrite');
    await tx.objectStore(STORE_CURRENT_REGISTRATION).delete('current_draft'); // Delete the draft record
    // If a photo was associated with this draft, delete its Blob from the image store
    if (currentRegistration && currentRegistration.step1 && currentRegistration.step1.photoId) {
         await tx.objectStore(STORE_OFFLINE_IMAGES).delete(currentRegistration.step1.photoId);
    }
    await tx.done;
    console.log('Current registration and associated image cleared from IndexedDB.');
}


// --- Send Data to Django Backend (HTTP Fetch API) ---

// This function sends the complete form data (including image Blob) to your Django API endpoint.
// It's used for both immediate online submissions and by the Service Worker for background sync.
async function sendRegistrationToServer(fullRegistrationData) {
    try {
        const formData = new FormData(); // Create a FormData object to send mixed text and files

        // Append all fields from Step 1 data
        for (const key in fullRegistrationData.step1) {
            // Exclude photoId, photoBase64, and location (handled separately)
            if (fullRegistrationData.step1.hasOwnProperty(key) && key !== 'photoId' && key !== 'photoBase64' && key !== 'location') {
                formData.append(key, fullRegistrationData.step1[key]);
            }
        }
        // Location data is an object, so stringify it to JSON
        if (fullRegistrationData.step1.location) {
            formData.append('location', JSON.stringify(fullRegistrationData.step1.location));
        }

        // Append the photo Blob
        if (fullRegistrationData.step1.photoId) {
            const tx = db.transaction(STORE_OFFLINE_IMAGES, 'readonly');
            const imageStore = tx.objectStore(STORE_OFFLINE_IMAGES);
            const imageData = await imageStore.get(fullRegistrationData.step1.photoId); // Retrieve the actual Blob
            if (imageData && imageData.image) {
                // Append the Blob to FormData with its original name and type
                formData.append('photo', imageData.image, imageData.name || 'captured_image.jpeg');
            }
        } else if (fullRegistrationData.step1.photoBase64) {
            // Fallback: If image was stored as base64, convert it to Blob for sending
            const response = await fetch(fullRegistrationData.step1.photoBase64);
            const blob = await response.blob();
            formData.append('photo', blob, 'captured_image.jpeg');
        }

        // Append all fields from Step 2 data
        if (fullRegistrationData.step2) {
            for (const key in fullRegistrationData.step2) {
                if (fullRegistrationData.step2.hasOwnProperty(key)) {
                    // Convert arrays (like skills, communication_preferences) and other objects to JSON strings
                    if (Array.isArray(fullRegistrationData.step2[key]) || (typeof fullRegistrationData.step2[key] === 'object' && fullRegistrationData.step2[key] !== null)) {
                        formData.append(key, JSON.stringify(fullRegistrationData.step2[key]));
                    } else {
                        formData.append(key, fullRegistrationData.step2[key]);
                    }
                }
            }
        }

        // Append data from Step 3
        if (fullRegistrationData.step3) {
            // Boolean values convert to 'true'/'false' strings when appended to FormData
            formData.append('data_sharing_agreement', fullRegistrationData.step3.data_sharing_agreement);
        }

        // Send the FormData to your Django API endpoint
        const response = await fetch('/api/submit-registration/', {
            method: 'POST',
            body: formData, // FormData automatically sets Content-Type: multipart/form-data
            headers: {
                'X-CSRFToken': getCookie('csrftoken'), // Get the CSRF token from cookies
            },
        });

        if (response.ok) {
            const result = await response.json(); // Assuming your Django API returns JSON
            console.log('Registration submitted successfully to backend:', result);
            return true; // Indicate success
        } else {
            const errorResponse = await response.json(); // Get error details from server
            console.error('Failed to submit registration:', response.status, errorResponse);
            return false; // Indicate failure
        }
    } catch (error) {
        console.error('Error sending registration to server:', error);
        return false; // Indicate failure due to network or other error
    }
}

// Helper function to retrieve Django's CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// --- Your Original Camera and Location Functions (Integrated) ---
// These functions are largely from your original code, adapted to use new hidden input IDs
// and the photoBlob variable.

// Initialize camera and location functionality
function initializeCameraAndLocation() {
    // Auto-request location on page load after a short delay
    setTimeout(() => {
        getCurrentLocation();
    }, 1000);

    // Get references to all camera and location related UI elements
    const startCameraBtn = document.getElementById('start-camera');
    const capturePhotoBtn = document.getElementById('capture-photo');
    const switchCameraBtn = document.getElementById('switch-camera');
    const retakePhotoBtn = document.getElementById('retake-photo');
    const confirmPhotoBtn = document.getElementById('confirm-photo');
    const changePhotoBtn = document.getElementById('change-photo');
    const getLocationBtn = document.getElementById('get-location');

    // Attach event listeners to buttons
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

    // Check available cameras once on load to configure UI (e.g., show/hide switch camera button)
    checkAvailableCameras();

    // Handle file input change for the fallback photo upload option
    const fileInput = document.querySelector('input[name="photo"]');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                photoBlob = file; // Store the uploaded File object as the primary photo Blob
                const reader = new FileReader();
                reader.onload = function(event) {
                    // Display the uploaded image in preview and final sections
                    document.getElementById('captured-image').src = event.target.result;
                    document.getElementById('final-image').src = event.target.result;
                    document.getElementById('captured_photo_hidden').value = event.target.result; // Update hidden input
                    // Adjust UI state to show the confirmed photo
                    document.getElementById('upload-fallback').style.display = 'none';
                    document.getElementById('camera-section').style.display = 'none';
                    document.getElementById('photo-preview').style.display = 'none';
                    document.getElementById('photo-confirmed').style.display = 'block';
                    document.getElementById('camera-status').innerHTML = '<p class="text-success"><i class="fas fa-check-circle me-2"></i>Photo uploaded successfully!</p>';
                };
                reader.readAsDataURL(file); // Read the file as a Data URL for display
            }
        });
    }
}

// Checks how many cameras are available and updates the UI accordingly (e.g., hides 'Switch Camera' if only one).
async function checkAvailableCameras() {
    try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        availableCameras = devices.filter(device => device.kind === 'videoinput'); // Filter for video input devices
        const switchBtn = document.getElementById('switch-camera');
        if (availableCameras.length <= 1) { // If 0 or 1 camera, hide the switch button
            if (switchBtn) {
                switchBtn.style.display = 'none';
            }
        } else { // If more than 1 camera, show the switch button
            if (switchBtn) {
                switchBtn.style.display = 'inline-block';
            }
        }
    } catch (error) {
        console.log('Could not enumerate devices:', error);
    }
}

// Starts the camera stream and displays it in the video element.
async function startCamera() {
    const video = document.getElementById('camera-stream');
    const startBtn = document.getElementById('start-camera');
    const captureBtn = document.getElementById('capture-photo');
    const switchBtn = document.getElementById('switch-camera');
    const statusDiv = document.getElementById('camera-status');
    const cameraInfo = document.getElementById('camera-info');
    const uploadFallback = document.getElementById('upload-fallback');

    try {
        // Define media constraints for optimal mobile camera usage
        const constraints = {
            video: {
                width: { ideal: 640 }, // Prefer 640p width
                height: { ideal: 480 }, // Prefer 480p height
                facingMode: currentFacingMode // Use 'environment' (back) or 'user' (front)
            }
        };

        statusDiv.innerHTML = '<div class="loading-spinner"></div>Starting camera...'; // Show loading spinner
        uploadFallback.style.display = 'none'; // Hide fallback upload option when camera is starting

        // Stop any existing camera stream before starting a new one
        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
        }

        cameraStream = await navigator.mediaDevices.getUserMedia(constraints); // Request camera access
        video.srcObject = cameraStream; // Assign stream to video element

        // Update UI: hide start button, show capture and switch buttons
        startBtn.style.display = 'none';
        captureBtn.style.display = 'inline-block';

        if (availableCameras.length > 1) {
            switchBtn.style.display = 'inline-block';
        }

        cameraInfo.style.display = 'block'; // Show camera info (which camera is active)
        updateCameraInfo(); // Update camera info text

        statusDiv.innerHTML = '<p class="text-info"><i class="fas fa-info-circle me-2"></i>Camera ready! Position yourself properly and click capture.</p>';

    } catch (error) {
        console.error('Camera error:', error); // Log camera errors

        let errorMessage = 'Camera access denied or not available.';
        if (error.name === 'NotAllowedError') {
            errorMessage = 'Camera permission denied. Please allow camera access and try again.';
        } else if (error.name === 'NotFoundError') {
            errorMessage = 'No camera found on this device.';
        } else if (error.name === 'NotReadableError') {
            errorMessage = 'Camera is being used by another application.';
        }

        statusDiv.innerHTML = `<p class="text-danger"><i class="fas fa-exclamation-triangle me-2"></i>${errorMessage}</p>`; // Display user-friendly error

        // If camera fails, show the fallback file upload option
        document.getElementById('upload-fallback').style.display = 'block';
        document.querySelector('input[name="photo"]').style.display = 'block'; // Ensure file input is visible
        // Hide camera-related buttons
        document.getElementById('start-camera').style.display = 'none';
        document.getElementById('capture-photo').style.display = 'none';
        document.getElementById('switch-camera').style.display = 'none';
    }
}

// Toggles between front and back camera (if available)
async function switchCamera() {
    currentFacingMode = currentFacingMode === 'user' ? 'environment' : 'user'; // Toggle facing mode
    await startCamera(); // Restart camera with the new facing mode
}

// Updates the displayed camera information (e.g., "Back Camera" or "Front Camera")
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

// Captures a photo from the video stream onto a canvas, then converts it to a Blob.
function capturePhoto() {
    const video = document.getElementById('camera-stream');
    const canvas = document.getElementById('photo-canvas');
    const cameraSection = document.getElementById('camera-section');
    const previewDiv = document.getElementById('photo-preview');
    const capturedImg = document.getElementById('captured-image');

    // Set canvas dimensions to match the video stream for accurate capture
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height); // Draw video frame onto canvas

    // Convert canvas content to a Blob (preferred for PWA)
    canvas.toBlob((blob) => {
        photoBlob = blob; // Store the Blob in the global variable
        capturedImg.src = URL.createObjectURL(photoBlob); // Create a temporary URL for displaying the Blob

        // Adjust UI: hide camera, show photo preview
        cameraSection.style.display = 'none';
        previewDiv.style.display = 'block';

        // Stop the camera stream to free up resources
        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
            cameraStream = null;
        }
    }, 'image/jpeg', 0.85); // Capture as JPEG with 85% quality
}

// Resets the photo capture process, allowing the user to retake a photo.
function retakePhoto() {
    const cameraSection = document.getElementById('camera-section');
    const previewDiv = document.getElementById('photo-preview');
    const confirmedDiv = document.getElementById('photo-confirmed');

    // Reset UI states
    cameraSection.style.display = 'block';
    previewDiv.style.display = 'none';
    confirmedDiv.style.display = 'none';
    document.getElementById('upload-fallback').style.display = 'none'; // Hide fallback if active

    // Revoke previous Blob URL to free up memory
    if (document.getElementById('captured-image').src && document.getElementById('captured-image').src.startsWith('blob:')) {
        URL.revokeObjectURL(document.getElementById('captured-image').src);
    }
    photoBlob = null; // Clear the stored photo Blob
    document.getElementById('captured_photo_hidden').value = ''; // Clear hidden input
    document.querySelector('input[name="photo"]').value = ''; // Clear the file input if used

    startCamera(); // Restart the camera for a new capture
}

// Confirms the captured/uploaded photo and transitions to the final confirmation state.
function confirmPhoto() {
    const previewDiv = document.getElementById('photo-preview');
    const confirmedDiv = document.getElementById('photo-confirmed');
    const finalImg = document.getElementById('final-image');
    const capturedPhotoInput = document.getElementById('captured_photo_hidden');

    if (photoBlob) {
        // If a Blob is available, convert it to a Data URL for the hidden input and final display
        const reader = new FileReader();
        reader.onloadend = () => {
            capturedPhotoInput.value = reader.result;
            finalImg.src = reader.result;
            // Adjust UI state
            previewDiv.style.display = 'none';
            confirmedDiv.style.display = 'block';
            document.getElementById('camera-status').innerHTML = '<p class="text-success"><i class="fas fa-check-circle me-2"></i>Photo captured and confirmed!</p>';
        };
        reader.readAsDataURL(photoBlob);
    } else if (document.querySelector('input[name="photo"]').files.length > 0) {
         // If photo was uploaded via fallback, use that file to set hidden input and final display
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
         // Fallback in case photoBlob is null and no file was uploaded (should be prevented by validation)
         finalImg.src = document.getElementById('captured-image').src; // Use current preview source
         previewDiv.style.display = 'none';
         confirmedDiv.style.display = 'block';
         document.getElementById('camera-status').innerHTML = '<p class="text-success"><i class="fas fa-check-circle me-2"></i>Photo confirmed!</p>';
    }
}

// Allows the user to re-initiate the photo capture process after confirmation.
function changePhoto() {
    retakePhoto();
}

// --- Location Functions ---

// Attempts to get the user's current geographical location.
function getCurrentLocation() {
    const locationBtn = document.getElementById('get-location');
    const locationInfo = document.getElementById('location-info');
    const locationError = document.getElementById('location-error');
    const coordinatesSpan = document.getElementById('location-coordinates');
    const accuracySpan = document.getElementById('location-accuracy');
    // Reference to the hidden input fields for location data
    const latitudeHidden = document.getElementById('latitude_hidden');
    const longitudeHidden = document.getElementById('longitude_hidden');
    const accuracyHidden = document.getElementById('location_accuracy_hidden');

    if (!navigator.geolocation) {
        showLocationError('Geolocation is not supported by this browser.');
        return;
    }

    locationBtn.innerHTML = '<div class="loading-spinner"></div>Getting location...'; // Show loading state
    locationBtn.disabled = true; // Disable button during request
    locationError.style.display = 'none'; // Hide any previous error message

    // Options for geolocation request
    const options = {
        enableHighAccuracy: true, // Request most accurate location
        timeout: 10000, // Timeout after 10 seconds
        maximumAge: 60000 // Accept a cached position if it's no older than 1 minute
    };

    navigator.geolocation.getCurrentPosition(
        function(position) {
            // Success callback: Location obtained
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            const accuracy = position.coords.accuracy;

            // Update hidden form fields with acquired data
            latitudeHidden.value = lat;
            longitudeHidden.value = lng;
            accuracyHidden.value = accuracy;

            // Display location info in the UI
            coordinatesSpan.textContent = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
            accuracySpan.textContent = `${accuracy.toFixed(0)}m`;

            locationInfo.style.display = 'block'; // Show success message
            locationError.style.display = 'none'; // Hide error if it was shown

            // Reset button to success state
            locationBtn.innerHTML = '<i class="fas fa-check me-2"></i>Location Captured';
            locationBtn.disabled = false;
            locationBtn.className = 'btn btn-success';
        },
        function(error) {
            // Error callback: Failed to get location
            let errorMessage = 'Unable to retrieve location.';
            // Provide specific error messages based on error code
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
            showLocationError(errorMessage); // Display the specific error message
        },
        options
    );
}

// Displays a detailed error message for location failures.
function showLocationError(message) {
    const locationBtn = document.getElementById('get-location');
    const locationError = document.getElementById('location-error');
    const locationInfo = document.getElementById('location-info');
    const errorMessageSpan = document.getElementById('location-error-message');

    errorMessageSpan.textContent = message;
    locationError.style.display = 'block'; // Show the error div
    locationInfo.style.display = 'none'; // Hide success div

    // Reset button to 'Try Again' state
    locationBtn.innerHTML = '<i class="fas fa-crosshairs me-2"></i>Try Again';
    locationBtn.disabled = false;
    locationBtn.className = 'btn btn-warning';
}

// --- Form Element Initialization and Dynamic Behavior ---

// Initializes dynamic behaviors of form elements (e.g., show/hide fields based on selections).
function initializeFormElements() {
    // Logic for 'can_refer_others' checkbox (Individual Labor form)
    const canReferCheckbox = document.querySelector('input[name="can_refer_others"]');
    const referralFields = document.getElementById('referral-fields'); // Assuming this div exists in category_forms.html

    if (canReferCheckbox && referralFields) {
        canReferCheckbox.addEventListener('change', function() {
            referralFields.style.display = this.checked ? 'block' : 'none';
        });
        // Set initial display based on pre-filled data
        if (canReferCheckbox.checked) {
            referralFields.style.display = 'block';
        }
    }

    // Logic for 'arrange_transport' select (Mukkadam form)
    const transportSelect = document.querySelector('select[name="arrange_transport"]');
    const transportOtherField = document.getElementById('transport-other-field'); // Assuming this div exists in category_forms.html

    if (transportSelect && transportOtherField) {
        transportSelect.addEventListener('change', function() {
            transportOtherField.style.display = this.value === 'other' ? 'block' : 'none';
        });
        // Set initial display based on pre-filled data
        if (transportSelect.value === 'other') {
            transportOtherField.style.display = 'block';
        }
    }

    // Auto-format phone numbers to add '+91' prefix
    document.querySelectorAll('input[type="text"]').forEach(input => {
        if (input.name.includes('mobile_number')) { // Apply only to mobile number fields
            input.addEventListener('input', function(e) {
                let value = e.target.value.replace(/[^\d+]/g, ''); // Remove non-numeric characters except '+'

                // Add '+91' prefix if it's not already there and looks like a bare Indian number
                if (value && !value.startsWith('+') && !value.startsWith('91') && value.length >= 10) {
                    value = '+91' + value;
                } else if (value.startsWith('91') && !value.startsWith('+91')) { // If it starts with '91' but no '+'
                    value = '+' + value;
                }

                e.target.value = value;
            });
        }
    });
}

// Handles the "Previous" button click, saves current step data, and navigates back.
async function goBack() {
    const currentStep = parseInt(document.querySelector('input[name="step"]').value);
    const form = document.getElementById('registrationForm');
    let currentRegistration = await getCurrentRegistrationData(); // Get the current draft
    let stepData = {}; // Data object for the current step (before going back)

    // Helper functions for getting field values (repeated here for self-containment if this was standalone,
    // but globally defined functions are better as in the main script structure above)
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

    // Collect data for the current step *before* navigating back
    // This ensures that if the user goes back and forth, data is preserved
    if (currentStep === 2) {
        const categoryFromStep1 = currentRegistration.step1 ? currentRegistration.step1.category : '';
        const currentCategory = document.getElementById('currentCategorySession').value || categoryFromStep1; // Determine category for step 2 fields

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
        currentRegistration.step2 = stepData; // Update the full draft
    } else if (currentStep === 3) {
         stepData = {
            data_sharing_agreement: getFieldValue('data_sharing_agreement')
        };
        currentRegistration.step3 = stepData; // Update the full draft
    }
    // No explicit data collection for step 1 when going back, as it's the first step

    await saveCurrentRegistrationData(currentRegistration); // Save the updated draft to IndexedDB
    window.location.href = `?step=${currentStep - 1}`; // Navigate back to the previous step
}

// Cleanup function: Ensures camera stream is stopped when the page is unloaded.
window.addEventListener('beforeunload', function() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop()); // Stop all tracks in the media stream
    }
});