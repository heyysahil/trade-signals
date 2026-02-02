// Main JavaScript for sendsignals application

// Initialize Lucide icons
(function() {
    'use strict';
    
    function initLucide() {
        if (typeof lucide !== 'undefined' && lucide.createIcons) {
            lucide.createIcons();
        }
    }
    
    // Sticky header scroll effect
    function initStickyHeader() {
        const header = document.querySelector('.header');
        if (!header) return;
        
        let lastScroll = 0;
        window.addEventListener('scroll', function() {
            const currentScroll = window.pageYOffset;
            if (currentScroll > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
            lastScroll = currentScroll;
        });
    }
    
    // Enhanced scroll reveal for all fade-in elements
    function initEnhancedScrollReveal() {
        const elements = document.querySelectorAll('.fade-in-on-scroll, .page-header, .summary-card, .service-card, .product-card, .contact-item, .feature-item');
        if (!elements.length) return;
        
        const observer = new IntersectionObserver(
            function(entries) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
        );
        
        elements.forEach(function(el) {
            observer.observe(el);
        });
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initLucide();
            initStickyHeader();
            initEnhancedScrollReveal();
        });
    } else {
        initLucide();
        initStickyHeader();
        initEnhancedScrollReveal();
    }
})();
