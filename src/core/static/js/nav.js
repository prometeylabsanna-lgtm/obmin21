(function () {
  'use strict';

  function initCitySelect(root) {
    var scope = root || document;
    scope.querySelectorAll('[data-city-select]').forEach(function (wrap) {
      var toggle = wrap.querySelector('[data-city-toggle]');
      var menu = wrap.querySelector('[data-city-menu]');
      if (!toggle || !menu) return;
      toggle.addEventListener('click', function (e) {
        e.stopPropagation();
        var open = menu.hasAttribute('hidden');
        menu.toggleAttribute('hidden', !open);
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    });
  }

  function initMenu() {
    var toggle = document.querySelector('[data-menu-toggle]');
    var drawer = document.querySelector('[data-menu-drawer]');
    if (!toggle || !drawer) return;
    toggle.addEventListener('click', function () {
      drawer.classList.toggle('is-open');
    });
  }

  function initScrollspy() {
    var links = Array.prototype.slice.call(document.querySelectorAll('[data-anchor]'));
    if (!links.length) return;
    var map = {};
    links.forEach(function (link) {
      var id = link.getAttribute('data-anchor');
      var el = document.getElementById(id);
      if (el) map[id] = { link: link, el: el };
    });
    var ids = Object.keys(map);
    if (!ids.length) return;

    function setActive(id) {
      links.forEach(function (l) {
        l.classList.toggle('is-active', l.getAttribute('data-anchor') === id);
      });
    }

    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) setActive(entry.target.id);
        });
      }, { rootMargin: '-40% 0px -50% 0px', threshold: 0.01 });
      ids.forEach(function (id) { io.observe(map[id].el); });
    }
  }

  document.addEventListener('click', function (e) {
    if (!e.target.closest('[data-city-select]')) {
      document.querySelectorAll('[data-city-menu]').forEach(function (menu) {
        menu.setAttribute('hidden', '');
      });
    }
  });

  document.body.addEventListener('cityChanged', function () {
    var panel = document.getElementById('rates-panel');
    if (panel && window.htmx) {
      window.htmx.ajax('GET', '/partials/rates/', { target: '#rates-panel', swap: 'outerHTML' });
    }
    var branches = document.getElementById('branch-list');
    if (branches) {
      window.location.reload();
    }
  });

  document.addEventListener('DOMContentLoaded', function () {
    initCitySelect();
    initMenu();
    initScrollspy();
  });

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    if (evt.target && evt.target.id === 'city-chrome') {
      initCitySelect(evt.target);
    }
  });
})();
