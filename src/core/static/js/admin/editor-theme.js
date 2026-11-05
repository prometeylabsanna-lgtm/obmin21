/* Скін TinyMCE за класом dark на <html>.
   Скрипт у head раніше за django-tinymce, тож перший init уже з правильним skin. */
(function () {
  'use strict';

  var FN_KEYS = [
    'color_picker_callback',
    'file_browser_callback',
    'file_picker_callback',
    'images_dataimg_filter',
    'images_upload_handler',
    'paste_postprocess',
    'paste_preprocess',
    'setup',
    'urlconverter_callback'
  ];

  var lastDark = null;
  var timer = 0;

  function isDark() {
    return document.documentElement.classList.contains('dark');
  }

  function readColor(name, fallback) {
    var raw = '';
    var guard = 0;
    try {
      raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    } catch (err) {
      raw = '';
    }
    while (raw.indexOf('var(') === 0 && guard < 4) {
      var match = raw.match(/^var\(\s*(--[\w-]+)/);
      if (!match) {
        break;
      }
      raw = getComputedStyle(document.documentElement).getPropertyValue(match[1]).trim();
      guard += 1;
    }
    if (/^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(raw)) {
      return raw;
    }
    if (/^rgba?\(\s*\d+(?:\.\d+)?%?\s*,\s*\d+(?:\.\d+)?%?\s*,\s*\d+(?:\.\d+)?%?\s*(?:,\s*(?:0|1|0?\.\d+)\s*)?\)$/.test(raw)) {
      return raw;
    }
    return fallback;
  }

  function themed(settings) {
    var source = settings || {};
    var next = {};
    var key;
    for (key in source) {
      if (Object.prototype.hasOwnProperty.call(source, key)) {
        next[key] = source[key];
      }
    }
    var dark = isDark();
    next.skin = dark ? 'oxide-dark' : 'oxide';
    next.content_css = dark ? 'dark' : 'default';
    var baseStyle = source.content_style ? String(source.content_style) : '';
    if (dark) {
      var bg = readColor('--color-base-900', '#052145');
      var fg = readColor('--color-font-default-dark', '') || readColor('--color-base-50', '#ffffff');
      var extra = 'body,body.mce-content-body{background-color:' + bg + ';color:' + fg + ';}';
      next.content_style = baseStyle + extra;
    } else {
      next.content_style = baseStyle;
    }
    return next;
  }

  function hookApi(api) {
    if (!api || typeof api.init !== 'function' || api.init.__obmin21Theme) {
      return api;
    }
    var orig = api.init.bind(api);
    function wrapped(settings) {
      var args = Array.prototype.slice.call(arguments);
      args[0] = themed(settings || {});
      return orig.apply(api, args);
    }
    wrapped.__obmin21Theme = true;
    api.init = wrapped;
    return api;
  }

  function installSetter(name) {
    var stored = window[name];
    try {
      Object.defineProperty(window, name, {
        configurable: true,
        enumerable: true,
        get: function () {
          return stored;
        },
        set: function (value) {
          stored = hookApi(value);
        }
      });
    } catch (err) {
      return;
    }
    if (stored) {
      window[name] = stored;
    }
  }

  function ensureHook() {
    hookApi(window.tinymce);
    hookApi(window.tinyMCE);
  }

  function cssEscape(value) {
    if (window.CSS && typeof CSS.escape === 'function') {
      return CSS.escape(value);
    }
    return String(value).replace(/[^a-zA-Z0-9_-]/g, '\\$&');
  }

  function revive(conf) {
    FN_KEYS.forEach(function (name) {
      if (typeof conf[name] === 'undefined') {
        return;
      }
      if (typeof conf[name] !== 'string') {
        return;
      }
      if (conf[name].indexOf('(') !== -1) {
        conf[name] = eval('(' + conf[name] + ')');
      } else {
        conf[name] = window[conf[name]];
      }
    });
  }

  function editorAreas() {
    return Array.prototype.filter.call(
      document.querySelectorAll('textarea.tinymce'),
      function (el) {
        return !el.closest('.empty-form');
      }
    );
  }

  function editorList(api) {
    var found = [];
    var seen = {};
    if (!api || typeof api.get !== 'function') {
      return found;
    }
    function push(ed) {
      if (!ed || !ed.id || seen[ed.id]) {
        return;
      }
      seen[ed.id] = true;
      found.push(ed);
    }
    try {
      var all = api.get();
      if (all && all.length) {
        Array.prototype.forEach.call(all, push);
      }
    } catch (err) {
      /* get(id) нижче */
    }
    if (api.editors && api.editors.length) {
      Array.prototype.forEach.call(api.editors, push);
    }
    Array.prototype.forEach.call(document.querySelectorAll('textarea.tinymce'), function (el) {
      if (el.closest('.empty-form')) {
        return;
      }
      try {
        push(api.get(el.id));
      } catch (err) {
        /* ще не ініціалізований */
      }
    });
    return found;
  }

  function hasEditors() {
    return editorList(window.tinymce || window.tinyMCE).length > 0;
  }

  function reinitEditors() {
    var api = window.tinymce || window.tinyMCE;
    if (!api || !hasEditors()) {
      return;
    }
    ensureHook();
    var areas = editorAreas();
    var saved = {};
    var live = editorList(api);
    if (typeof api.triggerSave === 'function') {
      try {
        api.triggerSave();
      } catch (err) {
        /* textarea лишається резервом */
      }
    }
    live.forEach(function (ed) {
      var el = document.getElementById(ed.id);
      if (!el) {
        return;
      }
      try {
        saved[ed.id] = ed.getContent();
      } catch (err) {
        saved[ed.id] = el.value;
      }
      try {
        ed.save();
      } catch (err) {
        /* getContent уже збережено */
      }
    });
    areas.forEach(function (el) {
      if (typeof saved[el.id] === 'string') {
        el.value = saved[el.id];
      }
      var ed = api.get ? api.get(el.id) : null;
      if (ed) {
        try {
          ed.remove();
        } catch (err) {
          /* наступний init підхопить textarea */
        }
      }
    });
    areas.forEach(function (el) {
      var raw = el.getAttribute('data-mce-conf');
      if (!raw) {
        return;
      }
      var conf;
      try {
        conf = JSON.parse(raw);
      } catch (err) {
        return;
      }
      revive(conf);
      conf.selector = '#' + cssEscape(el.id);
      delete conf.target;
      api.init(conf);
    });
  }

  function scheduleReinit() {
    if (timer) {
      window.clearTimeout(timer);
    }
    timer = window.setTimeout(function () {
      timer = 0;
      reinitEditors();
    }, 40);
  }

  function onClassChange() {
    var dark = isDark();
    if (dark === lastDark) {
      return;
    }
    lastDark = dark;
    if (!hasEditors()) {
      return;
    }
    scheduleReinit();
  }

  installSetter('tinymce');
  installSetter('tinyMCE');
  ensureHook();

  document.addEventListener('DOMContentLoaded', ensureHook);

  if (window.MutationObserver) {
    var observer = new MutationObserver(onClassChange);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });
  }
  lastDark = isDark();
})();
