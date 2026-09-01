/**
 * Qrious Tech Academy - Clean & Elegant Soft 3D Ambient Engine
 * Provides a subtle, non-intrusive 3D particle depth field and gentle glass card tilt,
 * ensuring 100% clean typography and zero visual obstruction.
 */

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', initCleanSoft3D);

    function initCleanSoft3D() {
        const canvas = document.getElementById('canvas3d');
        if (!canvas) return;

        if (typeof THREE === 'undefined') {
            return;
        }

        // --- 1. RENDERER & SCENE SETUP ---
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.z = 30;

        const renderer = new THREE.WebGLRenderer({
            canvas: canvas,
            alpha: true,
            antialias: true,
            powerPreference: 'high-performance'
        });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

        // --- 2. SOFT 3D FLOATING PARTICLES CONSTELLATION ---
        const particleCount = 200;
        const particleGeo = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const scales = new Float32Array(particleCount);

        for (let i = 0; i < particleCount; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 70;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 50;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 40 - 10;

            scales[i] = 0.5 + Math.random() * 0.8;
        }

        particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        // Create Soft Particle Radial Texture
        const createSoftDotTexture = () => {
            const pCanvas = document.createElement('canvas');
            pCanvas.width = 32;
            pCanvas.height = 32;
            const ctx = pCanvas.getContext('2d');
            const grad = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
            grad.addColorStop(0, 'rgba(212, 255, 0, 0.85)');
            grad.addColorStop(0.4, 'rgba(56, 189, 248, 0.35)');
            grad.addColorStop(1, 'rgba(212, 255, 0, 0)');
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(16, 16, 16, 0, Math.PI * 2);
            ctx.fill();
            return new THREE.CanvasTexture(pCanvas);
        };

        const particleMat = new THREE.PointsMaterial({
            size: 0.6,
            map: createSoftDotTexture(),
            transparent: true,
            opacity: 0.35,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        const particleSystem = new THREE.Points(particleGeo, particleMat);
        scene.add(particleSystem);

        // --- 3. SUBTLE DISTANT HORIZON MESH (LOW IN BACKGROUND) ---
        const horizonGeo = new THREE.PlaneGeometry(100, 30, 40, 15);
        const horizonMat = new THREE.MeshBasicMaterial({
            color: 0x111827,
            wireframe: true,
            transparent: true,
            opacity: 0.03
        });
        const horizonMesh = new THREE.Mesh(horizonGeo, horizonMat);
        horizonMesh.rotation.x = -Math.PI * 0.45;
        horizonMesh.position.set(0, -22, -25);
        scene.add(horizonMesh);

        // --- 4. MOUSE PARALLAX & SCROLL LISTENERS ---
        let mouseX = 0;
        let mouseY = 0;
        let targetMouseX = 0;
        let targetMouseY = 0;
        let scrollY = 0;

        window.addEventListener('mousemove', (e) => {
            targetMouseX = (e.clientX / window.innerWidth - 0.5) * 2;
            targetMouseY = (e.clientY / window.innerHeight - 0.5) * 2;
        });

        window.addEventListener('scroll', () => {
            scrollY = window.scrollY;
        });

        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });

        // --- 5. ANIMATION LOOP ---
        const clock = new THREE.Clock();

        function animate() {
            requestAnimationFrame(animate);

            const elapsedTime = clock.getElapsedTime();

            // Smooth Camera Parallax
            mouseX += (targetMouseX - mouseX) * 0.03;
            mouseY += (targetMouseY - mouseY) * 0.03;

            camera.position.x = mouseX * 1.5;
            camera.position.y = -mouseY * 1.5 + (scrollY * 0.001);
            camera.lookAt(0, 0, 0);

            // Rotate Particles Constellation
            particleSystem.rotation.y = elapsedTime * 0.02;
            particleSystem.rotation.x = elapsedTime * 0.01;

            // Animate Distant Horizon Mesh Waves
            const hPos = horizonGeo.attributes.position;
            for (let i = 0; i < hPos.count; i++) {
                const x = hPos.getX(i);
                const y = hPos.getY(i);
                hPos.setZ(i, Math.sin(elapsedTime * 1.5 + x * 0.2 + y * 0.2) * 0.5);
            }
            hPos.needsUpdate = true;

            renderer.render(scene, camera);
        }

        animate();

        // --- 6. SUBTLE CARD 3D HOVER TILT ---
        initSubtleCard3DTilt();

        // --- 7. CONTINUOUS UP & DOWN SCROLL MOTION ENGINE ---
        initScrollMotionObserver();
    }

    function initSubtleCard3DTilt() {
        const cards = document.querySelectorAll(
            '.mock-card, .process-item-card, .testimonial-card-plain, ' +
            '.testimonial-card-lime, .auth-card, .service-card, .feature-card, .course-card'
        );

        cards.forEach((card) => {
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                const centerX = rect.width / 2;
                const centerY = rect.height / 2;

                const rotateX = -((y - centerY) / centerY) * 3; // Max 3 deg
                const rotateY = ((x - centerX) / centerX) * 3;   // Max 3 deg

                card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-2px)`;
                card.style.transition = 'transform 0.1s ease-out';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)';
                card.style.transition = 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
            });
        });
    }

    // Continuous Up & Down Scroll Motion Engine
    function initScrollMotionObserver() {
        if (!('IntersectionObserver' in window)) return;

        const observerOptions = {
            root: null,
            rootMargin: '0px 0px -40px 0px',
            threshold: 0.1
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                } else {
                    // Allows continuous reveal animation on both upward and downward scrolling
                    if (entry.boundingClientRect.top > 0) {
                        entry.target.classList.remove('is-visible');
                    }
                }
            });
        }, observerOptions);

        // Select all section blocks, headers, cards, and images across all pages
        const revealTargets = document.querySelectorAll(
            '.mock-section, .hero-heading, .hero-subtext, .hero-arch-stage, ' +
            '.mock-card, .process-item-card, .process-img-card, .testimonial-card-plain, ' +
            '.testimonial-card-lime, .cta-banner-stage, .auth-card, .service-card, ' +
            '.feature-card, .course-card, .section-headline, .section-subtitle, ' +
            '.reviews-header, .reviews-section, .footer-inner, .scroll-reveal'
        );

        revealTargets.forEach((el, idx) => {
            if (!el.classList.contains('scroll-reveal')) {
                el.classList.add('scroll-reveal');
            }
            // Add subtle staggered transition delay for siblings in grids
            const parentGrid = el.closest('.grid-cards-6, .grid-process, .grid-testimonials, .form-row');
            if (parentGrid) {
                const siblings = Array.from(parentGrid.children);
                const itemIndex = siblings.indexOf(el);
                if (itemIndex > 0) {
                    el.style.transitionDelay = `${(itemIndex % 4) * 0.1}s`;
                }
            }
            observer.observe(el);
        });
    }

})();
