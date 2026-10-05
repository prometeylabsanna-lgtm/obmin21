(function () {
  'use strict';

  var root = document.querySelector('[data-chat]');
  if (!root) return;

  var toggle = root.querySelector('[data-chat-toggle]');
  var closeBtn = root.querySelector('[data-chat-close]');
  var panel = document.getElementById('site-chat-panel');
  var log = root.querySelector('[data-chat-log]');
  var form = root.querySelector('[data-chat-form]');
  var input = root.querySelector('[data-chat-input]');
  var cbForm = root.querySelector('[data-chat-cb-form]');
  var cbData = root.querySelector('[data-chat-cb-data]');
  var cbLabel = root.querySelector('[data-chat-cb-label]');
  var loaded = false;

  function scrollLog() {
    if (!log) return;
    log.scrollTop = log.scrollHeight;
  }

  function setOpen(open) {
    root.classList.toggle('is-open', open);
    document.body.classList.toggle('chat-open', open);
    if (panel) panel.hidden = !open;
    if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) {
      loadLog();
      window.setTimeout(function () {
        if (input) input.focus();
        scrollLog();
      }, 50);
    }
  }

  function loadLog() {
    if (loaded || !log) return;
    var url = log.getAttribute('hx-get');
    if (!url) return;
    loaded = true;
    fetch(url, {
      credentials: 'same-origin',
      headers: { 'HX-Request': 'true' },
    })
      .then(function (response) { return response.text(); })
      .then(function (html) {
        log.innerHTML = html;
        scrollLog();
      })
      .catch(function () {
        loaded = false;
      });
  }

  if (toggle) {
    toggle.addEventListener('click', function () {
      setOpen(true);
    });
  }
  if (closeBtn) {
    closeBtn.addEventListener('click', function () {
      setOpen(false);
    });
  }

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && root.classList.contains('is-open')) {
      setOpen(false);
    }
  });

  if (form) {
    form.addEventListener('htmx:afterRequest', function () {
      if (input) input.value = '';
      scrollLog();
    });
  }
  if (cbForm) {
    cbForm.addEventListener('htmx:afterRequest', scrollLog);
  }
  if (log) {
    log.addEventListener('htmx:afterSwap', scrollLog);
  }

  root.addEventListener('click', function (event) {
    var chip = event.target.closest('[data-chat-cb]');
    if (!chip || !cbForm || !window.htmx) return;
    cbData.value = chip.getAttribute('data-chat-cb') || '';
    cbLabel.value = chip.getAttribute('data-chat-label') || chip.textContent.trim();
    cbForm.requestSubmit();
  });

  function syncViewport() {
    if (!window.visualViewport) return;
    document.documentElement.style.setProperty(
      '--chat-vvh',
      window.visualViewport.height + 'px'
    );
  }
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', syncViewport);
    syncViewport();
  }
})();
