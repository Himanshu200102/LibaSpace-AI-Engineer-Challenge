/**
 * Content script for CAPTCHA detection and solving.
 * Runs on all pages to detect and handle CAPTCHA challenges.
 */

(function() {
    'use strict';

    const BRIDGE_URL = 'http://127.0.0.1:8765';
    
    // CAPTCHA detection patterns
    const CAPTCHA_SELECTORS = {
        recaptcha_v2: [
            'iframe[src*="recaptcha/api2/anchor"]',
            'iframe[src*="recaptcha/api2/bframe"]',
            '.g-recaptcha',
            '[data-sitekey]'
        ],
        recaptcha_v3: [
            'script[src*="recaptcha/api.js"]',
            'script[src*="recaptcha/enterprise.js"]'
        ],
        hcaptcha: [
            'iframe[src*="hcaptcha.com"]',
            '.h-captcha',
            '[data-sitekey]'
        ]
    };

    /**
     * Detect CAPTCHA type and extract site key.
     */
    function detectCaptcha() {
        const pageUrl = window.location.href;
        let captchaType = null;
        let siteKey = null;

        // Check for reCAPTCHA v2
        const recaptchaV2Elements = document.querySelectorAll(CAPTCHA_SELECTORS.recaptcha_v2.join(','));
        if (recaptchaV2Elements.length > 0) {
            // Try to find site key
            const siteKeyElement = document.querySelector('[data-sitekey]');
            if (siteKeyElement) {
                siteKey = siteKeyElement.getAttribute('data-sitekey');
            }
            
            // Also check in iframes
            const iframes = document.querySelectorAll('iframe[src*="recaptcha"]');
            iframes.forEach(iframe => {
                try {
                    const src = iframe.src;
                    const match = src.match(/[&?]k=([^&]+)/);
                    if (match) {
                        siteKey = match[1];
                    }
                } catch (e) {
                    // Cross-origin iframe, skip
                }
            });

            if (siteKey) {
                captchaType = 'recaptcha_v2';
            }
        }

        // Check for reCAPTCHA v3
        if (!captchaType) {
            const recaptchaV3Scripts = document.querySelectorAll(CAPTCHA_SELECTORS.recaptcha_v3.join(','));
            if (recaptchaV3Scripts.length > 0) {
                // Extract site key from script src or grecaptcha object
                recaptchaV3Scripts.forEach(script => {
                    const src = script.src;
                    const match = src.match(/[&?]render=([^&]+)/);
                    if (match) {
                        siteKey = match[1];
                        captchaType = 'recaptcha_v3';
                    }
                });

                // Also check window.grecaptcha
                if (!siteKey && window.grecaptcha && window.grecaptcha.ready) {
                    // Try to get site key from grecaptcha
                    captchaType = 'recaptcha_v3';
                    // Site key might be in the script tag or data attribute
                    const scripts = document.querySelectorAll('script');
                    scripts.forEach(script => {
                        const match = script.src.match(/[&?]render=([^&]+)/);
                        if (match) {
                            siteKey = match[1];
                        }
                    });
                }
            }
        }

        // Check for hCaptcha
        if (!captchaType) {
            const hcaptchaElements = document.querySelectorAll(CAPTCHA_SELECTORS.hcaptcha.join(','));
            if (hcaptchaElements.length > 0) {
                const siteKeyElement = document.querySelector('[data-sitekey]');
                if (siteKeyElement) {
                    siteKey = siteKeyElement.getAttribute('data-sitekey');
                    captchaType = 'hcaptcha';
                }
            }
        }

        return { captchaType, siteKey, pageUrl };
    }

    /**
     * Solve CAPTCHA by calling bridge API.
     */
    async function solveCaptcha(captchaType, siteKey, pageUrl) {
        try {
            console.log(`[CAPTCHA Solver] Solving ${captchaType} with site key: ${siteKey.substring(0, 20)}...`);
            
            const response = await fetch(`${BRIDGE_URL}/solve`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    captcha_type: captchaType,
                    site_key: siteKey,
                    page_url: pageUrl
                })
            });

            const result = await response.json();
            
            if (result.success && result.solution) {
                console.log('[CAPTCHA Solver] Solution received!');
                return result.solution;
            } else {
                console.error('[CAPTCHA Solver] Failed to solve:', result.error);
                return null;
            }
        } catch (error) {
            console.error('[CAPTCHA Solver] Error:', error);
            return null;
        }
    }

    /**
     * Inject solution into reCAPTCHA v2.
     */
    function injectRecaptchaV2Solution(solution) {
        // Find the callback function name
        const callbackName = window.___grecaptcha_cfg?.clients?.[0]?.callback;
        
        if (callbackName && typeof window[callbackName] === 'function') {
            window[callbackName](solution);
            return true;
        }

        // Alternative: Find textarea and set value, then trigger callback
        const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
        if (textarea) {
            textarea.value = solution;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            textarea.dispatchEvent(new Event('change', { bubbles: true }));
            
            // Trigger callback if available
            if (window.grecaptcha && window.grecaptcha.getResponse) {
                // Force update
                const widgetId = textarea.closest('.g-recaptcha')?.getAttribute('data-widget-id');
                if (widgetId) {
                    window.grecaptcha.execute();
                }
            }
            return true;
        }

        return false;
    }

    /**
     * Inject solution into reCAPTCHA v3.
     */
    function injectRecaptchaV3Solution(solution) {
        // reCAPTCHA v3 uses tokens differently
        // Usually set in a hidden field or sent directly in form submission
        const tokenInput = document.querySelector('input[name="g-recaptcha-response"]') ||
                          document.querySelector('textarea[name="g-recaptcha-response"]');
        
        if (tokenInput) {
            tokenInput.value = solution;
            tokenInput.dispatchEvent(new Event('input', { bubbles: true }));
            tokenInput.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }

        // Store in window for form submission
        window.recaptchaToken = solution;
        return true;
    }

    /**
     * Inject solution into hCaptcha.
     */
    function injectHcaptchaSolution(solution) {
        // Find hCaptcha response textarea
        const textarea = document.querySelector('textarea[name="h-captcha-response"]');
        if (textarea) {
            textarea.value = solution;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            textarea.dispatchEvent(new Event('change', { bubbles: true }));
            
            // Trigger hCaptcha callback
            const callback = textarea.closest('.h-captcha')?.getAttribute('data-callback');
            if (callback && typeof window[callback] === 'function') {
                window[callback](solution);
            }
            return true;
        }

        return false;
    }

    /**
     * Inject CAPTCHA solution into the page.
     */
    function injectSolution(captchaType, solution) {
        console.log(`[CAPTCHA Solver] Injecting solution for ${captchaType}`);
        
        switch (captchaType) {
            case 'recaptcha_v2':
                return injectRecaptchaV2Solution(solution);
            case 'recaptcha_v3':
                return injectRecaptchaV3Solution(solution);
            case 'hcaptcha':
                return injectHcaptchaSolution(solution);
            default:
                console.error(`[CAPTCHA Solver] Unknown CAPTCHA type: ${captchaType}`);
                return false;
        }
    }

    /**
     * Main handler: detect and solve CAPTCHA.
     */
    async function handleCaptcha() {
        // Wait a bit for page to load
        if (document.readyState !== 'complete') {
            await new Promise(resolve => {
                if (document.readyState === 'complete') {
                    resolve();
                } else {
                    window.addEventListener('load', resolve);
                }
            });
        }

        // Small delay to ensure CAPTCHA widgets are loaded
        await new Promise(resolve => setTimeout(resolve, 1000));

        const detection = detectCaptcha();
        
        if (detection.captchaType && detection.siteKey) {
            console.log(`[CAPTCHA Solver] Detected ${detection.captchaType}`);
            
            // Listen for messages from background script
            chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
                if (request.action === 'solveCaptcha') {
                    solveCaptcha(detection.captchaType, detection.siteKey, detection.pageUrl)
                        .then(solution => {
                            if (solution) {
                                const injected = injectSolution(detection.captchaType, solution);
                                sendResponse({ success: injected, solution: solution });
                            } else {
                                sendResponse({ success: false, error: 'Failed to solve CAPTCHA' });
                            }
                        })
                        .catch(error => {
                            sendResponse({ success: false, error: error.message });
                        });
                    return true; // Async response
                } else if (request.action === 'injectSolution') {
                    const injected = injectSolution(detection.captchaType, request.solution);
                    sendResponse({ success: injected });
                }
            });

            // Store detection info for later use
            window.__captchaDetection = detection;
        }
    }

    // Start handling
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', handleCaptcha);
    } else {
        handleCaptcha();
    }
})();

