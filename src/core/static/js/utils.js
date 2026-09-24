(function () {
  'use strict';

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  document.body.addEventListener('htmx:configRequest', function (event) {
    event.detail.headers['X-CSRFToken'] = getCsrfToken();
  });

  window.Obmin21 = window.Obmin21 || {};
  window.Obmin21.getCsrfToken = getCsrfToken;
})();
