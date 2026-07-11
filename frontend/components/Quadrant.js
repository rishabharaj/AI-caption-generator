/* ═══════════════════════════════════════════════════════════════
   Quadrant.js — Video quadrant component
   Creates a unified card with a video player (in wrapper), its corresponding
   caption card, and a download button at the bottom.
   ═══════════════════════════════════════════════════════════════ */

import { createCaptionCard } from './CaptionCard.js?v=1.1';

/**
 * Style configuration map with colors, labels, and CSS class suffixes.
 */
export const STYLE_CONFIG = {
  formal: {
    label: 'Formal',
    color: '#60a5fa',
    cssClass: 'formal',
    glowClass: 'glow-formal',
  },
  sarcastic: {
    label: 'Sarcastic',
    color: '#f472b6',
    cssClass: 'sarcastic',
    glowClass: 'glow-sarcastic',
  },
  humorous_tech: {
    label: 'Humorous-Tech',
    color: '#a78bfa',
    cssClass: 'humorous-tech',
    glowClass: 'glow-humorous-tech',
  },
  humorous_non_tech: {
    label: 'Humorous-NonTech',
    color: '#34d399',
    cssClass: 'humorous-nontech',
    glowClass: 'glow-humorous-nontech',
  },
};

/**
 * Creates a single video quadrant card element.
 *
 * @param {string} styleKey    — One of: formal, sarcastic, humorous_tech, humorous_non_tech
 * @param {string} videoSrc    — URL to the captioned video MP4
 * @param {string} captionText — The caption text to display below the video
 * @returns {HTMLElement}      — The quadrant card DOM node
 */
export function createQuadrant(styleKey, videoSrc, captionText = '') {
  const config = STYLE_CONFIG[styleKey];
  if (!config) throw new Error(`Unknown style key: ${styleKey}`);

  const card = document.createElement('div');
  card.className = 'quadrant-card reveal-card';
  card.id = `quadrant-${config.cssClass}`;
  card.setAttribute('data-style', styleKey);

  // ── Video wrapper (maintains 16:9 ratio) ──
  const videoWrapper = document.createElement('div');
  videoWrapper.className = 'quadrant-video-wrapper';

  // Style badge
  const badge = document.createElement('span');
  badge.className = `quadrant-badge quadrant-badge--${config.cssClass}`;
  badge.textContent = config.label;
  badge.setAttribute('aria-label', `${config.label} style`);
  videoWrapper.appendChild(badge);

  // Individual play button
  const playBtn = document.createElement('button');
  playBtn.className = 'quadrant-play-btn';
  playBtn.id = `play-${config.cssClass}`;
  playBtn.type = 'button';
  playBtn.setAttribute('aria-label', `Play ${config.label} video individually`);
  playBtn.innerHTML = `
    <svg class="play-icon" width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
      <polygon points="5 3 19 12 5 21 5 3"/>
    </svg>`;
  videoWrapper.appendChild(playBtn);

  // Video element
  const video = document.createElement('video');
  video.className = 'quadrant-video';
  video.id = `video-${config.cssClass}`;
  video.preload = 'metadata';
  video.muted = true;
  video.playsInline = true;
  video.setAttribute('aria-label', `${config.label} captioned video`);
  if (videoSrc) {
    video.src = videoSrc;
  }
  videoWrapper.appendChild(video);

  // Loading spinner overlay
  const spinner = document.createElement('div');
  spinner.className = 'quadrant-spinner';
  spinner.id = `spinner-${config.cssClass}`;
  spinner.setAttribute('aria-label', 'Loading video');
  spinner.innerHTML = `
    <div class="dual-ring">
      <div class="dual-ring__outer"></div>
      <div class="dual-ring__inner"></div>
    </div>`;
  videoWrapper.appendChild(spinner);

  // Timestamp
  const timestamp = document.createElement('span');
  timestamp.className = 'quadrant-timestamp';
  timestamp.id = `timestamp-${config.cssClass}`;
  timestamp.textContent = '0:00';
  videoWrapper.appendChild(timestamp);

  card.appendChild(videoWrapper);

  // ── Caption Card (nested) ──
  const captionCard = createCaptionCard(styleKey, captionText);
  card.appendChild(captionCard);

  // ── Events: hide spinner when video can play ──
  video.addEventListener('canplay', () => {
    spinner.classList.add('quadrant-spinner--hidden');
  }, { once: true });

  // ── Events: update timestamp ──
  video.addEventListener('timeupdate', () => {
    timestamp.textContent = formatTime(video.currentTime);
  });

  // ── Events: update individual play button icon ──
  video.addEventListener('play', () => {
    card.classList.add('is-playing');
    playBtn.innerHTML = `
      <svg class="play-icon" width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <rect x="6" y="4" width="4" height="16"/>
        <rect x="14" y="4" width="4" height="16"/>
      </svg>`;
  });

  video.addEventListener('pause', () => {
    card.classList.remove('is-playing');
    playBtn.innerHTML = `
      <svg class="play-icon" width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <polygon points="5 3 19 12 5 21 5 3"/>
      </svg>`;
  });

  // ── Play button click handler ──
  playBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    card.dispatchEvent(new CustomEvent('quadrant-play-toggle', {
      bubbles: true,
      detail: { style: styleKey, videoElement: video },
    }));
  });

  return card;
}

/**
 * Sets the video source on an existing quadrant.
 * @param {HTMLElement} card
 * @param {string} src
 */
export function setQuadrantVideo(card, src) {
  const video = card.querySelector('.quadrant-video');
  const spinner = card.querySelector('.quadrant-spinner');
  if (video) {
    video.src = src;
    video.load();
    if (spinner) spinner.classList.remove('quadrant-spinner--hidden');
  }
}

/**
 * Triggers the download button's loading → complete animation cycle.
 * @param {HTMLElement} card
 */
export function animateDownloadButton(card) {
  const btn = card.querySelector('.quadrant-download-btn');
  if (!btn) return;

  btn.classList.add('download-state--loading');
  const labelSpan = btn.querySelector('span');
  const origText = labelSpan ? labelSpan.textContent : 'Download Video';

  if (labelSpan) labelSpan.textContent = 'Preparing...';

  setTimeout(() => {
    btn.classList.remove('download-state--loading');
    btn.classList.add('download-state--complete');

    if (labelSpan) labelSpan.textContent = 'Downloaded!';

    // Swap icon to checkmark temporarily
    const origSVG = btn.querySelector('svg').outerHTML;
    btn.querySelector('svg').outerHTML = `
      <svg class="download-icon" width="16" height="16" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"/>
      </svg>`;

    setTimeout(() => {
      btn.classList.remove('download-state--complete');
      if (labelSpan) labelSpan.textContent = origText;
      btn.querySelector('svg').outerHTML = origSVG;
    }, 2000);
  }, 1000);
}

/**
 * Renders all 4 quadrants into the grid container.
 * @param {HTMLElement} container — The #quadrants-grid element
 * @param {Object} videoSources  — { formal: url, sarcastic: url, ... }
 * @param {Object} captions      — { formal: text, sarcastic: text, ... }
 */
export function renderAllQuadrants(container, videoSources = {}, captions = {}) {
  container.innerHTML = '';
  const styles = ['formal', 'sarcastic', 'humorous_tech', 'humorous_non_tech'];
  styles.forEach((key) => {
    const card = createQuadrant(key, videoSources[key] || '', captions[key] || '');
    container.appendChild(card);
  });
}

/**
 * Format seconds to m:ss string.
 * @param {number} seconds
 * @returns {string}
 */
function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
