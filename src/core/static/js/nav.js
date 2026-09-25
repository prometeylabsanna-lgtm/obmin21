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
    var drawer = document.querySelector('[data-menu-drawer]');
    if (!drawer) return;

    function getToggle() {
      return document.querySelector('[data-menu-toggle]');
    }

    function openMenu() {
      var toggle = getToggle();
      drawer.classList.add('is-open');
      drawer.removeAttribute('hidden');
      drawer.setAttribute('aria-hidden', 'false');
      if (toggle) toggle.setAttribute('aria-expanded', 'true');
      document.documentElement.classList.add('is-menu-open');
      var closeBtn = drawer.querySelector('[data-menu-close]');
      if (closeBtn) closeBtn.focus();
    }

    function closeMenu() {
      var toggle = getToggle();
      drawer.classList.remove('is-open');
      drawer.setAttribute('hidden', '');
      drawer.setAttribute('aria-hidden', 'true');
      if (toggle) toggle.setAttribute('aria-expanded', 'false');
      document.documentElement.classList.remove('is-menu-open');
      if (toggle) toggle.focus();
    }

    function isOpen() {
      return drawer.classList.contains('is-open');
    }

    document.addEventListener('click', function (e) {
      var toggle = e.target.closest('[data-menu-toggle]');
      if (toggle) {
        e.preventDefault();
        if (isOpen()) closeMenu();
        else openMenu();
        return;
      }
      if (e.target.closest('[data-menu-close]')) {
        e.preventDefault();
        closeMenu();
      }
    });

    drawer.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', closeMenu);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && isOpen()) closeMenu();
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
    var label = document.querySelector('[data-city-label]');
    var cityName = label ? label.textContent.trim() : '';
    if (cityName) {
      document.querySelectorAll('[data-live-city-name]').forEach(function (el) {
        el.textContent = cityName;
      });
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
