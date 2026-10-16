(function () {
  'use strict';

  function initFaq() {
    document.querySelectorAll('[data-faq]').forEach(function (list) {
      list.querySelectorAll('.faq-card__q, .faq-item__q').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var item = btn.closest('.faq-card, .faq-item');
          if (!item) return;
          var open = item.classList.contains('is-open');
          list.querySelectorAll('.faq-card, .faq-item').forEach(function (el) {
            el.classList.remove('is-open');
            var q = el.querySelector('.faq-card__q, .faq-item__q');
            if (q) q.setAttribute('aria-expanded', 'false');
          });
          if (!open) {
            item.classList.add('is-open');
            btn.setAttribute('aria-expanded', 'true');
          }
        });
      });
    });
  }

  function initSliders() {
    document.querySelectorAll('[data-slider-nav]').forEach(function (nav) {
      var name = nav.getAttribute('data-slider-nav');
      var track = document.querySelector('[data-slider="' + name + '"]');
      if (!track) return;
      var prev = nav.querySelector('[data-slider-prev]');
      var next = nav.querySelector('[data-slider-next]');

      function step() {
        var card = track.querySelector('.review-slide, .article-slide, .svc-card');
        if (!card) return 300;
        var gap = parseFloat(window.getComputedStyle(track).columnGap) || 20;
        return card.getBoundingClientRect().width + gap;
      }

      function sync() {
        var max = track.scrollWidth - track.clientWidth - 4;
        if (prev) prev.classList.toggle('is-active', track.scrollLeft > 8);
        if (next) next.classList.toggle('is-active', track.scrollLeft < max);
      }

      if (prev) {
        prev.addEventListener('click', function () {
          track.scrollBy({ left: -step(), behavior: 'smooth' });
        });
      }
      if (next) {
        next.addEventListener('click', function () {
          track.scrollBy({ left: step(), behavior: 'smooth' });
        });
      }
      track.addEventListener('scroll', sync, { passive: true });
      sync();
    });
  }

  function initPromo() {
    var root = document.querySelector('[data-promo]');
    if (!root) return;
    var slides = Array.prototype.slice.call(root.querySelectorAll('[data-promo-slide]'));
    var dots = Array.prototype.slice.call(root.querySelectorAll('[data-promo-dot]'));
    if (!slides.length) return;
    var index = 0;
    var timer = 0;

    function show(next) {
      index = (next + slides.length) % slides.length;
      slides.forEach(function (slide, i) {
        slide.classList.toggle('is-active', i === index);
      });
      dots.forEach(function (dot, i) {
        dot.classList.toggle('is-active', i === index);
        dot.setAttribute('aria-current', i === index ? 'true' : 'false');
      });
    }

    function start() {
      window.clearInterval(timer);
      timer = window.setInterval(function () {
        if (document.hidden || root.dataset.pause === '1') return;
        show(index + 1);
      }, 5000);
    }

    dots.forEach(function (dot, i) {
      dot.addEventListener('click', function (event) {
        event.stopPropagation();
        show(i);
        start();
      });
    });

    root.addEventListener('click', function (event) {
      if (window.innerWidth >= 768) return;
      if (event.target.closest('a, button, [data-promo-dot]')) return;
      var slide = slides[index];
      if (!slide) return;
      if (slide.getAttribute('data-modal') === '1') {
        var opener = slide.querySelector('[data-open-modal]');
        if (opener) opener.click();
        return;
      }
      var href = slide.getAttribute('data-href');
      if (!href) return;
      if (slide.getAttribute('data-blank') === '1') {
        window.open(href, '_blank', 'noopener');
      } else {
        window.location.href = href;
      }
    });

    root.addEventListener('mouseenter', function () {
      root.dataset.pause = '1';
    });
    root.addEventListener('mouseleave', function () {
      delete root.dataset.pause;
    });
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) start();
    });
    show(0);
    start();
  }

  document.addEventListener('DOMContentLoaded', function () {
    initFaq();
    initSliders();
    initPromo();
  });
})();
