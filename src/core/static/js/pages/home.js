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
      if (nav.getAttribute('data-slider-bound') === '1') return;
      var name = nav.getAttribute('data-slider-nav');
      if (!name) return;
      var track = document.querySelector('[data-slider="' + name + '"]');
      if (!track) return;
      nav.setAttribute('data-slider-bound', '1');

      var prev = nav.querySelector('[data-slider-prev]');
      var next = nav.querySelector('[data-slider-next]');

      function step() {
        var card = track.querySelector('.review-slide, .article-slide, .svc-card');
        if (!card) return 300;
        var styles = window.getComputedStyle(track);
        var gap = parseFloat(styles.columnGap);
        if (!(gap >= 0)) gap = parseFloat(styles.gap);
        if (!(gap >= 0)) gap = 0;
        return card.getBoundingClientRect().width + gap;
      }

      function maxScroll() {
        var layoutMax = Math.max(0, track.scrollWidth - track.clientWidth);
        if (track.getAttribute('data-slider') !== 'articles') return layoutMax;
        var cards = track.querySelectorAll('.article-slide');
        if (!cards.length) return layoutMax;
        var last = cards[cards.length - 1];
        if (last.offsetParent !== track) return layoutMax;
        var padRight = parseFloat(window.getComputedStyle(track).paddingRight) || 0;
        var contentMax = last.offsetLeft + last.offsetWidth + padRight - track.clientWidth;
        if (!(contentMax >= 0)) contentMax = 0;
        return Math.min(layoutMax, contentMax);
      }

      function go(dir) {
        var max = maxScroll();
        var size = step();
        if (!(size > 0)) return;
        var index = Math.round(track.scrollLeft / size) + dir;
        var maxIndex = Math.max(0, Math.round(max / size));
        if (index < 0) index = 0;
        if (index > maxIndex) index = maxIndex;
        track.scrollTo({
          left: Math.min(max, Math.max(0, index * size)),
          behavior: 'smooth'
        });
      }

      if (prev) {
        prev.addEventListener('click', function () {
          go(-1);
        });
      }
      if (next) {
        next.addEventListener('click', function () {
          go(1);
        });
      }

      if (track.getAttribute('data-slider-bound') === '1') return;
      track.setAttribute('data-slider-bound', '1');

      function sync() {
        var limit = Math.max(0, maxScroll() - 4);
        document.querySelectorAll('[data-slider-nav="' + name + '"]').forEach(function (item) {
          var prevBtn = item.querySelector('[data-slider-prev]');
          var nextBtn = item.querySelector('[data-slider-next]');
          if (prevBtn) prevBtn.classList.toggle('is-active', track.scrollLeft > 8);
          if (nextBtn) nextBtn.classList.toggle('is-active', track.scrollLeft < limit);
        });
      }

      var endTimer = 0;
      function clampToMax() {
        var max = maxScroll();
        if (track.scrollLeft > max) {
          track.scrollTo({ left: max, behavior: 'auto' });
        }
      }

      track.addEventListener('scroll', function () {
        sync();
        window.clearTimeout(endTimer);
        endTimer = window.setTimeout(clampToMax, 120);
      }, { passive: true });

      if ('onscrollend' in window) {
        track.addEventListener('scrollend', function () {
          window.clearTimeout(endTimer);
          clampToMax();
          sync();
        }, { passive: true });
      }

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

    function autoplayOn() {
      if (root.getAttribute('data-autoplay') === '0') return false;
      if (root.getAttribute('data-slides') === '1') return false;
      return slides.length > 1;
    }

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
      if (!autoplayOn()) return;
      timer = window.setInterval(function () {
        if (document.hidden || root.dataset.pause === '1') return;
        show(index + 1);
      }, 4000);
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
