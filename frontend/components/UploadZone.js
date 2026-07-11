/* ═══════════════════════════════════════════════════════════════
   UploadZone.js — Drag-and-drop upload zone component
   Handles file selection, validation, drag animations,
   ripple effects, and upload progress display.
   ═══════════════════════════════════════════════════════════════ */

/**
 * Accepted file types and constraints.
 */
const ACCEPTED_TYPES = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm'];
const ACCEPTED_EXTENSIONS = ['.mp4', '.mov', '.avi', '.webm'];
const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB
const MIN_DURATION = 30;  // seconds
const MAX_DURATION = 120; // seconds

/**
 * Initializes the upload zone with all drag-and-drop, click,
 * and validation behavior.
 *
 * @param {HTMLElement} zone       — The #upload-zone element
 * @param {HTMLInputElement} input — The #file-input hidden element
 * @param {Object} callbacks      — { onFileSelected, onError, onUploadProgress }
 * @returns {Object}              — Control methods: { reset, setProgress, disable, enable }
 */
export function createUploadZone(zone, input, callbacks = {}) {
  const { onFileSelected, onError, onWarning } = callbacks;

  // ── Click to browse ──
  zone.addEventListener('click', (e) => {
    if (zone.classList.contains('upload-zone--uploading')) return;
    input.click();
  });

  // Keyboard support
  zone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (!zone.classList.contains('upload-zone--uploading')) {
        input.click();
      }
    }
  });

  // ── File input change ──
  input.addEventListener('change', () => {
    if (input.files && input.files.length > 0) {
      handleFile(input.files[0]);
    }
  });

  // ── Drag and drop events ──
  let dragCounter = 0;

  zone.addEventListener('dragenter', (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter++;
    zone.classList.add('upload-zone--dragover');
  });

  zone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter--;
    if (dragCounter <= 0) {
      dragCounter = 0;
      zone.classList.remove('upload-zone--dragover');
    }
  });

  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.stopPropagation();
  });

  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter = 0;
    zone.classList.remove('upload-zone--dragover');

    // Trigger ripple effect
    triggerRipple(e);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  });

  /**
   * Handles the selected file: validates and dispatches.
   * @param {File} file
   */
  function handleFile(file) {
    // Check if uploading an already captioned file (e.g. video_formal.mp4)
    const lowerName = file.name.toLowerCase();
    const captionedSuffixes = ['_formal', '_sarcastic', '_humorous_tech', '_humorous_non_tech'];
    const isAlreadyCaptioned = captionedSuffixes.some(suffix => {
      const extIndex = lowerName.lastIndexOf('.');
      if (extIndex === -1) return false;
      const baseName = lowerName.substring(0, extIndex);
      return baseName.endsWith(suffix);
    });

    if (isAlreadyCaptioned && onWarning) {
      onWarning('Warning: You uploaded an already-captioned video from a previous run. To avoid double captions, please upload the original clean video.');
    }

    // Validate file type
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ACCEPTED_TYPES.includes(file.type) && !ACCEPTED_EXTENSIONS.includes(ext)) {
      if (onError) {
        onError(`Invalid file format. Please upload: ${ACCEPTED_EXTENSIONS.join(', ')}`);
      }
      return;
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      if (onError) {
        onError(`File is too large (${formatFileSize(file.size)}). Maximum: 500MB.`);
      }
      return;
    }

    // Validate duration (via temporary video element)
    validateDuration(file)
      .then((duration) => {
        if (duration < MIN_DURATION) {
          if (onError) onError(`Video is too short (${Math.round(duration)}s). Minimum: 30 seconds.`);
          return;
        }
        if (duration > MAX_DURATION) {
          if (onError) onError(`Video is too long (${Math.round(duration)}s). Maximum: 2 minutes.`);
          return;
        }
        // All validations passed
        if (onFileSelected) {
          onFileSelected(file, duration);
        }
      })
      .catch(() => {
        // If we can't determine duration, allow the file through
        // (backend will validate)
        if (onFileSelected) {
          onFileSelected(file, null);
        }
      });
  }

  /**
   * Triggers the ripple effect from the drop point.
   * @param {DragEvent|MouseEvent} e
   */
  function triggerRipple(e) {
    const ripple = document.getElementById('upload-ripple');
    if (!ripple) return;

    const rect = zone.getBoundingClientRect();
    const x = (e.clientX || rect.left + rect.width / 2) - rect.left;
    const y = (e.clientY || rect.top + rect.height / 2) - rect.top;

    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;
    ripple.classList.remove('upload-zone__ripple--active');
    // Force reflow
    void ripple.offsetWidth;
    ripple.classList.add('upload-zone__ripple--active');

    setTimeout(() => {
      ripple.classList.remove('upload-zone__ripple--active');
    }, 800);
  }

  // ── Control methods ──

  /**
   * Updates the upload progress bar.
   * @param {number} percent — 0 to 100
   */
  function setProgress(percent) {
    const bar = document.getElementById('upload-progress-bar');
    const fill = document.getElementById('upload-progress-fill');
    const text = document.getElementById('upload-progress-text');

    if (bar) {
      bar.classList.add('upload-progress--visible');
      bar.setAttribute('aria-hidden', 'false');
    }
    if (fill) {
      fill.style.width = `${percent}%`;
    }
    if (text) {
      text.textContent = `${Math.round(percent)}%`;
    }
  }

  /**
   * Resets the upload zone to its initial state.
   */
  function reset() {
    zone.classList.remove('upload-zone--uploading', 'upload-zone--dragover');
    input.value = '';
    setProgress(0);

    const bar = document.getElementById('upload-progress-bar');
    if (bar) {
      bar.classList.remove('upload-progress--visible');
      bar.setAttribute('aria-hidden', 'true');
    }
  }

  /**
   * Disables the upload zone (during upload/processing).
   */
  function disable() {
    zone.classList.add('upload-zone--uploading');
  }

  /**
   * Re-enables the upload zone.
   */
  function enable() {
    zone.classList.remove('upload-zone--uploading');
  }

  return { reset, setProgress, disable, enable };
}

/**
 * Validates the video duration using a temporary video element.
 * @param {File} file
 * @returns {Promise<number>} — Duration in seconds
 */
function validateDuration(file) {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    video.preload = 'metadata';

    const objectURL = URL.createObjectURL(file);
    video.src = objectURL;

    video.addEventListener('loadedmetadata', () => {
      URL.revokeObjectURL(objectURL);
      const duration = video.duration;
      if (isFinite(duration) && duration > 0) {
        resolve(duration);
      } else {
        reject(new Error('Could not determine video duration'));
      }
    });

    video.addEventListener('error', () => {
      URL.revokeObjectURL(objectURL);
      reject(new Error('Could not load video metadata'));
    });

    // Timeout fallback
    setTimeout(() => {
      URL.revokeObjectURL(objectURL);
      reject(new Error('Metadata loading timed out'));
    }, 10000);
  });
}

/**
 * Formats a file size in bytes to a human-readable string.
 * @param {number} bytes
 * @returns {string}
 */
function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
