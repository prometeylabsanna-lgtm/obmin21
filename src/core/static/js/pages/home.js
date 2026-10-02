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
        var card = track.querySelector('.review-slide, .article-slide');
        return card ? card.getBoundingClientRect().width + 20 : 300;
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

  document.addEventListener('DOMContentLoaded', function () {
    initFaq();
    initSliders();
  });
})();
