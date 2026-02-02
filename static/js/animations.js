/**
 * SendSignals – Scroll & heading animations
 * Keeps existing behaviour; adds 3D tilt, word-reveal, and scroll observers.
 */
(function () {
    'use strict';

    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function runWhenReady(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    /** Intersection observer for .visible class */
    function initScrollReveal() {
        var blocks = document.querySelectorAll('.fade-in-on-scroll, .stagger-children, .section-title-animated, .stat-card-animate, .trust-badge-animate');
        if (!blocks.length) return;

        var observer = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
        );

        blocks.forEach(function (el) {
            observer.observe(el);
        });
    }

    /** Wrap hero heading words for .heading-reveal */
    function initHeadingReveal() {
        var hero = document.querySelector('.hero-heading-reveal');
        if (!hero || reducedMotion) return;

        var text = hero.innerHTML;
        if (!text.trim()) return;

        // Support simple HTML like <span>highlight</span> by keeping tags, splitting the rest by words
        var temp = document.createElement('div');
        temp.innerHTML = text;
        var walk = document.createTreeWalker(temp, NodeFilter.SHOW_TEXT);
        var parts = [];
        while (walk.nextNode()) {
            var words = walk.currentNode.textContent.trim().split(/\s+/).filter(Boolean);
            words.forEach(function (w) {
                parts.push({ type: 'word', value: w });
            });
        }

        var lineHtml = '<span class="line">';
        parts.forEach(function (p) {
            if (p.type === 'word') {
                lineHtml += '<span class="word">' + escapeHtml(p.value) + '</span> ';
            }
        });
        lineHtml += '</span>';
        hero.innerHTML = lineHtml;
        hero.classList.add('heading-reveal');

        // Mark visible when in view (hero is usually in view on load)
        var ob = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (e) {
                    if (e.isIntersecting) e.target.classList.add('visible');
                });
            },
            { threshold: 0.2 }
        );
        ob.observe(hero);
    }

    function escapeHtml(s) {
        var div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }

    /** Optional: title letters for short section titles */
    function initTitleLetters() {
        var els = document.querySelectorAll('.title-letters');
        if (!els.length || reducedMotion) return;

        els.forEach(function (el) {
            var text = el.textContent;
            el.textContent = '';
            el.classList.add('title-letters');
            for (var i = 0; i < text.length; i++) {
                var c = text[i];
                var span = document.createElement('span');
                span.className = 'char';
                span.textContent = c === ' ' ? '\u00A0' : c;
                el.appendChild(span);
            }

            var ob = new IntersectionObserver(
                function (entries) {
                    entries.forEach(function (e) {
                        if (e.isIntersecting) {
                            e.target.classList.add('visible');
                        }
                    });
                },
                { threshold: 0.3 }
            );
            ob.observe(el);
        });
    }

    /** 3D tilt on mouse move for .card-3d inside .card-3d-wrapper */
    function initCardTilt() {
        if (reducedMotion) return;
        var wrappers = document.querySelectorAll('.card-3d-wrapper');
        wrappers.forEach(function (wrap) {
            var card = wrap.querySelector('.card-3d');
            if (!card) return;

            wrap.addEventListener('mousemove', function (e) {
                var rect = wrap.getBoundingClientRect();
                var x = (e.clientX - rect.left) / rect.width;
                var y = (e.clientY - rect.top) / rect.height;
                var rx = (y - 0.5) * -12;
                var ry = (x - 0.5) * 12;
                card.style.transform = 'rotateX(' + rx + 'deg) rotateY(' + ry + 'deg) translateZ(12px)';
            });
            wrap.addEventListener('mouseleave', function () {
                card.style.transform = '';
            });
        });
    }

    runWhenReady(function () {
        initScrollReveal();
        initHeadingReveal();
        initTitleLetters();
        initCardTilt();
    });
})();
