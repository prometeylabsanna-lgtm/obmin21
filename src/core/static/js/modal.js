(function () {
  'use strict';

  var root = null;
  var lastFocus = null;

  function getRoot() {
    if (!root) root = document.getElementById('modal-root');
    return root;
  }

  function trapFocus(container) {
    var focusable = container.querySelectorAll(
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
    );
    if (!focusable.length) return;
    focusable[0].focus();
  }

  function openModal(url) {
    var el = getRoot();
    if (!el || !window.htmx) return;
    lastFocus = document.activeElement;
    el.hidden = false;
    document.documentElement.style.overflow = 'hidden';
    window.htmx.ajax('GET', url, { target: '#modal-root', swap: 'innerHTML' });
  }

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    if (evt.target && evt.target.id === 'modal-root') {
      trapFocus(evt.target);
    }
  });

  function closeModal() {
    var el = getRoot();
    if (!el) return;
    el.hidden = true;
    el.innerHTML = '';
    document.documentElement.style.overflow = '';
    if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus();
  }

  document.addEventListener('click', function (e) {
    var opener = e.target.closest('[data-open-modal]');
    if (opener) {
      e.preventDefault();
      openModal(opener.getAttribute('data-open-modal'));
      return;
    }
    if (e.target.closest('[data-close-modal]')) {
      e.preventDefault();
      closeModal();
      return;
    }
    var el = getRoot();
    if (el && !el.hidden && e.target === el) {
      closeModal();
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeModal();
  });

  window.Obmin21 = window.Obmin21 || {};
  window.Obmin21.openModal = openModal;
  window.Obmin21.closeModal = closeModal;
})();
