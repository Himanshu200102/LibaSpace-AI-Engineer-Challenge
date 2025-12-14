/**
 * Standalone CAPTCHA handler utilities.
 * Can be injected into pages for CAPTCHA manipulation.
 */

window.CaptchaHandler = {
    /**
     * Inject reCAPTCHA v2 solution.
     */
    injectRecaptchaV2: function(solution) {
        const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
        if (textarea) {
            textarea.value = solution;
            const event = new Event('input', { bubbles: true });
            textarea.dispatchEvent(event);
            
            // Trigger callback if available
            if (window.grecaptcha) {
                try {
                    const widgetId = textarea.closest('.g-recaptcha')?.getAttribute('data-widget-id');
                    if (widgetId) {
                        window.grecaptcha.execute(parseInt(widgetId));
                    }
                } catch (e) {
                    console.warn('Could not trigger reCAPTCHA callback:', e);
                }
            }
            return true;
        }
        return false;
    },

    /**
     * Inject reCAPTCHA v3 solution.
     */
    injectRecaptchaV3: function(solution) {
        const input = document.querySelector('input[name="g-recaptcha-response"]') ||
                     document.querySelector('textarea[name="g-recaptcha-response"]');
        if (input) {
            input.value = solution;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            return true;
        }
        
        // Store globally for form submission
        window.recaptchaToken = solution;
        return true;
    },

    /**
     * Inject hCaptcha solution.
     */
    injectHcaptcha: function(solution) {
        const textarea = document.querySelector('textarea[name="h-captcha-response"]');
        if (textarea) {
            textarea.value = solution;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            
            // Trigger callback
            const container = textarea.closest('.h-captcha');
            if (container) {
                const callback = container.getAttribute('data-callback');
                if (callback && typeof window[callback] === 'function') {
                    window[callback](solution);
                }
            }
            return true;
        }
        return false;
    }
};

