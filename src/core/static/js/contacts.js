(function () {
  'use strict';

  var root = document.querySelector('[data-branches]');
  if (!root) return;

  var iframe = root.querySelector('[data-branches-map]');
  var nameEl = root.querySelector('[data-branches-name]');
  var addrEl = root.querySelector('[data-branches-addr]');
  var linkEl = root.querySelector('[data-branches-link]');
  var buttons = root.querySelectorAll('[data-branch]');

  buttons.forEach(function (btn) {
    btn.addEventListener('click', function () {
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
    });
  });
})();
