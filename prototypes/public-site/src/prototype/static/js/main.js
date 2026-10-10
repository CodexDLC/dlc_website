document.addEventListener('DOMContentLoaded', () => {
    // 1. Animated Number Counters using Intersection Observer
    const statsSection = document.querySelector('.stats-grid');
    const counters = document.querySelectorAll('.stat-number');
    let hasAnimated = false;

    if (statsSection && counters.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && !hasAnimated) {
                hasAnimated = true;
                counters.forEach(counter => {
                    const target = parseInt(counter.getAttribute('data-target'));
                    const suffix = counter.getAttribute('data-suffix') || '';
                    const duration = 2000; // ms
                    const step = target / (duration / 16); // 60fps

                    let current = 0;
                    const updateCounter = () => {
                        current += step;
                        if (current < target) {
                            counter.innerText = Math.ceil(current) + suffix;
                            requestAnimationFrame(updateCounter);
                        } else {
                            counter.innerText = target + suffix;
                        }
                    };
                    updateCounter();
                });
            }
        }, { threshold: 0.5 });

        observer.observe(statsSection);
    }

    // 2. Simple Scroll Reveal Animation for generic elements
    const fadeElements = document.querySelectorAll('.fade-in-section');
    const fadeObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                // Optional: stop observing once it's visible
                // fadeObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    fadeElements.forEach(el => fadeObserver.observe(el));

    // 3. FAQ Accordion Logic
    const accordions = document.querySelectorAll('.accordion-header');
    accordions.forEach(acc => {
        acc.addEventListener('click', function () {
            const parent = this.parentElement;
            const content = this.nextElementSibling;

            // Close all others (optional, remove if you want multiple open at once)
            document.querySelectorAll('.accordion').forEach(other => {
                if (other !== parent && other.classList.contains('active')) {
                    other.classList.remove('active');
                    other.querySelector('.accordion-content').style.maxHeight = null;
                }
            });

            // Toggle current
            parent.classList.toggle('active');
            if (parent.classList.contains('active')) {
                content.style.maxHeight = content.scrollHeight + "px";
            } else {
                content.style.maxHeight = null;
            }
        });
    });
});
