"""
HTML page templates for /slides, /notes, and /presenter views.
"""

_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
<link rel="stylesheet" href="/pitchfork.css">
<link rel="stylesheet" href="/styles.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
</head>"""

SLIDES_PAGE = _HEAD.format(title="Pitchfork — Slides") + """
<body class="view-slides">
<div id="slide-container">
  <div id="slide-content"></div>
  <canvas id="draw-canvas"></canvas>
  <img id="slide-logo" src="/logo.png" alt="" onerror="this.style.display='none'">
  <div id="slide-counter"></div>
</div>

<script>
const slides = __SLIDES_JSON__;
let current = location.hash ? parseInt(location.hash.slice(1)) || 0 : 0;

const ws = new WebSocket(`ws://${location.hostname}:__WS_PORT__`);
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === 'navigate') { current = msg.index; clearCanvas(); render(); }
  if (msg.type === 'reload') { _reloading = true; location.hash = '#' + current; location.reload(); }
};

function navigate(idx) {
  current = Math.max(0, Math.min(slides.length - 1, idx));
  clearCanvas();
  render();
  ws.send(JSON.stringify({ type: 'navigate', index: current }));
}

function render() {
  const slide = slides[current];
  document.getElementById('slide-content').innerHTML = slide.html;
  document.getElementById('slide-counter').textContent = (current + 1) + ' / ' + slides.length;
  document.querySelectorAll('pre code').forEach(el => hljs.highlightElement(el));
}

// ── Drawing ──────────────────────────────────────────────────
const canvas = document.getElementById('draw-canvas');
const ctx = canvas.getContext('2d');
let drawing = false;
let hasMoved = false;

const cs = getComputedStyle(document.documentElement);
function drawColor() { return cs.getPropertyValue('--pf-draw-color').trim() || '#ff3b30'; }
function drawWidth() { return parseFloat(cs.getPropertyValue('--pf-draw-width')) || 4; }

function resizeCanvas() {
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height);
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  ctx.putImageData(data, 0, 0);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
}

// When interactive elements (iframes, videos, links, form controls) are hovered
// or touched, disable pointer events on the drawing canvas so their controls
// are clickable. Re-binds after slide content changes.
function bindInteractiveGuard() {
  const SELECTOR = 'iframe, video, audio, a, button, input, select, textarea';

  // Check what's underneath the drawing canvas at a given point by
  // temporarily disabling pointer-events on the canvas, querying
  // elementFromPoint, then restoring pointer-events.
  function elementUnderPoint(x, y) {
    const prev = canvas.style.pointerEvents;
    canvas.style.pointerEvents = 'none';
    const el = document.elementFromPoint(x, y);
    canvas.style.pointerEvents = prev;
    return el;
  }

  function updateAtPoint(x, y) {
    const el = elementUnderPoint(x, y);
    const hit = el && el.closest && el.closest(SELECTOR);
    if (hit) {
      canvas.style.pointerEvents = 'none';
    } else {
      canvas.style.pointerEvents = '';
    }
  }

  // Pointer movement (mouse/touch) drives the check
  document.addEventListener('pointermove', (e) => {
    updateAtPoint(e.clientX, e.clientY);
  }, { passive: true });

  document.addEventListener('touchstart', (e) => {
    const t = e.touches && e.touches[0];
    if (t) updateAtPoint(t.clientX, t.clientY);
  }, { passive: true });

  // Also check on click/press to ensure canvas stays disabled while
  // interacting with the control until pointer moves away.
  document.addEventListener('pointerdown', (e) => {
    updateAtPoint(e.clientX, e.clientY);
  }, true);

  // Re-bind on DOM changes (new iframes / interactive elements may appear)
  const container = document.getElementById('slide-content');
  if (!container) return;
  const obs = new MutationObserver(() => { /* no-op: pointer handlers check underlying elements */ });
  obs.observe(container, { childList: true, subtree: true });
}

function clearCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function getPos(e) {
  if (e.touches) return { x: e.touches[0].clientX, y: e.touches[0].clientY };
  return { x: e.clientX, y: e.clientY };
}

canvas.addEventListener('mousedown', (e) => {
  drawing = true;
  hasMoved = false;
  const p = getPos(e);
  ctx.beginPath();
  ctx.moveTo(p.x, p.y);
  ctx.strokeStyle = drawColor();
  ctx.lineWidth = drawWidth();
});

canvas.addEventListener('mousemove', (e) => {
  if (!drawing) return;
  hasMoved = true;
  const p = getPos(e);
  ctx.lineTo(p.x, p.y);
  ctx.stroke();
});

canvas.addEventListener('mouseup', (e) => {
  if (drawing && !hasMoved) {
    const p = getPos(e);
    ctx.beginPath();
    ctx.arc(p.x, p.y, drawWidth() / 2, 0, Math.PI * 2);
    ctx.fillStyle = drawColor();
    ctx.fill();
  }
  drawing = false;
});

canvas.addEventListener('mouseleave', () => { drawing = false; });
window.addEventListener('resize', resizeCanvas);

resizeCanvas();

bindInteractiveGuard();

// Track all spawned popup windows so they can be closed when this tab closes.
const _spawnedWindows = [];
let _reloading = false;

function _openPopup(url, name, features) {
  const win = window.open(url, name, features);
  if (win) _spawnedWindows.push(win);
  return win;
}

window.addEventListener('beforeunload', () => {
  if (_reloading) return;
  _spawnedWindows.forEach(w => { try { if (w && !w.closed) w.close(); } catch (e) {} });
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Backspace')  { clearCanvas(); return; }
  if (e.key === ' ' || e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === 'j') { e.preventDefault(); navigate(current + 1); }
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp'   || e.key === 'k') navigate(current - 1);
  if (e.key === 'p') _openPopup('/presenter', 'Presenter View', 'location,status,scrollbars,resizable,width=1080,height=720');
  if (e.key === 'n') _openPopup('/notes', 'Notes View', 'location,status,scrollbars,resizable,width=680,height=1080');
  if (e.key === 't') _openPopup('/timer', 'Timer', 'width=300,height=240');
});

render();
</script>
</body></html>
"""

NOTES_PAGE = _HEAD.format(title="Pitchfork — Notes") + """
<body class="view-notes">
<div id="strip-container">
  <div id="strip"></div>
</div>
<div id="notes-panel">
  <div id="notes-list"></div>
</div>

<script>
const slides = __SLIDES_JSON__;
let current = location.hash ? parseInt(location.hash.slice(1)) || 0 : 0;

const ws = new WebSocket(`ws://${location.hostname}:__WS_PORT__`);
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === 'navigate') { current = msg.index; render(); }
  if (msg.type === 'reload') { location.hash = '#' + current; location.reload(); }
};

function navigate(idx) {
  current = Math.max(0, Math.min(slides.length - 1, idx));
  render();
  ws.send(JSON.stringify({ type: 'navigate', index: current }));
}

function buildStrip() {
  const strip = document.getElementById('strip');
  strip.innerHTML = '';
  slides.forEach((slide, i) => {
    const thumb = document.createElement('div');
    thumb.className = 'thumb';
    thumb.dataset.index = i;
    thumb.innerHTML = '<div class="thumb-inner">' + slide.html + '</div><span class="thumb-num">' + (i + 1) + '</span>';
    thumb.addEventListener('click', () => navigate(i));
    strip.appendChild(thumb);
  });
}

function buildNotesList() {
  const list = document.getElementById('notes-list');
  list.innerHTML = '';
  slides.forEach((slide, i) => {
    const entry = document.createElement('div');
    entry.className = 'notes-entry dimmed';
    entry.dataset.index = i;
    const label = document.createElement('div');
    label.className = 'notes-entry-label';
    label.textContent = 'Slide ' + (i + 1);
    entry.appendChild(label);
    const body = document.createElement('div');
    body.innerHTML = slide.notes;
    entry.appendChild(body);
    list.appendChild(entry);
  });
}

// Make tasklist checkboxes interactive in notes (no persistence).
function _makeTasklistsInteractive(root) {
  if (!root) root = document;
  root.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    try { cb.disabled = false; } catch (e) {}
    // initialize class based on checked state
    const li = cb.closest('li');
    if (li) li.classList.toggle('task-checked', cb.checked);
    cb.addEventListener('change', (e) => {
      const li = e.target.closest('li');
      if (li) li.classList.toggle('task-checked', e.target.checked);
    });
    // allow clicking the list item or label to toggle checkbox when label markup varies
    if (li) {
      li.addEventListener('click', (ev) => {
        // don't double-toggle if the actual input was clicked
        if (ev.target === cb) return;
        cb.checked = !cb.checked;
        cb.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }
  });
}

function render() {
  document.querySelectorAll('.thumb').forEach(t => {
    t.classList.toggle('active', parseInt(t.dataset.index) === current);
  });
  document.querySelectorAll('.notes-entry').forEach(e => {
    e.classList.toggle('dimmed', parseInt(e.dataset.index) !== current);
  });

  const activeThumb = document.querySelector('.thumb.active');
  if (activeThumb) activeThumb.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });

  const activeEntry = document.querySelector('.notes-entry:not(.dimmed)');
  if (activeEntry) activeEntry.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === 'j' || e.key === ' ') navigate(current + 1);
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp'   || e.key === 'k') navigate(current - 1);
});

buildStrip();
buildNotesList();
render();
_makeTasklistsInteractive(document.getElementById('notes-list'));
</script>
</body></html>
"""

PRESENTER_PAGE = _HEAD.format(title="Pitchfork — Presenter") + """
<body class="view-presenter">
<div id="presenter-grid">
  <div id="pres-current">
    <div class="pres-label">Current</div>
    <div id="pres-current-slide" class="pres-slide-frame"></div>
  </div>
  <div id="pres-next">
    <div class="pres-label">Next</div>
    <div id="pres-next-slide" class="pres-slide-frame"></div>
  </div>
  <div id="pres-meta">
    <div id="pres-counter"></div>
    <div id="pres-timer">00:00</div>
    <div id="timer-controls">
      <button onclick="startTimer()">Start</button>
      <button onclick="pauseTimer()">Pause</button>
      <button onclick="resetTimer()">Reset</button>
    </div>
  </div>
  <div id="pres-notes">
    <div id="pres-notes-list"></div>
  </div>
</div>

<script>
const slides = __SLIDES_JSON__;
let current = location.hash ? parseInt(location.hash.slice(1)) || 0 : 0;
let timerSeconds = 0, timerInterval = null;

const ws = new WebSocket(`ws://${location.hostname}:__WS_PORT__`);
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === 'navigate') { current = msg.index; render(); }
  if (msg.type === 'reload') { location.hash = '#' + current; location.reload(); }
};

function navigate(idx) {
  current = Math.max(0, Math.min(slides.length - 1, idx));
  render();
  ws.send(JSON.stringify({ type: 'navigate', index: current }));
}

function buildNotesList() {
  const list = document.getElementById('pres-notes-list');
  list.innerHTML = '';
  slides.forEach((slide, i) => {
    const entry = document.createElement('div');
    entry.className = 'pres-notes-entry dimmed';
    entry.dataset.index = i;
    const label = document.createElement('div');
    label.className = 'pres-notes-entry-label';
    label.textContent = 'Slide ' + (i + 1);
    entry.appendChild(label);
    const body = document.createElement('div');
    body.innerHTML = slide.notes;
    entry.appendChild(body);
    list.appendChild(entry);
  });
}

// Make tasklist checkboxes interactive in presenter notes (no persistence).
function _makeTasklistsInteractivePres(root) {
  if (!root) root = document;
  root.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    try { cb.disabled = false; } catch (e) {}
    const li = cb.closest('li');
    if (li) li.classList.toggle('task-checked', cb.checked);
    cb.addEventListener('change', (e) => {
      const li = e.target.closest('li');
      if (li) li.classList.toggle('task-checked', e.target.checked);
    });
    if (li) {
      li.addEventListener('click', (ev) => {
        if (ev.target === cb) return;
        cb.checked = !cb.checked;
        cb.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }
  });
}

function render() {
  const slide = slides[current];
  const next = slides[current + 1];
  document.getElementById('pres-current-slide').innerHTML = slide.html;
  document.getElementById('pres-next-slide').innerHTML = next ? next.html : '<div class="end-marker">End of deck</div>';
  document.getElementById('pres-counter').textContent = (current + 1) + ' / ' + slides.length;
  document.querySelectorAll('pre code').forEach(el => hljs.highlightElement(el));

  // Update dimming
  document.querySelectorAll('.pres-notes-entry').forEach(entry => {
    const isCurrent = parseInt(entry.dataset.index) === current;
    entry.classList.toggle('dimmed', !isCurrent);
  });

  // Auto-scroll current entry into view
  const activeEntry = document.querySelector('.pres-notes-entry:not(.dimmed)');
  if (activeEntry) {
    activeEntry.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function startTimer() {
  if (timerInterval) return;
  timerInterval = setInterval(() => {
    timerSeconds++;
    const m = String(Math.floor(timerSeconds / 60)).padStart(2, '0');
    const s = String(timerSeconds % 60).padStart(2, '0');
    document.getElementById('pres-timer').textContent = m + ':' + s;
  }, 1000);
}
function pauseTimer() { clearInterval(timerInterval); timerInterval = null; }
function resetTimer() { pauseTimer(); timerSeconds = 0; document.getElementById('pres-timer').textContent = '00:00'; }

document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowRight' || e.key === 'j' || e.key === ' ') navigate(current + 1);
  if (e.key === 'ArrowLeft'  || e.key === 'k') navigate(current - 1);
  if (e.key === 't') window.open('/timer', '_blank');
});

buildNotesList();
render();
_makeTasklistsInteractivePres(document.getElementById('pres-notes-list'));
</script>
</body></html>
"""

TIMER_PAGE = _HEAD.format(title="Pitchfork — Timer") + """
<body class="view-timer">
<div id="timer-root" style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;gap:12px;padding:24px;">
  <div style="display:flex;gap:8px;align-items:center;">
    <div id="timer-display" tabindex="0" role="textbox" aria-label="Timer input" style="padding:8px;font-size:72px;text-align:center;font-weight:600;color:var(--pf-accent);outline:none;box-shadow:none;">00:00</div>
  </div>
  <div id="timer-controls" style="display:flex;gap:8px;">
    <button id="timer-start">Start</button>
    <button id="timer-pause">Pause</button>
    <button id="timer-reset">Reset</button>
  </div>
</div>

<script>
let timerSeconds = 0, timerInterval = null, initialSeconds = 0;
const display = document.getElementById('timer-display');
const btnStart = document.getElementById('timer-start');
const btnPause = document.getElementById('timer-pause');
const btnReset = document.getElementById('timer-reset');

let editBuffer = '';

function formatTime(s) {
  const m = String(Math.floor(s / 60)).padStart(2, '0');
  const sec = String(s % 60).padStart(2, '0');
  return m + ':' + sec;
}

function updateDisplay() { display.textContent = formatTime(timerSeconds); }

function parseTime(str) {
  str = (str || '').trim();
  if (!str) return 0;
  if (str.indexOf(':') !== -1) {
    const parts = str.split(':').map(p => p.trim());
    const m = parseInt(parts[0]) || 0;
    let s = parseInt(parts[1]) || 0;
    s = Math.max(0, Math.min(59, s));
    return m * 60 + s;
  }
  const m = parseInt(str) || 0;
  return m * 60;
}

function setTimerFromBuffer() {
  timerSeconds = parseTime(editBuffer);
  initialSeconds = timerSeconds;
  updateDisplay();
  display.style.color = '';
}

function setDisplayBuffer(buf) {
  editBuffer = (buf || '').trim();
  // show typed form: if no colon, display as minutes:00
  if (!editBuffer) {
    display.textContent = '00:00';
  } else if (editBuffer.indexOf(':') !== -1) {
    const parts = editBuffer.split(':');
    const m = parseInt(parts[0]) || 0;
    let s = parseInt(parts[1]) || 0;
    s = Math.max(0, Math.min(59, s));
    display.textContent = String(m) + ':' + String(s).padStart(2, '0');
  } else {
    const m = parseInt(editBuffer) || 0;
    display.textContent = String(m) + ':00';
  }
}

function startTimer() {
  if (timerSeconds <= 0) return;
  if (timerInterval) return;
  timerInterval = setInterval(() => {
    timerSeconds--;
    if (timerSeconds <= 0) {
      timerSeconds = 0;
      updateDisplay();
      clearInterval(timerInterval);
      timerInterval = null;
      display.style.color = 'hsla(0, 60%, 60%)';
      return;
    }
    updateDisplay();
  }, 1000);
}

function pauseTimer() { clearInterval(timerInterval); timerInterval = null; }

function resetTimer() { pauseTimer(); timerSeconds = initialSeconds || 0; updateDisplay(); document.body.style.backgroundColor = ''; }

btnStart.addEventListener('click', startTimer);
btnPause.addEventListener('click', pauseTimer);
btnReset.addEventListener('click', resetTimer);

// display keyboard input handling on the display itself
// document-level key handling for typing into the timer display
document.addEventListener('keydown', (e) => {
  // only handle simple keys: digits, colon, backspace, enter
  if (/^[0-9]$/.test(e.key)) {
    editBuffer += e.key;
    setDisplayBuffer(editBuffer);
    setTimerFromBuffer();
    e.preventDefault();
    return;
  }
  if (e.key === ':') {
    if (!editBuffer.includes(':')) editBuffer = (editBuffer || '0') + ':';
    setDisplayBuffer(editBuffer);
    e.preventDefault();
    return;
  }
  if (e.key === 'Backspace') {
    editBuffer = editBuffer.slice(0, -1);
    setDisplayBuffer(editBuffer);
    setTimerFromBuffer();
    e.preventDefault();
    return;
  }
  if (e.key === 'Enter') {
    setTimerFromBuffer();
    startTimer();
    e.preventDefault();
    return;
  }
});

// Enhanced parseTime to support 'XmYs' syntax (e.g., 5m30s, 5m, 100s, 50m30s)
function parseFlexibleTime(str) {
  str = (str || '').trim().toLowerCase();
  if (!str) return 0;
  let total = 0;
  // Match e.g. 5m30s, 100s, 5m, 50m30s
  const re = /^(?:(\d+)m)?(?:(\d+)s)?$/;
  const match = re.exec(str);
  if (match) {
    const m = match[1], s = match[2];
    if (m) total += parseInt(m, 10) * 60;
    if (s) total += parseInt(s, 10);
    if (total > 0) return total;
  }
  // fallback: try as integer seconds
  const asInt = parseInt(str, 10);
  if (!isNaN(asInt)) return asInt;
  return 0;
}

// override parseTime to use flexible parser
parseTime = parseFlexibleTime;

editBuffer = '';
if (typeof window.TIMER_DEFAULT_SECONDS === 'number' && !isNaN(window.TIMER_DEFAULT_SECONDS)) {
  timerSeconds = window.TIMER_DEFAULT_SECONDS;
} else {
  timerSeconds = 5 * 60;
}
initialSeconds = timerSeconds;
updateDisplay();
// autofocus removed: don't steal focus when timer is opened
</script>
</body></html>
"""
