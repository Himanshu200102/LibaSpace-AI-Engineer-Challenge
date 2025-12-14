/**
 * Background service worker for CAPTCHA solver extension.
 * Handles communication between content scripts and bridge API.
 */

const BRIDGE_URL = 'http://127.0.0.1:8765';

/**
 * Check if bridge server is available.
 */
async function checkBridgeHealth() {
    try {
        const response = await fetch(`${BRIDGE_URL}/health`, {
            method: 'GET',
            timeout: 3000
        });
        return response.ok;
    } catch (error) {
        console.error('[Background] Bridge server not available:', error);
        return false;
    }
}

/**
 * Handle messages from content scripts.
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'solveCaptcha') {
        // Forward to content script to handle
        chrome.tabs.sendMessage(sender.tab.id, {
            action: 'solveCaptcha',
            captchaType: request.captchaType,
            siteKey: request.siteKey,
            pageUrl: request.pageUrl
        }, (response) => {
            sendResponse(response);
        });
        return true; // Async response
    }
    
    return false;
});

/**
 * Listen for tab updates to check for CAPTCHA on form pages.
 */
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        // Check if it's a job application page
        const jobSites = ['lever.co', 'greenhouse.io', 'workday.com', 'glassdoor.com'];
        const isJobSite = jobSites.some(site => tab.url.includes(site));
        
        if (isJobSite) {
            // Inject content script if needed
            chrome.scripting.executeScript({
                target: { tabId: tabId },
                files: ['content/content-script.js']
            }).catch(() => {
                // Script might already be injected
            });
        }
    }
});

// Check bridge health on startup
checkBridgeHealth().then(isHealthy => {
    if (!isHealthy) {
        console.warn('[Background] Bridge server is not available. CAPTCHA solving will not work.');
    }
});

