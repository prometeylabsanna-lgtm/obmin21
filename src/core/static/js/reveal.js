(function () {
  'use strict';

  var observer = null;

  function autoMarkReveals() {
    var selectors = [
      '.page__main > .section',
      '.page__main > .cta-block',
      '.page__main > .banner-slot',
      '.page__main .section__head',
      '.page__main .card-grid',
      '.page__main .adv-list',
      '.page__main .seo-block',
      '.page__main .form',
      '.page__main .branch-list'
    ];

    var nodes = document.querySelectorAll(selectors.join(','));
    var index = 0;

    nodes.forEach(function (el) {
      if (el.classList.contains('reveal')) {
        return;
      }
      /* Курси залишаємо видимими одразу — для анімації цифр */
      if (el.id === 'exchange') {
        return;
      }
      el.classList.add('reveal', 'reveal--up');
      if (!el.hasAttribute('data-reveal-delay')) {
        var delay = Math.min(index * 40, 160);
        if (delay > 0) {
          el.setAttribute('data-reveal-delay', String(delay));
        }
      }
      index += 1;
    });

    document.querySelectorAll('.page__main .card:not(.reveal)').forEach(function (card, i) {
      card.classList.add('reveal', 'reveal--up', 'hover-lift');
      card.setAttribute('data-reveal-delay', String(Math.min(i * 40, 160)));
    });

    document.querySelectorAll('.link-accent:not(.hover-underline)').forEach(function (link) {
      link.classList.add('hover-underline');
    });
  }

  function initReveal() {
    if (observer) {
      observer.disconnect();
      observer = null;
    }

    autoMarkReveals();

    var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      document.querySelectorAll('.reveal').forEach(function (el) {
        el.classList.add('is-visible');
      });
      return;
    }

    observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.06 }
    );

    document.querySelectorAll('.reveal').forEach(function (el) {
      var delay = el.getAttribute('data-reveal-delay');
      if (delay) {
        el.style.setProperty('--reveal-delay', delay + 'ms');
      }
      observer.observe(el);
    });
  }

  window.Obmin21 = window.Obmin21 || {};
  window.Obmin21.initReveal = initReveal;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initReveal);
  } else {
    initReveal();
  }

  document.body.addEventListener('htmx:afterSwap', function () {
    initReveal();
  });
})();
