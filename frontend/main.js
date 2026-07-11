/* ═══════════════════════════════════════════════════════════════
   main.js — Core application logic for CapturaAI
   API integration, video sync playback, upload handling, export
   system, toast notifications, and keyboard navigation.
   ═══════════════════════════════════════════════════════════════ */

import { renderAllQuadrants, animateDownloadButton, setQuadrantVideo, STYLE_CONFIG } from './components/Quadrant.js?v=1.1';
import { renderAllCaptionCards, renderSkeletonCards, setCaptionText } from './components/CaptionCard.js?v=1.1';
import { createExportBar, animateExportButton, showZipModal, hideZipModal, updateZipProgress, getZipOptions } from './components/ExportBar.js?v=1.1';
import { createProcessingModal } from './components/ProcessingModal.js?v=1.1';
import { createUploadZone } from './components/UploadZone.js?v=1.1';
import { initAllAnimations, triggerShake, revealCards, showSkeletonLoader } from './animations.js?v=1.1';

/* ─────────────────────────────────────────────
   CONSTANTS & STATE
   ───────────────────────────────────────────── */

/** API base URL — auto-detect from current host or fallback */
const API_BASE = detectApiBase();

/** Application state */
const state = {
  videoId: null,
  fileName: null,
  captions: {},
  videoSources: {},
  videoDuration: 0,
  hasAudio: true,
  isPlaying: false,
  isSyncedPlayback: false,
  syncInterval: null,
  processingModal: null,
  uploadZone: null,
  exportButtons: null,
};

/* ─────────────────────────────────────────────
   INITIALIZATION
   ───────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize animations (particles, mesh, scroll header, page load)
  initAllAnimations();

  // Initialize components
  initUploadZone();
  initProcessingModal();
  initExportBar();
  initPlaybackControls();
  initZipModal();
  initHeaderUploadButton();
  initKeyboardNavigation();
  initSettingsPanel();
});

/* ─────────────────────────────────────────────
   API BASE URL DETECTION
   ───────────────────────────────────────────── */

function detectApiBase() {
  const loc = window.location;
  // If running on localhost, assume backend is on port 8000
  if (loc.hostname === 'localhost' || loc.hostname === '127.0.0.1') {
    return `${loc.protocol}//${loc.hostname}:8000/api`;
  }
  // Otherwise, assume same origin
  return `${loc.origin}/api`;
}

/* ─────────────────────────────────────────────
   API KEY MANAGEMENT (LEGACY)
   ───────────────────────────────────────────── */

/**
 * Gets the current API key (deprecated, now handled server-side).
 * @returns {string|null}
 */
function getApiKey() {
  return null;
}



/**
 * Gets the current vertical caption position offset from settings.
 * @returns {number}
 */
function getCaptionPadding() {
  const select = document.getElementById('setting-caption-y');
  return select ? parseFloat(select.value) : 0.18;
}

/**
 * Initializes settings panel event listeners (Y-offset, Font selection).
 */
function initSettingsPanel() {
  const fontSelect = document.getElementById('setting-caption-font');
  if (!fontSelect) return;

  fontSelect.addEventListener('change', () => {
    const selectedFont = fontSelect.value;
    // Set CSS custom property dynamically on document body
    document.documentElement.style.setProperty('--caption-font-family', `'${selectedFont}', sans-serif`);
    // Style select dropdown font style
    fontSelect.style.fontFamily = `'${selectedFont}', sans-serif`;
    
    // Apply optional spacing adjustments
    if (selectedFont === 'Bangers' || selectedFont === 'Bebas Neue') {
      fontSelect.style.letterSpacing = '0.05em';
    } else {
      fontSelect.style.letterSpacing = 'normal';
    }
  });

  // Trigger once on startup to sync initial value
  fontSelect.dispatchEvent(new Event('change'));
}

/* ─────────────────────────────────────────────
   UPLOAD ZONE
   ───────────────────────────────────────────── */

function initUploadZone() {
  const zone = document.getElementById('upload-zone');
  const input = document.getElementById('file-input');

  if (!zone || !input) return;

  state.uploadZone = createUploadZone(zone, input, {
    onFileSelected: handleFileSelected,
    onError: (msg) => showToast(msg, 'error'),
    onWarning: (msg) => showToast(msg, 'warning'),
  });
}

function initHeaderUploadButton() {
  const btn = document.getElementById('header-upload-btn');
  if (!btn) return;

  btn.addEventListener('click', () => {
    const input = document.getElementById('file-input');
    if (input) input.click();
  });
}

/**
 * Handles a successfully validated file selection.
 * @param {File} file
 * @param {number|null} duration
 */
async function handleFileSelected(file, duration) {
  state.fileName = file.name;

  // Disable upload zone
  if (state.uploadZone) {
    state.uploadZone.disable();
  }

  // Show processing modal
  if (state.processingModal) {
    state.processingModal.reset();
    state.processingModal.show();
    state.processingModal.updateStep(0);
  }

  try {
    // Upload the file
    const videoId = await uploadFile(file);
    state.videoId = videoId;

    // Start video processing
    const padding = getCaptionPadding();
    const processResponse = await fetch(`${API_BASE}/process/${videoId}?bottom_padding=${padding}`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });

    if (!processResponse.ok) {
      const errData = await processResponse.json().catch(() => ({}));
      throw new Error(errData.detail || errData.message || `Failed to start video processing (${processResponse.status})`);
    }

    // Start polling for processing status
    await pollProcessingStatus(videoId);

  } catch (err) {
    showToast(err.message || 'Upload failed. Please try again.', 'error');
    if (state.processingModal) state.processingModal.hide();
    if (state.uploadZone) {
      state.uploadZone.reset();
      state.uploadZone.enable();
    }
  }
}

/**
 * Uploads the video file to the backend.
 * @param {File} file
 * @returns {Promise<string>} — The video ID
 */
function uploadFile(file) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);

    const apiKey = getApiKey();
    if (apiKey) {
      formData.append('api_key', apiKey);
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/upload`, true);

    // Authorization header
    if (apiKey) {
      xhr.setRequestHeader('Authorization', `Bearer ${apiKey}`);
    }

    // Upload progress
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percent = (e.loaded / e.total) * 100;
        if (state.uploadZone) {
          state.uploadZone.setProgress(percent);
        }
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          resolve(data.video_id || data.id);
        } catch {
          reject(new Error('Invalid server response'));
        }
      } else {
        try {
          const errData = JSON.parse(xhr.responseText);
          let errMsg = `Upload failed (${xhr.status})`;
          if (typeof errData.detail === 'string') {
            errMsg = errData.detail;
          } else if (Array.isArray(errData.detail) && errData.detail.length > 0) {
            const firstErr = errData.detail[0];
            errMsg = firstErr.msg ? `${firstErr.loc.join('.')}: ${firstErr.msg}` : JSON.stringify(errData.detail);
          } else if (errData.message) {
            errMsg = errData.message;
          }
          reject(new Error(errMsg));
        } catch {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      }
    });


    xhr.addEventListener('error', () => {
      reject(new Error('Network error during upload'));
    });

    xhr.addEventListener('timeout', () => {
      reject(new Error('Upload timed out'));
    });

    xhr.timeout = 300000; // 5 minute timeout
    xhr.send(formData);
  });
}

/* ─────────────────────────────────────────────
   PROCESSING STATUS POLLING
   ───────────────────────────────────────────── */

/**
 * Polls the backend for video processing status.
 * Updates the processing modal steps as they complete.
 * @param {string} videoId
 */
async function pollProcessingStatus(videoId) {
  const stepMap = {
    'extracting_frames':  0,
    'analyzing_audio':    1,
    'transcribing':       2,
    'generating_captions': 3,
    'burning_subtitles':  4,
    'ready':              5,
    'complete':           5,
    'done':               5,
  };

  let attempts = 0;
  const maxAttempts = 300; // 5 minutes at 1s intervals
  const pollInterval = 1000;

  return new Promise((resolve, reject) => {
    const poll = async () => {
      attempts++;
      if (attempts > maxAttempts) {
        reject(new Error('Processing timed out'));
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/status/${videoId}`, {
          headers: getAuthHeaders(),
        });

        if (!response.ok) {
          throw new Error(`Status check failed (${response.status})`);
        }

        const data = await response.json();

        // Update processing modal step
        const stepIndex = stepMap[data.current_step] ?? stepMap[data.status] ?? -1;
        if (stepIndex >= 0 && state.processingModal) {
          const stepData = {};

          // Pass progress for burn step
          if (data.progress !== undefined) {
            stepData.progress = data.progress;
          }

          // Pass filled styles count
          if (data.captions_generated !== undefined) {
            stepData.filledStyles = data.captions_generated;
          }

          state.processingModal.updateStep(stepIndex, stepData);
        }

        // Update no-audio badge
        const badge = document.getElementById('no-audio-badge');
        if (badge) {
          if (data.has_audio === false) {
            state.hasAudio = false;
            badge.classList.remove('no-audio-badge--hidden');
          } else {
            state.hasAudio = true;
            badge.classList.add('no-audio-badge--hidden');
          }
        }

        // Check if complete
        if (data.status === 'ready' || data.status === 'complete' || data.status === 'done') {
          // Fetch final results
          await loadResults(videoId);

          // Hide processing modal after a brief delay (to show confetti)
          setTimeout(() => {
            if (state.processingModal) state.processingModal.hide();
          }, 2000);

          resolve();
          return;
        }

        // Check if error
        if (data.status === 'error' || data.status === 'failed') {
          reject(new Error(data.error || data.message || 'Processing failed'));
          return;
        }

        // Continue polling
        setTimeout(poll, pollInterval);

      } catch (err) {
        // Retry on transient errors
        if (attempts < 5) {
          setTimeout(poll, pollInterval * 2);
        } else {
          reject(err);
        }
      }
    };

    poll();
  });
}

/**
 * Loads the final results (captions + video sources) from the backend.
 * @param {string} videoId
 */
async function loadResults(videoId) {
  try {
    const response = await fetch(`${API_BASE}/captions/${videoId}`, {
      headers: getAuthHeaders(),
    });


    if (!response.ok) throw new Error('Failed to load results');

    const data = await response.json();

    // Store captions
    state.captions = data.captions || {};
    state.videoDuration = data.video?.duration || 0;
    state.hasAudio = data.video?.has_audio !== false;

    // Show/hide no-audio badge
    const badge = document.getElementById('no-audio-badge');
    if (badge) {
      if (state.hasAudio) {
        badge.classList.add('no-audio-badge--hidden');
      } else {
        badge.classList.remove('no-audio-badge--hidden');
      }
    }

    // Build video source URLs
    const styles = ['formal', 'sarcastic', 'humorous_tech', 'humorous_non_tech'];
    styles.forEach((style) => {
      state.videoSources[style] = `${API_BASE}/video/${videoId}/${style}`;
    });

    // Render the UI
    renderResults();

  } catch (err) {
    showToast('Failed to load results: ' + err.message, 'error');
  }
}

/**
 * Renders all result UI sections (quadrants, captions, controls, export).
 */
function renderResults() {
  // Hide upload section
  const uploadSection = document.getElementById('upload-section');
  if (uploadSection) uploadSection.style.display = 'none';

  // Show header upload button now that results are ready
  const headerUploadBtn = document.getElementById('header-upload-btn');
  if (headerUploadBtn) {
    headerUploadBtn.classList.remove('header-btn--hidden');
  }

  // Show quadrants
  const quadrantsSection = document.getElementById('quadrants-section');
  const quadrantsGrid = document.getElementById('quadrants-grid');
  if (quadrantsSection && quadrantsGrid) {
    quadrantsSection.classList.remove('quadrants-section--hidden');
    renderAllQuadrants(quadrantsGrid, state.videoSources, state.captions);

    // Reveal with stagger
    requestAnimationFrame(() => revealCards('#quadrants-grid'));
  }

  // Show playback controls
  const playbackSection = document.getElementById('playback-section');
  if (playbackSection) {
    playbackSection.classList.remove('playback-section--hidden');
  }

  // The captions are now beautifully embedded inside the video quadrant cards,
  // so we keep the standalone captions section hidden to keep the page clean and fit on one screen.

  // Show export bar
  const exportSection = document.getElementById('export-section');
  if (exportSection) {
    exportSection.classList.remove('export-section--hidden');
  }

  // Initialize video sync after videos are in DOM
  requestAnimationFrame(() => {
    initVideoSync();
    updateSeekBarMax();
  });

  // Listen for custom events from caption cards
  document.addEventListener('caption-regenerate', handleRegenerateCaption);
  document.addEventListener('caption-edit', handleEditCaption);
  document.addEventListener('caption-error', (e) => {
    showToast(e.detail.message, 'error');
  });

  // Listen for download events from quadrants
  document.addEventListener('quadrant-download', handleQuadrantDownload);
  document.addEventListener('quadrant-play-toggle', handleQuadrantPlayToggle);

  showToast('Processing complete! Your 4-style captions are ready.', 'success');
}

/* ─────────────────────────────────────────────
   VIDEO SYNC PLAYBACK SYSTEM
   ───────────────────────────────────────────── */

/**
 * Gets all 4 video elements.
 * @returns {HTMLVideoElement[]}
 */
function getAllVideos() {
  return Array.from(document.querySelectorAll('.quadrant-video'));
}

/**
 * Initializes synchronised playback across all 4 videos.
 */
function initVideoSync() {
  const videos = getAllVideos();
  if (videos.length === 0) return;

  // Unmute the first video, mute all other videos to prevent echoing
  videos.forEach((v, index) => {
    v.muted = index === 0 ? false : true;
  });

  // Start sync drift correction interval
  if (state.syncInterval) clearInterval(state.syncInterval);
  state.syncInterval = setInterval(() => {
    correctSyncDrift();
  }, 100);

  // Listen for timeupdate on the first video to update seek bar
  const masterVideo = videos[0];
  if (masterVideo) {
    masterVideo.addEventListener('timeupdate', updateSeekBarPosition);
    masterVideo.addEventListener('loadedmetadata', updateSeekBarMax);

    // Sync universal play/pause button icon
    const playPauseBtn = document.getElementById('btn-play-pause-all');
    if (playPauseBtn) {
      masterVideo.addEventListener('play', () => {
        playPauseBtn.innerHTML = `
          <svg class="play-pause-icon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none">
            <rect x="6" y="4" width="4" height="16"/>
            <rect x="14" y="4" width="4" height="16"/>
          </svg>`;
      });
      masterVideo.addEventListener('pause', () => {
        playPauseBtn.innerHTML = `
          <svg class="play-pause-icon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>`;
      });
    }
  }
}

/**
 * Updates the seek bar maximum value based on video duration.
 */
function updateSeekBarMax() {
  const videos = getAllVideos();
  const seekBar = document.getElementById('seek-bar');
  const totalTime = document.getElementById('seek-time-total');

  if (videos.length > 0 && videos[0].duration) {
    const duration = videos[0].duration;
    state.videoDuration = duration;
    if (seekBar) seekBar.max = duration;
    if (totalTime) totalTime.textContent = formatTime(duration);
  }
}

/**
 * Updates the seek bar position and current time display.
 */
function updateSeekBarPosition() {
  if (!state.isSyncedPlayback) return;
  const videos = getAllVideos();
  const seekBar = document.getElementById('seek-bar');
  const currentTime = document.getElementById('seek-time-current');

  if (videos.length > 0 && seekBar) {
    const ct = videos[0].currentTime;
    seekBar.value = ct;
    if (currentTime) currentTime.textContent = formatTime(ct);

    // Update CSS custom property for active track color
    const pct = state.videoDuration > 0 ? (ct / state.videoDuration) * 100 : 0;
    seekBar.style.setProperty('--seek-pct', `${pct}%`);
  }
}

/**
 * Corrects sync drift: if any video is >0.2s out of sync with
 * the reference (first) video, adjust its currentTime.
 */
function correctSyncDrift() {
  if (!state.isSyncedPlayback) return;
  const videos = getAllVideos();
  if (videos.length < 2) return;

  const refTime = videos[0].currentTime;

  for (let i = 1; i < videos.length; i++) {
    const drift = Math.abs(videos[i].currentTime - refTime);
    if (drift > 0.2) {
      videos[i].currentTime = refTime;
    }
  }
}

/**
 * Plays all 4 videos simultaneously.
 */
function playAll() {
  state.isSyncedPlayback = true;
  const videos = getAllVideos();
  if (videos.length === 0) return;

  const refTime = videos[0].currentTime || 0;

  // Sync all to reference time first and pause to prevent seek race conditions
  videos.forEach((v, index) => {
    v.pause();
    v.currentTime = refTime;
    // Unmute the first video, mute all other videos to prevent echoing
    v.muted = index === 0 ? false : true;
  });

  // Small delay to allow the browser to complete the seek before playing
  setTimeout(() => {
    const playPromises = videos.map((v) => {
      const p = v.play();
      return p ? p.catch(() => {}) : Promise.resolve();
    });

    Promise.all(playPromises).then(() => {
      state.isPlaying = true;
    });
  }, 50);
}

/**
 * Pauses all 4 videos simultaneously.
 */
function pauseAll() {
  state.isSyncedPlayback = true;
  const videos = getAllVideos();
  videos.forEach((v) => v.pause());
  state.isPlaying = false;
}

/**
 * Seeks all 4 videos to a specific time.
 * @param {number} time — Time in seconds
 */
function seekAll(time) {
  state.isSyncedPlayback = true;
  const videos = getAllVideos();
  const clampedTime = Math.max(0, Math.min(time, state.videoDuration || Infinity));
  videos.forEach((v) => {
    v.currentTime = clampedTime;
  });
}

/**
 * Jumps all videos forward or backward by a delta.
 * @param {number} delta — Seconds to jump (positive or negative)
 */
function jumpAll(delta) {
  state.isSyncedPlayback = true;
  const videos = getAllVideos();
  if (videos.length === 0) return;
  const newTime = videos[0].currentTime + delta;
  seekAll(newTime);
}

/**
 * Replays all videos from the beginning.
 */
function replayAll() {
  seekAll(0);
  playAll();
}

/**
 * Initializes playback control button event listeners.
 */
function initPlaybackControls() {
  const btnPlayPause = document.getElementById('btn-play-pause-all');
  const btnBack = document.getElementById('btn-back-10');
  const btnFwd = document.getElementById('btn-forward-10');
  const btnReplay = document.getElementById('btn-replay');
  const seekBar = document.getElementById('seek-bar');

  if (btnPlayPause) {
    btnPlayPause.addEventListener('click', () => {
      const videos = getAllVideos();
      if (videos.length === 0) return;

      const isAnyPlaying = videos.some(v => !v.paused);
      if (isAnyPlaying) {
        pauseAll();
      } else {
        playAll();
      }
    });
  }
  if (btnBack) btnBack.addEventListener('click', () => jumpAll(-10));
  if (btnFwd) btnFwd.addEventListener('click', () => jumpAll(10));
  if (btnReplay) btnReplay.addEventListener('click', replayAll);

  if (seekBar) {
    let isSeeking = false;

    seekBar.addEventListener('input', () => {
      isSeeking = true;
      const time = parseFloat(seekBar.value);
      seekAll(time);

      const currentTime = document.getElementById('seek-time-current');
      if (currentTime) currentTime.textContent = formatTime(time);

      // Update CSS custom property
      const pct = state.videoDuration > 0 ? (time / state.videoDuration) * 100 : 0;
      seekBar.style.setProperty('--seek-pct', `${pct}%`);
    });

    seekBar.addEventListener('change', () => {
      isSeeking = false;
    });
  }
}

/* ─────────────────────────────────────────────
   PROCESSING MODAL
   ───────────────────────────────────────────── */

function initProcessingModal() {
  const container = document.getElementById('processing-modal-card');
  if (!container) return;

  state.processingModal = createProcessingModal(container);
}

/* ─────────────────────────────────────────────
   EXPORT BAR
   ───────────────────────────────────────────── */

function initExportBar() {
  const container = document.getElementById('export-bar');
  if (!container) return;

  state.exportButtons = createExportBar(container);

  // Listen for export events
  container.addEventListener('export-json', handleExportJSON);
  container.addEventListener('export-srt', handleExportSRT);
  container.addEventListener('export-videos', handleExportVideos);
  container.addEventListener('export-report', handleExportReport);
  container.addEventListener('export-zip', handleExportZip);
}

async function handleExportJSON() {
  if (!state.videoId) return showToast('No video processed yet.', 'warning');

  const btn = state.exportButtons?.['export-json'];
  try {
    await animateExportButton(btn, 'json');
    triggerDownload(`${API_BASE}/export/json/${state.videoId}`, `${state.videoId}_captions.json`);
    showToast('JSON export downloaded!', 'success');
  } catch (err) {
    showToast('JSON export failed: ' + err.message, 'error');
  }
}

async function handleExportSRT() {
  if (!state.videoId) return showToast('No video processed yet.', 'warning');

  const btn = state.exportButtons?.['export-srt'];
  try {
    await animateExportButton(btn, 'srt');
    triggerDownload(`${API_BASE}/export/srt-combined/${state.videoId}`, `${state.videoId}_captions.srt`);
    showToast('SRT export downloaded!', 'success');
  } catch (err) {
    showToast('SRT export failed: ' + err.message, 'error');
  }
}

async function handleExportVideos() {
  if (!state.videoId) return showToast('No video processed yet.', 'warning');

  const btn = state.exportButtons?.['export-videos'];
  try {
    await animateExportButton(btn, 'videos');
    triggerDownload(`${API_BASE}/export/videos-zip/${state.videoId}`, `${state.videoId}_all_styles.zip`);
    showToast('All videos downloaded!', 'success');
  } catch (err) {
    showToast('Video export failed: ' + err.message, 'error');
  }
}

async function handleExportReport() {
  if (!state.videoId) return showToast('No video processed yet.', 'warning');

  const btn = state.exportButtons?.['export-report'];
  try {
    await animateExportButton(btn, 'report');
    // Open report in new tab
    window.open(`${API_BASE}/export/report/${state.videoId}`, '_blank');
    showToast('Report opened in new tab!', 'success');
  } catch (err) {
    showToast('Report export failed: ' + err.message, 'error');
  }
}

function handleExportZip() {
  if (!state.videoId) return showToast('No video processed yet.', 'warning');
  showZipModal();
}

/* ─────────────────────────────────────────────
   ZIP MODAL
   ───────────────────────────────────────────── */

function initZipModal() {
  const cancelBtn = document.getElementById('zip-cancel-btn');
  const confirmBtn = document.getElementById('zip-confirm-btn');
  const backdrop = document.getElementById('zip-modal');

  if (cancelBtn) cancelBtn.addEventListener('click', hideZipModal);

  if (backdrop) {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) hideZipModal();
    });
  }

  if (confirmBtn) {
    confirmBtn.addEventListener('click', async () => {
      if (!state.videoId) return;

      const options = getZipOptions();

      try {
        // Simulate progress
        let progress = 0;
        const progressInterval = setInterval(() => {
          progress += Math.random() * 15 + 5;
          if (progress > 95) progress = 95;
          updateZipProgress(progress);
        }, 400);

        // Make API request
        const response = await fetch(`${API_BASE}/export/full-zip/${state.videoId}`, {
          method: 'POST',
          headers: {
            ...getAuthHeaders(),
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(options),
        });

        clearInterval(progressInterval);

        if (!response.ok) throw new Error('ZIP creation failed');

        updateZipProgress(100);

        // Download the blob
        const blob = await response.blob();
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const filename = `CapturaAI_Export_${state.videoId}_${timestamp}.zip`;
        downloadBlob(blob, filename);

        setTimeout(() => {
          hideZipModal();
          showToast('Master ZIP downloaded!', 'success');
        }, 500);

      } catch (err) {
        hideZipModal();
        showToast('ZIP export failed: ' + err.message, 'error');
      }
    });
  }
}

/* ─────────────────────────────────────────────
   CAPTION REGENERATION
   ───────────────────────────────────────────── */

async function handleRegenerateCaption(e) {
  const { style } = e.detail;
  if (!state.videoId || !style) return;

  const config = STYLE_CONFIG[style];
  if (!config) return;

  const textEl = document.getElementById(`caption-text-${config.cssClass}`);
  if (!textEl) return;

  // Show loading state
  const origText = textEl.textContent;
  textEl.textContent = 'Regenerating...';
  textEl.style.opacity = '0.5';

  try {
    const padding = getCaptionPadding();
    const response = await fetch(`${API_BASE}/captions/${state.videoId}/${style}/regenerate?bottom_padding=${padding}`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });

    if (!response.ok) throw new Error('Regeneration failed');

    const data = await response.json();
    const newCaption = data.caption || data.text || '';

    // Update state
    state.captions[style] = newCaption;

    // Update card
    const card = document.getElementById(`caption-card-${config.cssClass}`);
    if (card) {
      setCaptionText(card, newCaption);
    }

    // Reload corresponding video in quadrant with cache busting query param
    const quadCard = document.getElementById(`quadrant-${config.cssClass}`);
    if (quadCard) {
      const freshSrc = `${API_BASE}/video/${state.videoId}/${style}?t=${Date.now()}`;
      setQuadrantVideo(quadCard, freshSrc);
    }

    textEl.style.opacity = '1';
    showToast(`${config.label} caption regenerated!`, 'success');

  } catch (err) {
    textEl.textContent = origText;
    textEl.style.opacity = '1';
    showToast(`Failed to regenerate ${config.label} caption: ${err.message}`, 'error');
  }
}

/**
 * Handles saving manual caption edits to the backend.
 */
async function handleEditCaption(e) {
  const { style, text } = e.detail;
  if (!state.videoId || !style) return;

  try {
    const padding = getCaptionPadding();
    const response = await fetch(`${API_BASE}/captions/${state.videoId}/${style}`, {
      method: 'PUT',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text, bottom_padding: padding }),
    });

    if (!response.ok) throw new Error('Failed to save caption edit');

    // Update local state text
    if (state.captions[style]) {
      if (typeof state.captions[style] === 'object') {
        state.captions[style].text = text;
      } else {
        state.captions[style] = text;
      }
    }

    // Reload corresponding video in quadrant with cache busting query param
    const config = STYLE_CONFIG[style];
    if (config) {
      const quadCard = document.getElementById(`quadrant-${config.cssClass}`);
      if (quadCard) {
        const freshSrc = `${API_BASE}/video/${state.videoId}/${style}?t=${Date.now()}`;
        setQuadrantVideo(quadCard, freshSrc);
      }
    }

    showToast('Caption updated successfully!', 'success');
  } catch (err) {
    showToast('Failed to save caption edit: ' + err.message, 'error');
  }
}

/* ─────────────────────────────────────────────
   QUADRANT VIDEO DOWNLOAD
   ───────────────────────────────────────────── */

function handleQuadrantDownload(e) {
  const { style } = e.detail;
  if (!state.videoId || !style) return;

  const config = STYLE_CONFIG[style];
  if (!config) return;

  const card = document.getElementById(`quadrant-${config.cssClass}`);
  if (card) animateDownloadButton(card);

  const fileName = state.fileName
    ? state.fileName.replace(/\.[^.]+$/, `_${style}.mp4`)
    : `${state.videoId}_${style}.mp4`;

  triggerDownload(`${API_BASE}/download/${state.videoId}/${style}`, fileName);
}

/**
 * Handles toggling play/pause for a single video quadrant.
 * Unmutes this video and pauses/mutes all other quadrants.
 */
function handleQuadrantPlayToggle(e) {
  const { videoElement } = e.detail;
  if (!videoElement) return;

  state.isSyncedPlayback = false; // Disable synced playback mode

  if (videoElement.paused) {
    videoElement.muted = false;
    videoElement.play().catch(() => {});
  } else {
    videoElement.pause();
    videoElement.muted = true;
  }
}

/* ─────────────────────────────────────────────
   TOAST NOTIFICATION SYSTEM
   ───────────────────────────────────────────── */

/**
 * Shows a toast notification.
 *
 * @param {string} message — The message to display
 * @param {string} [type='info'] — One of: success, error, warning, info
 * @param {number} [duration=4000] — Auto-dismiss time in ms
 */
function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;

  // Icon
  const iconMap = {
    success: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
    error: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    warning: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    info: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
  };

  toast.innerHTML = `
    <span class="toast__icon">${iconMap[type] || iconMap.info}</span>
    <span>${escapeHTML(message)}</span>
    <button class="toast__close" type="button" aria-label="Dismiss notification">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    </button>`;

  // Close button handler
  toast.querySelector('.toast__close').addEventListener('click', () => {
    dismissToast(toast);
  });

  container.appendChild(toast);

  // Auto dismiss
  if (duration > 0) {
    setTimeout(() => {
      dismissToast(toast);
    }, duration);
  }
}

/**
 * Dismisses a toast with exit animation.
 * @param {HTMLElement} toast
 */
function dismissToast(toast) {
  if (!toast || toast.classList.contains('toast--exit')) return;
  toast.classList.add('toast--exit');
  toast.addEventListener('animationend', () => {
    toast.remove();
  }, { once: true });
}

/* ─────────────────────────────────────────────
   KEYBOARD NAVIGATION
   ───────────────────────────────────────────── */

function initKeyboardNavigation() {
  document.addEventListener('keydown', (e) => {
    // Space: toggle play/pause
    if (e.code === 'Space' && !isInputFocused()) {
      e.preventDefault();
      if (state.isPlaying) {
        pauseAll();
      } else {
        playAll();
      }
    }

    // Arrow keys: seek
    if (e.code === 'ArrowLeft' && !isInputFocused()) {
      e.preventDefault();
      jumpAll(e.shiftKey ? -10 : -5);
    }
    if (e.code === 'ArrowRight' && !isInputFocused()) {
      e.preventDefault();
      jumpAll(e.shiftKey ? 10 : 5);
    }

    // Escape: close modals
    if (e.code === 'Escape') {
      hideZipModal();
    }
  });
}

/**
 * Checks if an input-like element is currently focused.
 */
function isInputFocused() {
  const tag = document.activeElement?.tagName?.toLowerCase();
  return tag === 'input' || tag === 'textarea' || document.activeElement?.isContentEditable;
}

/* ─────────────────────────────────────────────
   UTILITY FUNCTIONS
   ───────────────────────────────────────────── */

/**
 * Returns authorization headers for API requests.
 * @returns {Object}
 */
function getAuthHeaders() {
  const key = getApiKey();
  const headers = {};
  if (key) {
    headers['Authorization'] = `Bearer ${key}`;
  }
  return headers;
}

/**
 * Triggers a file download from a URL.
 * @param {string} url
 * @param {string} filename
 */
function triggerDownload(url, filename) {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.style.display = 'none';

  // Add auth header via fetch if needed
  const key = getApiKey();
  if (key) {
    fetch(url, { headers: getAuthHeaders() })
      .then((res) => res.blob())
      .then((blob) => {
        downloadBlob(blob, filename);
      })
      .catch(() => {
        // Fallback: direct link
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      });
  } else {
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }
}

/**
 * Downloads a Blob as a file.
 * @param {Blob} blob
 * @param {string} filename
 */
function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 100);
}

/**
 * Formats seconds to m:ss display string.
 * @param {number} seconds
 * @returns {string}
 */
function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/**
 * Simple debounce utility.
 * @param {Function} fn
 * @param {number} delay
 * @returns {Function}
 */
function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Escapes HTML entities in a string to prevent XSS.
 * @param {string} str
 * @returns {string}
 */
function escapeHTML(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
