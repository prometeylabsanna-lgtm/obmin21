(function () {
  'use strict';

  var root = null;
  var lastFocus = null;
  var scrollY = 0;

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

  function lockScroll() {
    scrollY = window.scrollY || window.pageYOffset || 0;
    document.documentElement.style.overflow = 'hidden';
    document.body.style.overflow = 'hidden';
    document.body.style.position = 'fixed';
    document.body.style.top = '-' + scrollY + 'px';
    document.body.style.left = '0';
    document.body.style.right = '0';
    document.body.style.width = '100%';
  }

  function unlockScroll() {
    document.documentElement.style.overflow = '';
    document.body.style.overflow = '';
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.left = '';
    document.body.style.right = '';
    document.body.style.width = '';
    window.scrollTo(0, scrollY);
  }

  function openModal(url) {
    var el = getRoot();
    if (!el || !window.htmx) return;
    lastFocus = document.activeElement;
    el.hidden = false;
    lockScroll();
    window.htmx.ajax('GET', url, { target: '#modal-root', swap: 'innerHTML' });
  }

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    if (evt.target && evt.target.id === 'modal-root') {
      trapFocus(evt.target);
      syncModalOverflow(evt.target);
    }
  });

  function syncModalOverflow(el) {
    if (!el) return;
    // Phantom scroll: only allow overflow when content actually exceeds viewport
    el.style.overflowY = 'hidden';
    requestAnimationFrame(function () {
      var needsScroll = el.scrollHeight > el.clientHeight + 1;
      el.style.overflowY = needsScroll ? 'auto' : 'hidden';
    });
  }

  function closeModal() {
    var el = getRoot();
    if (!el) return;
    el.hidden = true;
    el.innerHTML = '';
    el.style.overflowY = '';
    unlockScroll();
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
