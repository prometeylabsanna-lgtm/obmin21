(function () {
  'use strict';

  var root = document.querySelector('[data-branches]');
  if (!root) return;

  var iframe = root.querySelector('[data-branches-map]');
  var nameEl = root.querySelector('[data-branches-name]');
  var addrEl = root.querySelector('[data-branches-addr]');
  var linkEl = root.querySelector('[data-branches-link]');
  var buttons = root.querySelectorAll('[data-branch]');
  var setCityUrl = root.getAttribute('data-set-city-url') || '/htmx/set-city/';
  var syncingFromHeader = false;

  function applyBranchUi(btn) {
    buttons.forEach(function (item) {
      item.classList.remove('is-active');
      item.setAttribute('aria-pressed', 'false');
    });
    btn.classList.add('is-active');
    btn.setAttribute('aria-pressed', 'true');
    var name = btn.getAttribute('data-name') || '';
    var addr = btn.getAttribute('data-addr') || '';
    var map = btn.getAttribute('data-map') || '';
    var link = btn.getAttribute('data-link') || '';
    if (iframe && map) {
      iframe.src = map;
      iframe.title = 'Карта: ' + addr;
    }
    if (nameEl) nameEl.textContent = 'Обмін21 · ' + name;
    if (addrEl) addrEl.textContent = addr;
    if (linkEl && link) linkEl.href = link;
  }

  function syncHeaderCity(btn) {
    var city = btn.getAttribute('data-city') || '';
    var branch = btn.getAttribute('data-branch-id') || '';
    if (!city || !window.htmx) return;
    window.htmx.ajax('POST', setCityUrl, {
      target: '#city-chrome',
      swap: 'outerHTML',
      values: { city: city, branch: branch },
    });
  }

  function findBranchButton(detail) {
    var branchId = detail.branchId != null ? String(detail.branchId) : '';
    var slug = detail.slug || '';
    var match = null;
    if (branchId) {
      buttons.forEach(function (btn) {
        if (btn.getAttribute('data-branch-id') === branchId) match = btn;
      });
    }
    if (!match && slug) {
      buttons.forEach(function (btn) {
        if (!match && btn.getAttribute('data-city') === slug) match = btn;
      });
    }
    return match;
  }

  buttons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (btn.classList.contains('is-active') && !syncingFromHeader) {
        return;
      }
      applyBranchUi(btn);
      if (!syncingFromHeader) syncHeaderCity(btn);
    });
  });

  document.body.addEventListener('cityChanged', function (evt) {
    var match = findBranchButton(evt.detail || {});
    if (!match || match.classList.contains('is-active')) return;
    syncingFromHeader = true;
    applyBranchUi(match);
    syncingFromHeader = false;
  });
})();
