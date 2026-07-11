/* ═══════════════════════════════════════════════════════════════
   CaptionCard.js — Caption text card component
   Glass card with colored left border, editable text area,
   character count, and Copy / Edit / Regenerate action buttons.
   ═══════════════════════════════════════════════════════════════ */

import { STYLE_CONFIG } from './Quadrant.js?v=1.1';

/**
 * Creates a single caption card element.
 *
 * @param {string} styleKey   — One of: formal, sarcastic, humorous_tech, humorous_non_tech
 * @param {string} text       — The caption text to display
 * @param {object} [options]  — Optional overrides
 * @returns {HTMLElement}     — The caption card DOM node
 */
export function createCaptionCard(styleKey, text, options = {}) {
  const config = STYLE_CONFIG[styleKey];
  if (!config) throw new Error(`Unknown style key: ${styleKey}`);

  const captionText = (text && typeof text === 'object') ? (text.text || '') : (text || '');

  const card = document.createElement('div');
  card.className = `caption-card caption-card--${config.cssClass} reveal-card`;
  card.id = `caption-card-${config.cssClass}`;
  card.setAttribute('data-style', styleKey);

  // ── Style label ──
  const label = document.createElement('span');
  label.className = `caption-card__label caption-card__label--${config.cssClass}`;
  label.textContent = config.label;
  card.appendChild(label);

  // ── Text area (content-editable) ──
  const textEl = document.createElement('div');
  textEl.className = 'caption-card__text';
  textEl.id = `caption-text-${config.cssClass}`;
  textEl.textContent = captionText;
  textEl.setAttribute('role', 'textbox');
  textEl.setAttribute('aria-label', `${config.label} caption text`);
  textEl.setAttribute('tabindex', '0');
  card.appendChild(textEl);

  // ── Bottom row: actions + char count ──
  const actionsRow = document.createElement('div');
  actionsRow.className = 'caption-card__actions';

  // Copy button
  const copyBtn = createActionButton(
    `copy-${config.cssClass}`,
    'Copy',
    `Copy ${config.label} caption`,
    /* icon */ `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`
  );

  // Edit button
  const editBtn = createActionButton(
    `edit-${config.cssClass}`,
    'Edit',
    `Edit ${config.label} caption`,
    /* icon */ `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`
  );

  // Regenerate button
  const regenBtn = createActionButton(
    `regen-${config.cssClass}`,
    'Regenerate',
    `Regenerate ${config.label} caption`,
    /* icon */ `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`
  );

  // Character count
  const charCount = document.createElement('span');
  charCount.className = 'caption-card__charcount';
  charCount.id = `charcount-${config.cssClass}`;
  charCount.textContent = `${captionText.length} chars`;

  actionsRow.appendChild(copyBtn);
  actionsRow.appendChild(editBtn);
  actionsRow.appendChild(regenBtn);
  actionsRow.appendChild(charCount);
  card.appendChild(actionsRow);

  // ── EVENTS ──

  // Copy handler
  copyBtn.addEventListener('click', () => {
    const currentText = textEl.textContent || '';
    navigator.clipboard.writeText(currentText).then(() => {
      copyBtn.classList.add('caption-action-btn--copied');
      const origInner = copyBtn.innerHTML;
      copyBtn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        <span>Copied!</span>`;
      setTimeout(() => {
        copyBtn.classList.remove('caption-action-btn--copied');
        copyBtn.innerHTML = origInner;
      }, 1500);
    }).catch(() => {
      card.dispatchEvent(new CustomEvent('caption-error', {
        bubbles: true,
        detail: { message: 'Failed to copy to clipboard' },
      }));
    });
  });

  // Edit toggle handler
  let isEditing = false;
  editBtn.addEventListener('click', () => {
    isEditing = !isEditing;
    textEl.contentEditable = isEditing ? 'true' : 'false';
    textEl.classList.toggle('caption-card__text--editing', isEditing);

    if (isEditing) {
      textEl.focus();
      editBtn.querySelector('span').textContent = 'Save';
    } else {
      editBtn.querySelector('span').textContent = 'Edit';
      charCount.textContent = `${textEl.textContent.length} chars`;
      card.dispatchEvent(new CustomEvent('caption-edit', {
        bubbles: true,
        detail: { style: styleKey, text: textEl.textContent },
      }));
    }
  });

  // Save on blur when editing
  textEl.addEventListener('blur', () => {
    if (isEditing) {
      isEditing = false;
      textEl.contentEditable = 'false';
      textEl.classList.remove('caption-card__text--editing');
      editBtn.querySelector('span').textContent = 'Edit';
      charCount.textContent = `${textEl.textContent.length} chars`;
      card.dispatchEvent(new CustomEvent('caption-edit', {
        bubbles: true,
        detail: { style: styleKey, text: textEl.textContent },
      }));
    }
  });

  // Update char count on input
  textEl.addEventListener('input', () => {
    charCount.textContent = `${textEl.textContent.length} chars`;
  });

  // Regenerate handler (dispatch event for main.js to handle)
  regenBtn.addEventListener('click', () => {
    card.dispatchEvent(new CustomEvent('caption-regenerate', {
      bubbles: true,
      detail: { style: styleKey },
    }));
  });

  return card;
}

/**
 * Updates the text content of an existing caption card.
 * @param {HTMLElement} card
 * @param {string} text
 */
export function setCaptionText(card, text) {
  const textEl = card.querySelector('.caption-card__text');
  const charCount = card.querySelector('.caption-card__charcount');
  const captionText = (text && typeof text === 'object') ? (text.text || '') : (text || '');
  if (textEl) {
    textEl.textContent = captionText;
  }
  if (charCount) {
    charCount.textContent = `${captionText.length} chars`;
  }
}

/**
 * Renders all 4 caption cards into the container.
 * @param {HTMLElement} container — The #captions-grid element
 * @param {Object} captions      — { formal: "text", sarcastic: "text", ... }
 */
export function renderAllCaptionCards(container, captions = {}) {
  container.innerHTML = '';
  const styles = ['formal', 'sarcastic', 'humorous_tech', 'humorous_non_tech'];
  styles.forEach((key) => {
    const card = createCaptionCard(key, captions[key] || '');
    container.appendChild(card);
  });
}

/**
 * Renders skeleton loading cards (shimmer placeholders).
 * @param {HTMLElement} container
 */
export function renderSkeletonCards(container) {
  container.innerHTML = '';
  for (let i = 0; i < 4; i++) {
    const skel = document.createElement('div');
    skel.className = 'skeleton-card reveal-card';
    skel.innerHTML = `
      <div class="skeleton-line skeleton-line--full"></div>
      <div class="skeleton-line skeleton-line--medium"></div>
      <div class="skeleton-line skeleton-line--short"></div>`;
    container.appendChild(skel);
  }
}

/**
 * Helper: creates an action button element.
 */
function createActionButton(id, label, ariaLabel, iconHTML) {
  const btn = document.createElement('button');
  btn.className = 'caption-action-btn';
  btn.id = id;
  btn.type = 'button';
  btn.setAttribute('aria-label', ariaLabel);
  btn.innerHTML = `${iconHTML}<span>${label}</span>`;
  return btn;
}
