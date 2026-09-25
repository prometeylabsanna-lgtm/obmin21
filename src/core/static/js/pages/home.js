(function () {
  'use strict';

  function initAdvTabs() {
    document.querySelectorAll('[data-adv-tabs]').forEach(function (tabsRoot) {
      var section = tabsRoot.closest('section') || document;
      tabsRoot.querySelectorAll('[data-adv-tab]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var key = btn.getAttribute('data-adv-tab');
          tabsRoot.querySelectorAll('[data-adv-tab]').forEach(function (b) {
            var active = b === btn;
            b.classList.toggle('is-active', active);
            b.setAttribute('aria-selected', active ? 'true' : 'false');
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
