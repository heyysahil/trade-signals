/**
 * Admin Dashboard Initialization & Interaction Fix
 * Ensures UI is fully interactive after login
 */

(function() {
    'use strict';
    
    /**
     * CRITICAL: Fail-safe cleanup on admin dashboard load
     * Removes any blocking overlays, loaders, or disabled states
     */
    function forceEnableInteractions() {
        // Remove any overlays, loaders, backdrops
        const blockingElements = document.querySelectorAll('.overlay, .loader, .backdrop, .loading-overlay, .modal-backdrop');
        blockingElements.forEach(el => el.remove());
        
        // Reset body styles to ensure interactions work
        document.body.style.pointerEvents = 'auto';
        document.body.style.overflow = 'auto';
        document.body.style.opacity = '1';
        
        // Remove any classes that might block interaction
        document.body.classList.remove('loading', 'no-scroll', 'modal-open', 'disabled');
        
        // Ensure main content is interactive
        const main = document.querySelector('main');
        if (main) {
            main.style.pointerEvents = 'auto';
            main.style.opacity = '1';
        }
    }
    
    /**
     * Fix fade-in-on-scroll elements that are stuck
     * Immediately show all admin dashboard elements
     */
    function fixStuckAnimations() {
        const fadeElements = document.querySelectorAll('.fade-in-on-scroll, .admin-page-header, .admin-summary-card, .admin-table-section');
        
        fadeElements.forEach(el => {
            // Force add visible class
            el.classList.add('visible');
            // Override any stuck animation state
            el.style.opacity = '1';
            el.style.transform = 'none';
            el.style.pointerEvents = 'auto';
        });
    }
    
    /**
     * Enhanced scroll reveal for admin with immediate activation
     */
    function initAdminScrollReveal() {
        const elements = document.querySelectorAll('.fade-in-on-scroll');
        if (!elements.length) return;
        
        // Create observer with very aggressive settings
        const observer = new IntersectionObserver(
            function(entries) {
                entries.forEach(function(entry) {
                    // Immediately mark as visible if anywhere near viewport
                    if (entry.isIntersecting || entry.boundingClientRect.top < window.innerHeight) {
                        entry.target.classList.add('visible');
                        observer.unobserve(entry.target);
                    }
                });
            },
            { 
                threshold: 0, 
                rootMargin: '200px 0px 200px 0px' // Very generous margins
            }
        );
        
        elements.forEach(function(el) {
            // Immediately mark visible if already in view
            const rect = el.getBoundingClientRect();
            if (rect.top < window.innerHeight && rect.bottom > 0) {
                el.classList.add('visible');
            } else {
                observer.observe(el);
            }
        });
    }
    
    /**
     * Initialize Lucide icons
     */
    function initLucide() {
        if (typeof lucide !== 'undefined' && lucide.createIcons) {
            lucide.createIcons();
        }
    }
    
    /**
     * Main initialization
     */
    function init() {
        // CRITICAL: Force enable interactions first
        forceEnableInteractions();
        
        // Fix any stuck animations
        fixStuckAnimations();
        
        // Initialize scroll reveal
        initAdminScrollReveal();
        
        // Initialize icons
        initLucide();
        
        console.log('✅ Admin dashboard interactions enabled');
    }
    
    // Run immediately if DOM is ready, otherwise wait
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Additional safety: run again after a short delay
    setTimeout(function() {
        forceEnableInteractions();
        fixStuckAnimations();
    }, 100);
    
})();
