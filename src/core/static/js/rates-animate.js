(function () {
  'use strict';

  var DURATION = 620;
  var ROW_STAGGER = 36;
  var VALUE_STAGGER = 40;

  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function easeOutExpo(t) {
    return t >= 1 ? 1 : 1 - Math.pow(2, -10 * t);
  }

  function parseRate(text) {
    var raw = String(text || '').trim();
    var normalized = raw.replace(/\s/g, '').replace(',', '.');
    var num = parseFloat(normalized);
    if (!isFinite(num)) {
      return null;
    }
    var parts = normalized.split('.');
    var decimals = parts.length > 1 ? parts[1].length : 0;
    return { value: num, decimals: decimals, raw: raw };
  }

  function formatRate(value, decimals) {
    var text = value.toFixed(decimals);
    if (text.indexOf('.') !== -1) {
      text = text.replace(/0+$/, '').replace(/\.$/, '');
    }
    return text;
  }

  function animateValue(el, target, delay) {
    var start = null;
    var from = 0;
    var startedReveal = false;

    el.classList.add('is-animating');
    el.textContent = formatRate(from, target.decimals);

    function frame(ts) {
      if (start === null) {
        start = ts;
      }
      var elapsed = ts - start - delay;
      if (elapsed < 0) {
        window.requestAnimationFrame(frame);
        return;
      }

      if (!startedReveal) {
        startedReveal = true;
        el.classList.add('is-revealed');
      }

      var progress = Math.min(1, elapsed / DURATION);
      var eased = easeOutExpo(progress);
      var current = from + (target.value - from) * eased;
      el.textContent = formatRate(current, target.decimals);

      if (progress < 1) {
        window.requestAnimationFrame(frame);
        return;
      }

      el.textContent = target.raw;
      el.classList.remove('is-animating');
    }

    window.requestAnimationFrame(frame);
  }

  function revealRow(row, delay) {
    row.classList.add('is-rate-enter');
    window.setTimeout(function () {
      row.classList.add('is-rate-visible');
      row.classList.remove('is-rate-enter');
    }, delay);
  }

  function animateRates(root) {
    var scope = root || document;
    var values = scope.querySelectorAll(
      '[data-rate-animate]:not(.is-revealed):not(.is-animating)'
    );
    if (!values.length) {
      return;
    }

    if (prefersReducedMotion()) {
      values.forEach(function (el) {
        el.classList.add('is-revealed');
      });
      scope.querySelectorAll('.rates-table__row[data-qa="rate-row"]').forEach(function (row) {
        row.classList.add('is-rate-visible');
      });
      return;
    }

    var rows = scope.querySelectorAll('.rates-table__row[data-qa="rate-row"]');
    rows.forEach(function (row, index) {
      if (!row.classList.contains('is-rate-visible')) {
        revealRow(row, index * ROW_STAGGER);
      }
    });

    values.forEach(function (el, index) {
      var parsed = parseRate(el.textContent);
      if (!parsed) {
        el.classList.add('is-revealed');
        return;
      }
      var row = el.closest('.rates-table__row');
      var rowIndex = row && rows.length ? Array.prototype.indexOf.call(rows, row) : index;
      var delay = Math.max(0, rowIndex) * ROW_STAGGER + (index % 2) * VALUE_STAGGER * 0.35;
      animateValue(el, parsed, delay);
    });
  }

  function resolveRatesRoot(target) {
    if (!target) {
      return null;
    }
    if (target.id === 'rates-panel') {
      return target;
    }
    if (target.querySelector) {
      return target.querySelector('#rates-panel');
    }
    return null;
  }

  var savedRatesQuery = '';

  function bindRatesSearch(panel) {
    if (!panel) return;
    var input = panel.querySelector('[data-rates-search]');
    if (!input) return;
    if (savedRatesQuery) {
      input.value = savedRatesQuery;
    }

    function apply() {
      savedRatesQuery = input.value || '';
      var q = savedRatesQuery.trim().toLowerCase();
      var rows = panel.querySelectorAll('.rates-table__row[data-qa="rate-row"]');
      var visible = 0;
      rows.forEach(function (row) {
        var hay = (row.getAttribute('data-search') || row.textContent || '').toLowerCase();
        var show = !q || hay.indexOf(q) !== -1;
        row.hidden = !show;
        if (show) visible += 1;
      });
      var empty = panel.querySelector('[data-rates-empty]');
      if (empty) empty.hidden = visible > 0;
    }

    if (input.dataset.bound === '1') {
      apply();
      return;
    }
    input.dataset.bound = '1';
    input.addEventListener('input', apply);
    apply();
  }

  function boot() {
    animateRates(document);
    bindRatesSearch(document.getElementById('rates-panel'));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var panel = resolveRatesRoot(evt.target);
    if (panel) {
      animateRates(panel);
      bindRatesSearch(panel);
    }
  });

  window.Obmin21 = window.Obmin21 || {};
  window.Obmin21.animateRatesOnce = animateRates;
  window.Obmin21.animateRates = animateRates;
})();
