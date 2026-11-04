/* Мобільна підміна довгих input у change-form на textarea з автовисотою.
   На >=768px скрипт не змінює DOM. */
(function () {
  var MQ = '(max-width: 767px)';
  /* Назви міст (max_length=80) теж кліпаються; без maxlength підміна лишається. */
  var LONG_TEXT_MIN = 50;
  var supportsFieldSizing = !!(window.CSS && CSS.supports && CSS.supports('field-sizing', 'content'));
  var inputValue = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
  var textareaValue = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
  var COPY_ATTRS = [
    'maxlength', 'minlength', 'placeholder', 'required', 'disabled', 'readonly',
    'inputmode', 'autocomplete', 'autocapitalize', 'autocorrect', 'spellcheck',
    'title', 'enterkeyhint', 'lang', 'dir', 'form'
  ];
  var active = false;
  var mobile = false;
  var pairs = [];
  var cleanups = [];
  var fitted = [];
  var bound = new WeakSet();
  var observer = null;
  var io = null;
  var seq = 0;
  var notifying = false;
  var mq = null;

  function sanitize(value) {
    return String(value == null ? '' : value).replace(/\r\n|\r|\n|\u2028|\u2029/g, ' ');
  }

  function limit(input, value) {
    if (!input.hasAttribute('maxlength')) return value;
    var max = parseInt(input.getAttribute('maxlength'), 10);
    if (isNaN(max) || max < 0 || value.length <= max) return value;
    return value.slice(0, max);
  }

  function inTemplate(el) {
    if (el.closest && el.closest('.empty-form')) return true;
    var name = el.getAttribute('name') || '';
    var id = el.id || '';
    return name.indexOf('__prefix__') !== -1 || id.indexOf('__prefix__') !== -1;
  }

  function isDateTime(input) {
    if (input.classList.contains('vDateField') || input.classList.contains('vTimeField')) return true;
    var type = (input.getAttribute('type') || '').toLowerCase();
    return type === 'date' || type === 'time' || type === 'datetime-local' || type === 'month' || type === 'week';
  }

  function isAutocomplete(input) {
    if (input.closest('.select2-container, .select2-dropdown, .select2-search, .ts-wrapper, .selector, .autocomplete-light-widget, .ui-autocomplete')) {
      return true;
    }
    var cls = typeof input.className === 'string' ? input.className : '';
    if (/select2|autocomplete/i.test(cls)) return true;
    if (input.getAttribute('role') === 'combobox') return true;
    if (input.hasAttribute('list')) return true;
    if (input.hasAttribute('data-autocomplete-light-function') || input.hasAttribute('data-select2-id')) return true;
    return false;
  }

  function isLongText(input) {
    if (!input.hasAttribute('maxlength')) return true;
    var max = parseInt(input.getAttribute('maxlength'), 10);
    if (isNaN(max)) return true;
    return max >= LONG_TEXT_MIN;
  }

  function isShown(el) {
    if (!el || !document.contains(el)) return false;
    var node = el;
    while (node && node !== document.body) {
      if (node.hidden) return false;
      var style = window.getComputedStyle(node);
      if (style.display === 'none' || style.visibility === 'hidden') return false;
      node = node.parentElement;
    }
    return true;
  }

  /* style.height — лише fallback, коли field-sizing: content не підтримується
     (старіший WebKit/Safari). Якщо CSS.supports('field-sizing', 'content') істинний,
     висоту не чіпаємо: її задає CSS. */
  function fit(el) {
    if (!el || supportsFieldSizing || !mobile) return;
    if (!document.contains(el) || el.getClientRects().length === 0) return;
    var style = window.getComputedStyle(el);
    var border = (parseFloat(style.borderTopWidth) || 0) + (parseFloat(style.borderBottomWidth) || 0);
    el.style.height = '0px';
    var next = Math.ceil(el.scrollHeight + border) + 'px';
    el.style.height = next;
    if (fitted.indexOf(el) === -1) fitted.push(el);
  }

  function refitAll() {
    if (!mobile || supportsFieldSizing) return;
    var nodes = document.querySelectorAll('body.change-form form[id$="_form"] textarea');
    for (var i = 0; i < nodes.length; i++) {
      if (!skipTextarea(nodes[i])) fit(nodes[i]);
    }
  }

  function listen(target, type, fn, options) {
    target.addEventListener(type, fn, options || false);
    var opts = options || false;
    cleanups.push(function () {
      target.removeEventListener(type, fn, opts);
    });
  }

  function skipTextarea(el) {
    if (el.classList.contains('mobile-field-proxy')) return false;
    if (inTemplate(el)) return true;
    if (el.closest('.jsoneditor, .ace_editor, .CodeMirror, .cm-editor, .tox-tinymce, .trix-editor, .select2-container')) {
      return true;
    }
    return false;
  }

  function bindTextarea(el) {
    if (skipTextarea(el) || bound.has(el)) return;
    bound.add(el);
    if (supportsFieldSizing) return;
    fit(el);
    listen(el, 'input', function () { fit(el); });
    if (io) io.observe(el);
  }

  function readProxy(proxy) {
    return textareaValue.get.call(proxy);
  }

  function writeProxy(proxy, value) {
    if (readProxy(proxy) === value) return;
    var start = proxy.selectionStart;
    var end = proxy.selectionEnd;
    var previous = readProxy(proxy);
    textareaValue.set.call(proxy, value);
    var delta = previous.length - value.length;
    try {
      proxy.setSelectionRange(Math.max(0, (start || 0) - delta), Math.max(0, (end || 0) - delta));
    } catch (err) {}
  }

  function syncToOriginal(pair, notify) {
    var clean = limit(pair.original, sanitize(readProxy(pair.proxy)));
    if (readProxy(pair.proxy) !== clean) writeProxy(pair.proxy, clean);
    if (inputValue.get.call(pair.original) !== clean) {
      inputValue.set.call(pair.original, clean);
    }
    if (notify) {
      notifying = true;
      pair.original.dispatchEvent(new Event('input', { bubbles: true }));
      pair.original.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
      notifying = false;
    }
    fit(pair.proxy);
  }

  function pullFromOriginal(pair) {
    if (notifying || !pair.proxy) return;
    var clean = limit(pair.original, sanitize(inputValue.get.call(pair.original)));
    if (readProxy(pair.proxy) !== clean) {
      textareaValue.set.call(pair.proxy, clean);
      fit(pair.proxy);
    }
  }

  function proxyInput(input) {
    if (!input || input.tagName !== 'INPUT' || bound.has(input) || !inputValue || !textareaValue) return;
    var typeAttr = input.getAttribute('type');
    var type = typeAttr === null || typeAttr === '' ? 'text' : typeAttr.toLowerCase();
    if (type !== 'text') return;
    if (input.readOnly || input.hasAttribute('readonly')) return;
    if (input.classList.contains('vForeignKeyRawIdAdminField') || input.classList.contains('vManyToManyRawIdAdminField')) return;
    if (!isLongText(input) || inTemplate(input) || isDateTime(input) || isAutocomplete(input)) return;
    if (!input.closest('form[id$="_form"]')) return;

    bound.add(input);
    seq += 1;
    var proxy = document.createElement('textarea');
    proxy.className = input.className;
    proxy.classList.add('mobile-field-proxy');
    proxy.rows = 1;
    var sourceId = input.id || '';
    if (sourceId) {
      proxy.id = sourceId;
      input.id = sourceId + '-source';
    } else {
      proxy.id = 'mobile-field-' + seq;
    }
    var a;
    for (a = 0; a < COPY_ATTRS.length; a++) {
      if (input.hasAttribute(COPY_ATTRS[a])) proxy.setAttribute(COPY_ATTRS[a], input.getAttribute(COPY_ATTRS[a]));
    }
    for (a = 0; a < input.attributes.length; a++) {
      var attr = input.attributes[a];
      if (attr.name.indexOf('aria-') === 0) proxy.setAttribute(attr.name, attr.value);
    }
    if (!proxy.hasAttribute('aria-multiline')) proxy.setAttribute('aria-multiline', 'false');

    var pair = {
      original: input,
      proxy: proxy,
      sourceId: sourceId,
      tabindex: input.hasAttribute('tabindex') ? input.getAttribute('tabindex') : null,
      ariaHidden: input.hasAttribute('aria-hidden') ? input.getAttribute('aria-hidden') : null,
      hadAriaHidden: input.hasAttribute('aria-hidden'),
      composing: false
    };
    input._mobilePair = pair;
    pairs.push(pair);

    textareaValue.set.call(proxy, limit(input, sanitize(inputValue.get.call(input))));
    input.insertAdjacentElement('beforebegin', proxy);
    input.classList.add('mobile-field-source');
    input.setAttribute('tabindex', '-1');
    input.setAttribute('aria-hidden', 'true');

    try {
      Object.defineProperty(input, 'value', {
        configurable: true,
        enumerable: true,
        get: function () { return inputValue.get.call(this); },
        set: function (next) {
          var clean = limit(this, sanitize(next));
          inputValue.set.call(this, clean);
          if (!document.contains(proxy)) return;
          if (readProxy(proxy) !== clean) {
            textareaValue.set.call(proxy, clean);
            fit(proxy);
          }
        }
      });
      Object.defineProperty(proxy, 'value', {
        configurable: true,
        enumerable: true,
        get: function () { return textareaValue.get.call(this); },
        set: function (next) {
          var clean = limit(input, sanitize(next));
          textareaValue.set.call(this, clean);
          if (inputValue.get.call(input) !== clean) inputValue.set.call(input, clean);
          fit(proxy);
        }
      });
    } catch (err) {}

    listen(proxy, 'compositionstart', function () { pair.composing = true; });
    listen(proxy, 'compositionend', function () {
      pair.composing = false;
      proxy.setCustomValidity('');
      syncToOriginal(pair, true);
    });
    listen(proxy, 'beforeinput', function (event) {
      if (event.inputType === 'insertLineBreak' || event.inputType === 'insertParagraph') {
        event.preventDefault();
      }
    });
    listen(proxy, 'keydown', function (event) {
      if (event.isComposing || event.keyCode === 229) return;
      if (event.key === 'Enter' || event.keyCode === 13) event.preventDefault();
    });
    listen(proxy, 'paste', function (event) {
      var data = event.clipboardData || window.clipboardData;
      if (!data) return;
      var text = data.getData('text/plain');
      if (!text || (text.indexOf('\n') === -1 && text.indexOf('\r') === -1 && text.indexOf('\u2028') === -1)) return;
      event.preventDefault();
      var clean = sanitize(text);
      var start = proxy.selectionStart || 0;
      var end = proxy.selectionEnd || 0;
      var merged = limit(input, readProxy(proxy).slice(0, start) + clean + readProxy(proxy).slice(end));
      textareaValue.set.call(proxy, merged);
      var caret = Math.min(start + clean.length, merged.length);
      try { proxy.setSelectionRange(caret, caret); } catch (err) {}
      proxy.setCustomValidity('');
      syncToOriginal(pair, true);
    });
    listen(proxy, 'input', function () {
      if (pair.composing) return;
      proxy.setCustomValidity('');
      syncToOriginal(pair, true);
    });
    listen(proxy, 'change', function () {
      proxy.setCustomValidity('');
      syncToOriginal(pair, false);
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
    listen(proxy, 'focus', function () { pullFromOriginal(pair); });
    listen(input, 'input', function () { pullFromOriginal(pair); });
    listen(input, 'change', function () { pullFromOriginal(pair); });
    listen(input, 'invalid', function (event) {
      event.preventDefault();
      var message = input.validationMessage || '';
      var proxyWasInvalid = !proxy.validity.valid;
      if (message) proxy.setCustomValidity(message);
      if (!proxyWasInvalid) {
        window.setTimeout(function () {
          if (document.contains(proxy)) proxy.reportValidity();
        }, 0);
      }
    });
    if (io && !supportsFieldSizing) io.observe(proxy);
    fit(proxy);
  }

  function restorePair(pair) {
    var input = pair.original;
    var proxy = pair.proxy;
    var focused = document.activeElement === proxy;
    if (inputValue && textareaValue && document.contains(proxy)) {
      var clean = limit(input, sanitize(textareaValue.get.call(proxy)));
      inputValue.set.call(input, clean);
    }
    if (proxy.parentNode) proxy.parentNode.removeChild(proxy);
    if (pair.sourceId) input.id = pair.sourceId;
    else if (input.id && input.id.indexOf('-source') !== -1) input.removeAttribute('id');
    input.classList.remove('mobile-field-source');
    if (pair.tabindex === null) input.removeAttribute('tabindex');
    else input.setAttribute('tabindex', pair.tabindex);
    if (!pair.hadAriaHidden) input.removeAttribute('aria-hidden');
    else input.setAttribute('aria-hidden', pair.ariaHidden);
    if (inputValue) {
      var current = inputValue.get.call(input);
      try {
        delete input.value;
      } catch (err) {}
      input.value = current;
    }
    delete input._mobilePair;
    bound.delete(input);
    if (focused) {
      try { input.focus(); } catch (err) {}
    }
  }

  function restoreAll() {
    var copy = pairs.slice();
    pairs = [];
    for (var i = 0; i < copy.length; i++) restorePair(copy[i]);
  }

  function clearFitted() {
    for (var i = 0; i < fitted.length; i++) {
      if (fitted[i] && fitted[i].style) fitted[i].style.height = '';
    }
    fitted = [];
  }

  function upgrade(el) {
    if (!active || !el || el.nodeType !== 1) return;
    if (el.tagName === 'TEXTAREA') {
      bindTextarea(el);
      return;
    }
    if (el.tagName === 'INPUT') proxyInput(el);
  }

  function scan(root) {
    if (!root) return;
    if (root === document || root === document.documentElement || root === document.body) {
      if (!document.body || !document.body.classList.contains('change-form')) return;
      var forms = document.querySelectorAll('form[id$="_form"]');
      for (var i = 0; i < forms.length; i++) scan(forms[i]);
      return;
    }
    if (root.nodeType !== 1) return;
    upgrade(root);
    if (!root.querySelectorAll) return;
    var nodes = root.querySelectorAll('input, textarea');
    for (var j = 0; j < nodes.length; j++) upgrade(nodes[j]);
  }

  function prune() {
    var next = [];
    for (var i = 0; i < pairs.length; i++) {
      if (document.contains(pairs[i].original)) next.push(pairs[i]);
      else delete pairs[i].original._mobilePair;
    }
    pairs = next;
  }

  function onSubmit(event) {
    if (!mobile) return;
    var form = event.target;
    if (!form || !form.querySelectorAll) return;
    var sources = form.querySelectorAll('input.mobile-field-source');
    var first = null;
    for (var i = 0; i < sources.length; i++) {
      var pair = sources[i]._mobilePair;
      if (!pair) continue;
      syncToOriginal(pair, false);
      pair.proxy.setCustomValidity('');
      if (!sources[i].validity.valid) {
        pair.proxy.setCustomValidity(sources[i].validationMessage || '');
      }
      if (!pair.proxy.validity.valid && isShown(pair.proxy) && !first) first = pair.proxy;
    }
    if (!first) return;
    event.preventDefault();
    first.reportValidity();
  }

  function onAdded(event) {
    if (!active) return;
    var target = event.target;
    if (!target || target === document || target === document.body) scan(document);
    else scan(target);
  }

  function scheduleRefit() {
    if (scheduleRefit.queued || supportsFieldSizing || !mobile) return;
    scheduleRefit.queued = true;
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        scheduleRefit.queued = false;
        if (mobile) refitAll();
      });
    });
  }

  function onResize() {
    scheduleRefit();
  }

  function activate() {
    if (active || !document.body || !document.body.classList.contains('change-form')) return;
    active = true;
    mobile = true;
    if (!supportsFieldSizing && window.IntersectionObserver) {
      io = new IntersectionObserver(function (entries) {
        if (!mobile || supportsFieldSizing) return;
        for (var i = 0; i < entries.length; i++) {
          if (entries[i].isIntersecting) fit(entries[i].target);
        }
      });
    }
    scan(document);
    observer = new MutationObserver(function (mutations) {
      if (!active) return;
      for (var i = 0; i < mutations.length; i++) {
        var added = mutations[i].addedNodes;
        for (var j = 0; j < added.length; j++) scan(added[j]);
        if (mutations[i].removedNodes && mutations[i].removedNodes.length) prune();
      }
    });
    observer.observe(document.getElementById('content') || document.body, { childList: true, subtree: true });
    listen(document, 'formset:added', onAdded);
    listen(document, 'submit', onSubmit, true);
    if (!supportsFieldSizing) {
      listen(window, 'resize', onResize);
      if (window.visualViewport) listen(window.visualViewport, 'resize', onResize);
      listen(document, 'click', scheduleRefit);
      listen(document, 'focusin', scheduleRefit);
      if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(function () {
          if (mobile) refitAll();
        });
      }
    }
  }

  function deactivate() {
    if (!active) return;
    mobile = false;
    if (observer) {
      observer.disconnect();
      observer = null;
    }
    if (io) {
      io.disconnect();
      io = null;
    }
    var jobs = cleanups.slice();
    cleanups = [];
    for (var i = 0; i < jobs.length; i++) jobs[i]();
    restoreAll();
    clearFitted();
    bound = new WeakSet();
    active = false;
  }

  function syncMode() {
    if (!mq) return;
    if (mq.matches) activate();
    else deactivate();
  }

  function boot() {
    if (!window.matchMedia || !inputValue || !textareaValue) return;
    mq = window.matchMedia(MQ);
    if (mq.addEventListener) mq.addEventListener('change', syncMode);
    else if (mq.addListener) mq.addListener(syncMode);
    window.addEventListener('orientationchange', syncMode);
    syncMode();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
