(function () {
  'use strict';

  var fixedRafId = null;
  var sectionRafId = null;

  function initParallax() {
    if (fixedRafId !== null) {
      cancelAnimationFrame(fixedRafId);
      fixedRafId = null;
    }
    if (sectionRafId !== null) {
      cancelAnimationFrame(sectionRafId);
      sectionRafId = null;
    }

    document.querySelectorAll('.parallax-bg[data-bg]').forEach(function (el) {
      var url = el.getAttribute('data-bg');
      if (url) {
        el.style.backgroundImage = 'url("' + url + '")';
      }
    });

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }

    var fixedBgs = Array.prototype.slice.call(
      document.querySelectorAll('[data-parallax-fixed]')
    );

    if (fixedBgs.length) {
      var lastFixed = -1;

      function tickFixed() {
        var scrollY = window.scrollY || window.pageYOffset || 0;

        if (scrollY !== lastFixed) {
          lastFixed = scrollY;
          fixedBgs.forEach(function (bg) {
            var speed = parseFloat(bg.getAttribute('data-parallax-fixed-speed') || '0.12');
            bg.style.transform = 'translate3d(0, ' + (-scrollY * speed).toFixed(2) + 'px, 0)';
          });
        }

        fixedRafId = requestAnimationFrame(tickFixed);
      }

      fixedRafId = requestAnimationFrame(tickFixed);
    }

    var sections = Array.prototype.slice.call(
      document.querySelectorAll('[data-parallax]')
    );
    if (!sections.length) {
      return;
    }

    var lastScroll = -1;

    function tick() {
      var scrollY = window.scrollY || window.pageYOffset || 0;

      if (scrollY !== lastScroll) {
        lastScroll = scrollY;

        sections.forEach(function (section) {
          var bg = section.querySelector('[data-parallax-bg]');
          if (!bg) {
            return;
          }

          var rect = section.getBoundingClientRect();
          if (rect.bottom < -200 || rect.top > window.innerHeight + 200) {
            return;
          }

          var speed = parseFloat(section.getAttribute('data-parallax-speed') || '0.3');
          var sectionMid = rect.top + rect.height / 2;
          var viewportMid = window.innerHeight / 2;
          var offset = (sectionMid - viewportMid) * speed;

          bg.style.transform = 'translate3d(0, ' + offset.toFixed(2) + 'px, 0)';
        });
      }

      sectionRafId = requestAnimationFrame(tick);
    }

    sectionRafId = requestAnimationFrame(tick);
  }

  window.Obmin21 = window.Obmin21 || {};
  window.Obmin21.initParallax = initParallax;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initParallax);
  } else {
    initParallax();
  }
})();
