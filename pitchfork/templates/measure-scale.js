() => {
    const slide = document.querySelector('.export-slide');
    if (!slide) return 1.0;
    const inner = slide.querySelector('.slide-layout') || slide;

    // Release pre elements from flex/scroll containment so their full height is measurable.
    inner.querySelectorAll('pre').forEach(p => {
        p.style.overflow = 'visible';
        p.style.maxHeight = 'none';
        p.style.flex = 'none';
        p.style.height = 'auto';
        p.style.whiteSpace = 'pre-wrap';
        p.style.wordBreak = 'break-word';
    });

    // Temporarily make overflow visible so scrollWidth/scrollHeight reflect true content size.
    const prevSlide = slide.style.overflow;
    const prevInner = inner.style.overflow;
    slide.style.overflow = 'visible';
    inner.style.overflow = 'visible';

    const scaleW = slide.clientWidth  / inner.scrollWidth;
    const scaleH = slide.clientHeight / inner.scrollHeight;

    slide.style.overflow = prevSlide;
    inner.style.overflow = prevInner;

    const fit = Math.min(1.0, scaleW, scaleH);
    // Ignore sub-pixel rounding differences.
    return fit >= 0.98 ? 1.0 : Math.max(fit, 0.1);
}
