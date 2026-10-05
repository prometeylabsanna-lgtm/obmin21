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

  document.body.addEventListener('cityChanged', function (evt) {
    var detail = evt.detail || {};
    var panel = document.getElementById('rates-panel');
    if (panel && window.htmx) {
      var parts = [];
      if (panel.closest('.hero__rates')) parts.push('home=1');
      if (panel.closest('.rates-page-card')) parts.push('hide_full=1');
      var tab = panel.querySelector('.rates-tabs__btn.is-active');
      if (tab) {
        var qa = tab.getAttribute('data-qa') || '';
        var board = qa.replace('rates-tab-', '');
        if (board) parts.push('board=' + encodeURIComponent(board));
      }
      var qs = parts.length ? '?' + parts.join('&') : '';
      window.htmx.ajax('GET', '/partials/rates/' + qs, { target: '#rates-panel', swap: 'outerHTML' });
    }
    if (window.Obmin21 && typeof window.Obmin21.syncQuotes === 'function') {
      window.Obmin21.syncQuotes();
    }
    var nameIn = detail.nameIn || '';
    if (nameIn) {
      document.querySelectorAll('[data-city-in]').forEach(function (el) {
        el.textContent = nameIn;
      });
    }
    var banner = document.querySelector('[data-hero-banner]');
    if (banner) {
      if (detail.bannerUrl) {
        banner.src = detail.bannerUrl;
      } else if (detail.slug) {
        var prefix = banner.getAttribute('data-static-prefix') || '/static/';
        var next = prefix + 'images/hero-' + detail.slug + '.jpg';
        banner.onerror = function () {
          banner.onerror = null;
          banner.src = banner.getAttribute('data-hero-fallback') || '/static/images/hero-kyiv.jpg';
        };
        banner.src = next;
      }
    }
    if (detail.bannerTitle) {
      document.querySelectorAll('[data-hero-title]').forEach(function (el) {
        el.textContent = detail.bannerTitle;
      });
    }
    if (detail.bannerSuffix) {
      document.querySelectorAll('[data-hero-suffix]').forEach(function (el) {
        el.textContent = detail.bannerSuffix;
      });
    }
    if (detail.bannerText) {
      document.querySelectorAll('[data-hero-lead]').forEach(function (el) {
        el.textContent = detail.bannerText;
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
