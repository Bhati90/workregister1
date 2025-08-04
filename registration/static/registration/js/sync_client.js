// Add this to your multi_step_form_client.js or create a separate sync.js file

// Make functions globally available by attaching to window
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

// Function to get count of pending registrations
async function getPendingRegistrationsCount() {
    if (!('indexedDB' in window)) return 0;
    
    try {
        const { openDB } = await import('https://cdn.jsdelivr.net/npm/idb@7/+esm');
        const db = await openDB('LaborRegistrationDB', 2);
        const tx = db.transaction('pending_registrations', 'readonly');
        const store = tx.objectStore('pending_registrations');
        const count = await store.count();
        await tx.done;
        return count;
    } catch (error) {
        console.error('[Client] Failed to get pending count:', error);
        return 0;
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