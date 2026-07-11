/* ═══════════════════════════════════════════════════════════════
   ProcessingModal.js — AI Processing animation modal
   Central glass card with animated neural network SVG,
   6-step progress timeline with unique animations per step,
   confetti on completion.
   ═══════════════════════════════════════════════════════════════ */

/**
 * Processing steps configuration.
 */
const STEPS = [
  { id: 'step-frames',     label: 'Extracting video frames…',          animType: 'orbiting-dots' },
  { id: 'step-audio',      label: 'Analyzing audio stream…',           animType: 'waveform' },
  { id: 'step-transcribe', label: 'Transcribing speech…',              animType: 'typing' },
  { id: 'step-captions',   label: 'Generating captions (4 styles)…',   animType: 'style-dots' },
  { id: 'step-burn',       label: 'Burning subtitles into videos…',    animType: 'progress-bar' },
  { id: 'step-ready',      label: 'Ready! 🎉',                          animType: 'ready' },
];

/**
 * Creates the processing modal content inside the given container.
 *
 * @param {HTMLElement} container — The #processing-modal-card element
 * @returns {Object}             — Control methods: { show, hide, updateStep, reset }
 */
export function createProcessingModal(container) {
  container.innerHTML = '';

  // ── Radial glow ──
  const glow = document.createElement('div');
  glow.className = 'processing-modal__glow';
  container.appendChild(glow);

  // ── Neural network SVG ──
  const svgWrap = document.createElement('div');
  svgWrap.className = 'processing-modal__svg-wrap';
  svgWrap.innerHTML = createNeuralNetworkSVG();
  container.appendChild(svgWrap);

  // ── Title ──
  const title = document.createElement('h2');
  title.className = 'processing-modal__title';
  title.textContent = 'Processing Your Video';
  container.appendChild(title);

  // ── Subtitle ──
  const subtitle = document.createElement('p');
  subtitle.className = 'processing-modal__subtitle';
  subtitle.textContent = 'AI is analyzing and generating captions…';
  container.appendChild(subtitle);

  // ── Progress timeline ──
  const timeline = document.createElement('div');
  timeline.className = 'progress-timeline';
  timeline.id = 'progress-timeline';

  STEPS.forEach((step, index) => {
    const stepEl = document.createElement('div');
    stepEl.className = 'progress-step';
    stepEl.id = step.id;
    stepEl.setAttribute('data-step-index', index);

    // Indicator
    const indicator = document.createElement('div');
    indicator.className = 'step-indicator step-indicator--pending';
    indicator.id = `${step.id}-indicator`;
    // Ring ripple child (used when active)
    const ring = document.createElement('div');
    ring.className = 'step-ring';
    ring.style.display = 'none';
    indicator.appendChild(ring);
    stepEl.appendChild(indicator);

    // Label
    const label = document.createElement('span');
    label.className = 'step-label';
    label.textContent = step.label;
    stepEl.appendChild(label);

    // Animation container
    const animContainer = document.createElement('div');
    animContainer.className = 'step-anim';
    animContainer.id = `${step.id}-anim`;
    animContainer.style.display = 'none';
    animContainer.innerHTML = createStepAnimation(step.animType);
    stepEl.appendChild(animContainer);

    timeline.appendChild(stepEl);
  });

  container.appendChild(timeline);

  // ── Confetti container (for step 6) ──
  const confettiContainer = document.createElement('div');
  confettiContainer.className = 'confetti-container';
  confettiContainer.id = 'confetti-container';
  confettiContainer.style.display = 'none';
  container.appendChild(confettiContainer);

  // ── Control methods ──

  let currentStep = -1;

  function show() {
    const modal = document.getElementById('processing-modal');
    if (modal) modal.classList.remove('modal-backdrop--hidden');
  }

  function hide() {
    const modal = document.getElementById('processing-modal');
    if (modal) modal.classList.add('modal-backdrop--hidden');
  }

  function reset() {
    currentStep = -1;
    STEPS.forEach((step) => {
      const stepEl = document.getElementById(step.id);
      const indicator = document.getElementById(`${step.id}-indicator`);
      const anim = document.getElementById(`${step.id}-anim`);

      if (stepEl) {
        stepEl.classList.remove('progress-step--active', 'progress-step--complete');
      }
      if (indicator) {
        indicator.className = 'step-indicator step-indicator--pending';
        const ring = indicator.querySelector('.step-ring');
        if (ring) ring.style.display = 'none';
      }
      if (anim) {
        anim.style.display = 'none';
      }
    });
    confettiContainer.style.display = 'none';
    confettiContainer.innerHTML = '';
  }

  /**
   * Updates the progress to a specific step index (0-5).
   * Marks previous steps as complete, current as active.
   *
   * @param {number} stepIndex — 0-based step index
   * @param {Object} [data]   — Optional data (e.g., burn progress %)
   */
  function updateStep(stepIndex, data = {}) {
    if (stepIndex < 0 || stepIndex >= STEPS.length) return;

    // Mark all previous steps as complete
    for (let i = 0; i < stepIndex; i++) {
      markComplete(i);
    }

    // Mark current step as active
    markActive(stepIndex);

    // Mark all subsequent steps as pending
    for (let i = stepIndex + 1; i < STEPS.length; i++) {
      markPending(i);
    }

    // Special: burn progress bar update
    if (stepIndex === 4 && data.progress !== undefined) {
      const fill = document.querySelector(`#step-burn-anim .burn-progress__fill`);
      if (fill) {
        fill.style.width = `${data.progress}%`;
      }
    }

    // Special: style dots filling
    if (stepIndex === 3 && data.filledStyles) {
      const dots = document.querySelectorAll(`#step-captions-anim .style-dot`);
      const styleClasses = [
        'style-dot--filled-formal',
        'style-dot--filled-sarcastic',
        'style-dot--filled-humorous-tech',
        'style-dot--filled-humorous-nontech',
      ];
      dots.forEach((dot, i) => {
        if (i < data.filledStyles) {
          dot.classList.add(styleClasses[i]);
        }
      });
    }

    // Special: ready step → confetti
    if (stepIndex === 5) {
      markComplete(5);
      triggerConfetti();
    }

    currentStep = stepIndex;
  }

  function markActive(index) {
    const step = STEPS[index];
    const stepEl = document.getElementById(step.id);
    const indicator = document.getElementById(`${step.id}-indicator`);
    const anim = document.getElementById(`${step.id}-anim`);

    if (stepEl) {
      stepEl.classList.remove('progress-step--complete');
      stepEl.classList.add('progress-step--active');
    }
    if (indicator) {
      indicator.className = 'step-indicator step-indicator--active';
      const ring = indicator.querySelector('.step-ring');
      if (ring) ring.style.display = '';
    }
    if (anim) {
      anim.style.display = '';
    }
  }

  function markComplete(index) {
    const step = STEPS[index];
    const stepEl = document.getElementById(step.id);
    const indicator = document.getElementById(`${step.id}-indicator`);
    const anim = document.getElementById(`${step.id}-anim`);

    if (stepEl) {
      stepEl.classList.remove('progress-step--active');
      stepEl.classList.add('progress-step--complete');
    }
    if (indicator) {
      indicator.className = 'step-indicator step-indicator--complete';
      const ring = indicator.querySelector('.step-ring');
      if (ring) ring.style.display = 'none';
      // Add checkmark SVG
      if (!indicator.querySelector('svg')) {
        indicator.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>`;
      }
    }
    if (anim) {
      anim.style.display = 'none';
    }
  }

  function markPending(index) {
    const step = STEPS[index];
    const stepEl = document.getElementById(step.id);
    const indicator = document.getElementById(`${step.id}-indicator`);
    const anim = document.getElementById(`${step.id}-anim`);

    if (stepEl) {
      stepEl.classList.remove('progress-step--active', 'progress-step--complete');
    }
    if (indicator) {
      indicator.className = 'step-indicator step-indicator--pending';
      indicator.innerHTML = '';
      const ring = document.createElement('div');
      ring.className = 'step-ring';
      ring.style.display = 'none';
      indicator.appendChild(ring);
    }
    if (anim) {
      anim.style.display = 'none';
    }
  }

  function triggerConfetti() {
    confettiContainer.style.display = '';
    confettiContainer.innerHTML = '';
    const colors = ['#6366f1', '#a78bfa', '#f472b6', '#34d399', '#60a5fa', '#f59e0b'];
    for (let i = 0; i < 20; i++) {
      const piece = document.createElement('div');
      piece.className = 'confetti-piece';
      piece.style.left = `${40 + Math.random() * 20}%`;
      piece.style.top = `${30 + Math.random() * 10}%`;
      piece.style.background = colors[Math.floor(Math.random() * colors.length)];
      piece.style.setProperty('--confetti-x', `${(Math.random() - 0.5) * 200}px`);
      piece.style.setProperty('--confetti-y', `${Math.random() * 150 + 50}px`);
      piece.style.animationDelay = `${Math.random() * 0.5}s`;
      piece.style.width = `${4 + Math.random() * 4}px`;
      piece.style.height = `${4 + Math.random() * 4}px`;
      confettiContainer.appendChild(piece);
    }
  }

  return { show, hide, updateStep, reset };
}

/**
 * Creates the neural network SVG (6 nodes in hexagon pattern).
 * @returns {string} SVG markup
 */
function createNeuralNetworkSVG() {
  const cx = 100, cy = 80, r = 50;
  const nodes = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2;
    nodes.push({
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    });
  }

  // Connection lines between all nodes
  let lines = '';
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      lines += `<line class="neural-line" x1="${nodes[i].x}" y1="${nodes[i].y}" x2="${nodes[j].x}" y2="${nodes[j].y}"/>`;
    }
  }

  // Nodes
  let circles = '';
  nodes.forEach((n) => {
    circles += `<circle class="neural-node" cx="${n.x}" cy="${n.y}" r="8"/>`;
  });

  // Center node
  circles += `<circle class="neural-node" cx="${cx}" cy="${cy}" r="10" style="fill: rgba(99,102,241,0.4); stroke: var(--accent-indigo); stroke-width: 2;"/>`;

  // Lines from center to each node
  nodes.forEach((n) => {
    lines += `<line class="neural-line" x1="${cx}" y1="${cy}" x2="${n.x}" y2="${n.y}" style="stroke: rgba(139,92,246,0.2);"/>`;
  });

  return `
    <svg viewBox="0 0 200 160" width="200" height="160" style="display: block; margin: 0 auto;">
      ${lines}
      ${circles}
    </svg>`;
}

/**
 * Creates the inline animation HTML for each step type.
 * @param {string} type
 * @returns {string}
 */
function createStepAnimation(type) {
  switch (type) {
    case 'orbiting-dots':
      return `
        <div class="orbiting-dots">
          <div class="orbiting-dot"></div>
          <div class="orbiting-dot"></div>
          <div class="orbiting-dot"></div>
        </div>`;

    case 'waveform':
      return `
        <div class="waveform-bars">
          <div class="waveform-bar"></div>
          <div class="waveform-bar"></div>
          <div class="waveform-bar"></div>
          <div class="waveform-bar"></div>
          <div class="waveform-bar"></div>
        </div>`;

    case 'typing':
      return `<span class="typing-cursor">Abc</span>`;

    case 'style-dots':
      return `
        <div class="style-dots">
          <div class="style-dot" data-style="formal"></div>
          <div class="style-dot" data-style="sarcastic"></div>
          <div class="style-dot" data-style="humorous-tech"></div>
          <div class="style-dot" data-style="humorous-nontech"></div>
        </div>`;

    case 'progress-bar':
      return `
        <div class="burn-progress">
          <div class="burn-progress__fill" style="width: 0%"></div>
        </div>`;

    case 'ready':
      return `
        <div class="ready-check">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </div>`;

    default:
      return '';
  }
}
