/* ═══════════════════════════════════════════════════════════════
   animations.js — All loading and animation effects
   Floating particles, gradient mesh, upload drag animations,
   skeleton shimmer, staggered reveal, page load, scroll header,
   error shake, and card flip transitions.
   ═══════════════════════════════════════════════════════════════ */

/**
 * Generates 50 floating particles and appends them to the container.
 * Each particle gets randomized size, position, and drift animation.
 *
 * @param {HTMLElement} container — The #particles-container element
 * @param {number} [count=50]    — Number of particles to generate
 */
export function generateParticles(container, count = 50) {
  if (!container) return;

  // Check for reduced motion preference
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return;
  }

  container.innerHTML = '';

  for (let i = 0; i < count; i++) {
    const particle = document.createElement('div');
    particle.className = 'particle';

    // Random size: 1-2px
    const size = 1 + Math.random();
    particle.style.width = `${size}px`;
    particle.style.height = `${size}px`;

    // Random position
    particle.style.left = `${Math.random() * 100}%`;
    particle.style.top = `${Math.random() * 100}%`;

    // Random drift values for CSS animation
    const driftRange = 80;
    particle.style.setProperty('--drift-x1', `${(Math.random() - 0.5) * driftRange}px`);
    particle.style.setProperty('--drift-y1', `${(Math.random() - 0.5) * driftRange}px`);
    particle.style.setProperty('--drift-x2', `${(Math.random() - 0.5) * driftRange}px`);
    particle.style.setProperty('--drift-y2', `${(Math.random() - 0.5) * driftRange}px`);
    particle.style.setProperty('--drift-x3', `${(Math.random() - 0.5) * driftRange}px`);
    particle.style.setProperty('--drift-y3', `${(Math.random() - 0.5) * driftRange}px`);

    // Random animation duration and delay
    const duration = 15 + Math.random() * 25; // 15-40s
    const delay = Math.random() * -30; // negative delay for staggered start
    particle.style.animation = `particleDrift ${duration}s ease-in-out ${delay}s infinite`;

    // Random opacity variation (around 0.08)
    particle.style.opacity = (0.04 + Math.random() * 0.08).toFixed(3);

    container.appendChild(particle);
  }
}

/**
 * Initializes the gradient mesh animation.
 * The CSS animations are already defined in style.css; this function
 * can be used to dynamically adjust blob properties if needed.
 *
 * @param {HTMLElement} meshContainer — The #gradient-mesh element
 */
export function initGradientMesh(meshContainer) {
  if (!meshContainer) return;

  // Check reduced motion
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const blobs = meshContainer.querySelectorAll('.mesh-blob');
    blobs.forEach((blob) => {
      blob.style.animation = 'none';
    });
  }
}

/**
 * Sets up scroll-based header opacity increase.
 * As the user scrolls, the header background becomes more opaque.
 *
 * @param {HTMLElement} header — The #app-header element
 */
export function initScrollHeaderOpacity(header) {
  if (!header) return;

  let ticking = false;

  function onScroll() {
    if (!ticking) {
      requestAnimationFrame(() => {
        const scrollY = window.scrollY;
        const maxScroll = 200;
        const progress = Math.min(scrollY / maxScroll, 1);

        // Increase background opacity from 0.04 → 0.12
        const bgOpacity = 0.04 + progress * 0.08;
        header.style.background = `rgba(255, 255, 255, ${bgOpacity})`;

        // Increase shadow intensity
        const shadowAlpha = 0.4 + progress * 0.2;
        header.style.boxShadow = `0 4px 24px rgba(0, 0, 0, ${shadowAlpha}), inset 0 1px 0 rgba(255, 255, 255, 0.05)`;

        ticking = false;
      });
      ticking = true;
    }
  }

  window.addEventListener('scroll', onScroll, { passive: true });
}

/**
 * Applies a staggered fade-in animation to all child elements of a container.
 *
 * @param {HTMLElement} container — Parent element
 * @param {string} [selector='> *'] — CSS selector for children to animate
 * @param {number} [delay=0.1]   — Delay between each element (seconds)
 */
export function staggeredFadeIn(container, selector = ':scope > *', delay = 0.1) {
  if (!container) return;

  const elements = container.querySelectorAll(selector);
  elements.forEach((el, index) => {
    el.classList.add('stagger-load');
    el.style.animationDelay = `${index * delay}s`;
  });
}

/**
 * Applies the page load staggered fade-in to major sections.
 */
export function pageLoadAnimation() {
  // Wait a small tick to ensure DOM is ready
  requestAnimationFrame(() => {
    const sections = document.querySelectorAll(
      '#app-header, #upload-section, #quadrants-section, #captions-section, #export-section'
    );

    sections.forEach((section, index) => {
      if (!section.classList.contains('quadrants-section--hidden') &&
          !section.classList.contains('captions-section--hidden') &&
          !section.classList.contains('export-section--hidden')) {
        section.style.opacity = '0';
        section.style.transform = 'translateY(20px)';
        section.style.transition = `opacity 0.5s cubic-bezier(0.4, 0, 0.2, 1) ${index * 0.1}s, transform 0.5s cubic-bezier(0.4, 0, 0.2, 1) ${index * 0.1}s`;

        requestAnimationFrame(() => {
          section.style.opacity = '1';
          section.style.transform = 'translateY(0)';
        });
      }
    });
  });
}

/**
 * Triggers the error shake animation on an element.
 *
 * @param {HTMLElement} element — The element to shake
 * @param {boolean} [addGlow=true] — Whether to add the red glow effect
 */
export function triggerShake(element, addGlow = true) {
  if (!element) return;

  element.classList.add('shake');
  if (addGlow) {
    element.classList.add('error-glow');
  }

  element.addEventListener('animationend', () => {
    element.classList.remove('shake');
    if (addGlow) {
      setTimeout(() => {
        element.classList.remove('error-glow');
      }, 1500);
    }
  }, { once: true });
}

/**
 * Creates a card flip transition effect.
 * Wraps an element in a flip container and triggers the flip.
 *
 * @param {HTMLElement} element     — The element to flip
 * @param {HTMLElement} backContent — Content to show on the back
 * @returns {Object}               — { flip, unflip }
 */
export function createCardFlip(element, backContent) {
  if (!element) return { flip: () => {}, unflip: () => {} };

  const parent = element.parentNode;
  const wrapper = document.createElement('div');
  wrapper.className = 'card-flip-wrapper';

  const flipInner = document.createElement('div');
  flipInner.className = 'card-flip';

  // Front
  element.classList.add('card-flip__front');
  flipInner.appendChild(element);

  // Back
  backContent.classList.add('card-flip__back');
  flipInner.appendChild(backContent);

  wrapper.appendChild(flipInner);
  parent.appendChild(wrapper);

  return {
    flip: () => flipInner.classList.add('card-flip--flipped'),
    unflip: () => flipInner.classList.remove('card-flip--flipped'),
  };
}

/**
 * Animates the staggered reveal of quadrant and caption cards.
 * Call this when videos/captions are loaded to reveal them with stagger.
 *
 * @param {string} gridSelector — CSS selector for the grid container
 */
export function revealCards(gridSelector) {
  const grid = document.querySelector(gridSelector);
  if (!grid) return;

  const cards = grid.children;
  Array.from(cards).forEach((card, index) => {
    card.classList.remove('reveal-card');
    // Force reflow
    void card.offsetWidth;
    card.classList.add('reveal-card');
    card.style.animationDelay = `${index * 0.15}s`;
  });
}

/**
 * Shows the skeleton loading state in a container.
 *
 * @param {HTMLElement} container — Target container (e.g., #captions-grid)
 * @param {number} [count=4]     — Number of skeleton cards
 */
export function showSkeletonLoader(container, count = 4) {
  if (!container) return;
  container.innerHTML = '';

  for (let i = 0; i < count; i++) {
    const skel = document.createElement('div');
    skel.className = 'skeleton-card reveal-card';
    skel.style.animationDelay = `${i * 0.15}s`;
    skel.innerHTML = `
      <div class="skeleton-line skeleton-line--full"></div>
      <div class="skeleton-line skeleton-line--medium"></div>
      <div class="skeleton-line skeleton-line--short"></div>`;
    container.appendChild(skel);
  }
}

/**
 * Hides skeleton loader and clears the container.
 *
 * @param {HTMLElement} container
 */
export function hideSkeletonLoader(container) {
  if (!container) return;
  container.innerHTML = '';
}

/**
 * Initializes all animation systems on page load.
 * Call this from main.js during app initialization.
 */
export function initAllAnimations() {
  const particlesContainer = document.getElementById('particles-container');
  const meshContainer = document.getElementById('gradient-mesh');
  const header = document.getElementById('app-header');

  generateParticles(particlesContainer, 50);
  initGradientMesh(meshContainer);
  initScrollHeaderOpacity(header);
  pageLoadAnimation();
}
