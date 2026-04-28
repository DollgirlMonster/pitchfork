(function(){
  const slides = Array.from(document.querySelectorAll('.export-slide'));
  const counter = document.getElementById('slide-counter');
  let idx = 0;
  const show = i => {
    idx = ((i % slides.length) + slides.length) % slides.length;
    slides.forEach((s, n) => s.classList.toggle('active', n === idx));
    if (counter) counter.textContent = `${idx + 1} / ${slides.length}`;
    window.scrollTo(0, 0);
  };
  document.addEventListener('keydown', e => {
    if (e.target.matches('input,textarea')) return;
    if (['ArrowRight','ArrowDown','PageDown',' '].includes(e.key))  { e.preventDefault(); show(idx + 1); }
    if (['ArrowLeft','ArrowUp','PageUp','Backspace'].includes(e.key)) { e.preventDefault(); show(idx - 1); }
  });
  show(0);
})();
