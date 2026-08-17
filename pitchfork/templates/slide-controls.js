// slide-controls.js — navigation & helpers shared by slides.html and
// notes.html. Each page defines its own `slides`, `chapters`, `current`,
// `step`, and `ws`, plus a `render(movedSlide)` that skips rebuilding slide
// content when `movedSlide` is false (a `--` reveal within the same slide);
// the functions here only reference those globals when called, so load order
// relative to this file doesn't matter.

function maxStep(idx) {
  const slide = slides[idx];
  return (slide && slide.steps) || 0;
}

let ws;
// Set right before a reload we triggered ourselves, so pages with a
// beforeunload handler (e.g. closing spawned popups) can tell it apart from
// the user actually navigating away.
let _reloading = false;

// Opens the websocket and wires up the two message types every view handles
// the same way: a remote navigate to stay in sync, and a reload broadcast
// (deck/CSS/asset changed) to refresh in place.
function initSocket() {
  ws = new WebSocket(`ws://${location.hostname}:__WS_PORT__`);
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'navigate') applyRemoteNavigate(msg.index, msg.step);
    if (msg.type === 'reload') { _reloading = true; location.hash = '#' + current; location.reload(); }
  };
}

function broadcastPosition() {
  ws.send(JSON.stringify({ type: 'navigate', index: current, step: step }));
}

// wantStep may be a number, or 'last' to land on a slide fully revealed (what
// you want stepping backwards into it, or jumping to it from another view).
function goTo(idx, wantStep) {
  const clamped = Math.max(0, Math.min(slides.length - 1, idx));
  const movedSlide = clamped !== current;
  current = clamped;
  const target = wantStep === 'last' ? maxStep(current) : (wantStep || 0);
  step = Math.max(0, Math.min(maxStep(current), target));
  render(movedSlide);
  broadcastPosition();
}

// Jumping to a slide from a thumbnail, chapter menu, etc. starts it unrevealed.
function navigate(idx) {
  goTo(idx, 0);
}

// Applies a navigate message received from another connected view, without
// re-broadcasting it back out.
function applyRemoteNavigate(idx, msgStep) {
  const movedSlide = idx !== current;
  current = idx;
  step = msgStep || 0;
  render(movedSlide);
}

function advance() {
  if (step < maxStep(current)) goTo(current, step + 1);
  else if (current < slides.length - 1) goTo(current + 1, 0);
  // else: already on the last step of the last slide, stay put
}

function retreat() {
  if (step > 0) goTo(current, step - 1);
  else if (current > 0) goTo(current - 1, 'last');
}

function currentChapterIndex() {
  let idx = -1;
  for (let i = 0; i < chapters.length; i++) {
    if (chapters[i].index <= current) idx = i;
    else break;
  }
  return idx;
}

function currentChapterTitle() {
  const idx = currentChapterIndex();
  return idx >= 0 ? chapters[idx].title : null;
}

// Nasty nasty nasty nasty nasty listener because PyMdown doesn't want to structure `<label><input></label>` correctly and also doesn't emit `label for`
function _makeTasklistsInteractive(root) {
  if (!root) root = document;
  root.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    const li = cb.closest('li');
    if (li) {
      li.addEventListener('click', (ev) => {
        if (ev.target === cb) return;
        cb.checked = !cb.checked;
        cb.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }
  });
}