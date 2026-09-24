(function () {
  'use strict';

  function initAdvTabs() {
    document.querySelectorAll('[data-adv-tabs]').forEach(function (tabs) {
      var section = tabs.closest('section') || document;
      tabs.querySelectorAll('[data-adv-tab]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var key = btn.getAttribute('data-adv-tab');
          tabs.querySelectorAll('[data-adv-tab]').forEach(function (b) {
            b.classList.toggle('is-active', b === btn);
          });
          section.querySelectorAll('[data-adv-panel]').forEach(function (panel) {
            panel.hidden = panel.getAttribute('data-adv-panel') !== key;
          });
        });
      });
    });
  }

  document.addEventListener('DOMContentLoaded', initAdvTabs);
})();
