/* ═══════════════════════════════════════════════════════════════
   ExportBar.js — Export bar component
   Sticky bottom glass pill with JSON, SRT, All Videos, Report,
   and ZIP All buttons. Includes download animations and ZIP modal
   integration.
   ═══════════════════════════════════════════════════════════════ */

/**
 * Icon SVG templates for export buttons.
 */
const ICONS = {
  json: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`,
  srt: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/></svg>`,
  videos: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>`,
  report: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
  zip: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`,
  spinner: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg>`,
  check: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
};

/**
 * Button configurations for the export bar.
 */
const EXPORT_BUTTONS = [
  { id: 'export-json',   label: 'JSON',         icon: 'json',   cssClass: 'export-btn--json',   event: 'export-json' },
  { id: 'export-srt',    label: 'SRT',          icon: 'srt',    cssClass: 'export-btn--srt',    event: 'export-srt' },
  { id: 'export-videos', label: 'All 4 Videos', icon: 'videos', cssClass: 'export-btn--videos', event: 'export-videos' },
  { id: 'export-report', label: 'Report',       icon: 'report', cssClass: 'export-btn--report', event: 'export-report' },
  { id: 'export-zip',    label: 'ZIP All',      icon: 'zip',    cssClass: 'export-btn--zip',    event: 'export-zip' },
];

/**
 * Creates and populates the export bar inside the given container.
 *
 * @param {HTMLElement} container — The #export-bar element
 * @returns {Object}             — Map of button elements keyed by id
 */
export function createExportBar(container) {
  container.innerHTML = '';
  const buttons = {};

  EXPORT_BUTTONS.forEach((cfg) => {
    const btn = document.createElement('button');
    btn.className = `export-btn ${cfg.cssClass}`;
    btn.id = cfg.id;
    btn.type = 'button';
    btn.setAttribute('aria-label', `Export ${cfg.label}`);

    btn.innerHTML = `
      <span class="export-btn__icon">${ICONS[cfg.icon]}</span>
      <span>${cfg.label}</span>`;

    // Dispatch custom event on click
    btn.addEventListener('click', () => {
      container.dispatchEvent(new CustomEvent(cfg.event, {
        bubbles: true,
        detail: { buttonId: cfg.id },
      }));
    });

    container.appendChild(btn);
    buttons[cfg.id] = btn;
  });

  return buttons;
}

/**
 * Animates an export button through loading → done → reset states.
 *
 * @param {HTMLElement} btn     — The export button element
 * @param {string} originalIcon — Key from ICONS for the original icon
 */
export function animateExportButton(btn, originalIcon) {
  if (!btn) return;
  const iconEl = btn.querySelector('.export-btn__icon');
  const origHTML = iconEl.innerHTML;

  // Phase 1: Loading spinner
  btn.classList.add('export-btn--loading');
  iconEl.innerHTML = ICONS.spinner;

  // Phase 2: After some time, show checkmark
  return new Promise((resolve) => {
    setTimeout(() => {
      btn.classList.remove('export-btn--loading');
      btn.classList.add('export-btn--done');
      iconEl.innerHTML = ICONS.check;

      // Phase 3: Revert after 2s
      setTimeout(() => {
        btn.classList.remove('export-btn--done');
        iconEl.innerHTML = origHTML;
        resolve();
      }, 2000);
    }, 1200);
  });
}

/**
 * Shows the ZIP modal.
 */
export function showZipModal() {
  const modal = document.getElementById('zip-modal');
  if (modal) {
    modal.classList.remove('modal-backdrop--hidden');
  }
}

/**
 * Hides the ZIP modal.
 */
export function hideZipModal() {
  const modal = document.getElementById('zip-modal');
  if (modal) {
    modal.classList.add('modal-backdrop--hidden');
  }

  // Reset progress
  const progressWrap = document.getElementById('zip-progress-wrapper');
  if (progressWrap) {
    progressWrap.classList.add('zip-progress-wrapper--hidden');
  }
}

/**
 * Updates the ZIP modal circular progress bar.
 * @param {number} percent — 0 to 100
 */
export function updateZipProgress(percent) {
  const progressWrap = document.getElementById('zip-progress-wrapper');
  const circle = document.getElementById('zip-progress-circle');
  const pctText = document.getElementById('zip-progress-pct');

  if (progressWrap) {
    progressWrap.classList.remove('zip-progress-wrapper--hidden');
  }
  if (circle) {
    const circumference = 2 * Math.PI * 34; // r=34
    const offset = circumference - (percent / 100) * circumference;
    circle.style.strokeDashoffset = offset;
  }
  if (pctText) {
    pctText.textContent = `${Math.round(percent)}%`;
  }
}

/**
 * Gets the selected export options from the ZIP modal checkboxes.
 * @returns {Object} — { videos, json, srt, report, transcript }
 */
export function getZipOptions() {
  return {
    videos:     document.getElementById('zip-opt-videos')?.checked ?? true,
    json:       document.getElementById('zip-opt-json')?.checked ?? true,
    srt:        document.getElementById('zip-opt-srt')?.checked ?? true,
    report:     document.getElementById('zip-opt-report')?.checked ?? true,
    transcript: document.getElementById('zip-opt-transcript')?.checked ?? true,
  };
}
