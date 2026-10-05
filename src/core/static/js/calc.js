(function () {
  'use strict';

  function parseNum(value) {
    var raw = String(value || '0').replace(',', '.').replace(/\s/g, '');
    var num = parseFloat(raw);
    return isNaN(num) ? 0 : num;
  }

  function formatUa(value, maxDecimals) {
    var n = Number(value);
    if (!isFinite(n)) return '0';
    return n.toLocaleString('uk-UA', {
      minimumFractionDigits: 0,
      maximumFractionDigits: maxDecimals
    });
  }

  function formatNum(value, maxDecimals) {
    return formatUa(value, typeof maxDecimals === 'number' ? maxDecimals : 2);
  }

  function activeBtn(scope) {
    return (
      scope.querySelector('.calc-codes__btn.is-active') ||
      scope.querySelector('[data-calc-pick].is-active')
    );
  }

  function syncActive(scope, btn) {
    scope.querySelectorAll('.calc-codes__btn, [data-calc-pick]').forEach(function (el) {
      el.classList.toggle('is-active', el === btn || el.getAttribute('data-code') === btn.getAttribute('data-code') || el.getAttribute('data-calc-code') === btn.getAttribute('data-code') || el.getAttribute('data-calc-code') === btn.getAttribute('data-calc-code'));
    });
    var code = btn.getAttribute('data-code') || btn.getAttribute('data-calc-code') || '';
    var codeEl = scope.querySelector('[data-calc-from-code]');
    var flagEl = scope.querySelector('[data-calc-from-flag]');
    if (codeEl) codeEl.textContent = code;
    if (flagEl) {
      flagEl.className = 'flag flag--' + code.toLowerCase();
      flagEl.setAttribute('data-code', code);
      flagEl.textContent = '';
    }
  }

  function recalc(scope) {
    var amountInput = scope.querySelector('[data-calc-amount]');
    var resultEl = scope.querySelector('[data-calc-result]');
    var labelEl = scope.querySelector('[data-calc-rate-label]');
    var btn = activeBtn(scope);
    if (!amountInput || !resultEl || !btn) return;
    var amount = parseNum(amountInput.value);
    var buyRaw = btn.getAttribute('data-buy') || '0';
    var buy = parseNum(buyRaw);
    var code = btn.getAttribute('data-code') || btn.getAttribute('data-calc-code') || '';
    resultEl.textContent = formatUa(amount * buy, 2);
    if (labelEl) {
      var rateDecimals = buy < 1 ? 4 : 2;
      labelEl.textContent = 'За поточним курсом 1 ' + code + ' = ' + formatUa(buy, rateDecimals) + ' UAH';
    }
  }

  function bindCalc(scope) {
    if (!scope || scope.dataset.calcBound === '1') return;
    scope.dataset.calcBound = '1';

    var amountInput = scope.querySelector('[data-calc-amount]');
    if (amountInput) {
      amountInput.addEventListener('input', function () {
        recalc(scope);
      });
    }

    var fromToggle = scope.querySelector('[data-calc-from-toggle]');
    var fromMenu = scope.querySelector('[data-calc-from-menu]');
    if (fromToggle && fromMenu) {
      fromToggle.addEventListener('click', function (e) {
        e.stopPropagation();
        fromMenu.toggleAttribute('hidden');
      });
      document.addEventListener('click', function (e) {
        if (!e.target.closest('[data-calc]')) fromMenu.setAttribute('hidden', '');
      });
    }

    scope.querySelectorAll('[data-calc-pick], .calc-codes__btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        syncActive(scope, btn);
        if (fromMenu) fromMenu.setAttribute('hidden', '');
        recalc(scope);
      });
    });

    var cont = scope.querySelector('[data-calc-continue]');
    if (cont) {
      cont.addEventListener('click', function () {
        var btn = activeBtn(scope);
        if (!btn || !window.Obmin21) return;
        var amount = amountInput ? amountInput.value : '100';
        var buy = btn.getAttribute('data-buy');
        var pairId = btn.getAttribute('data-pair-id');
        var receive = formatUa(parseNum(amount) * parseNum(buy), 2);
        var url =
          '/htmx/zayavka/?pair=' +
          encodeURIComponent(pairId) +
          '&direction=sell&amount_give=' +
          encodeURIComponent(amount) +
          '&amount_receive=' +
          encodeURIComponent(receive) +
          '&rate_fixed=' +
          encodeURIComponent(buy) +
          '&step=1';
        window.Obmin21.openModal(url);
      });
    }

    recalc(scope);
  }

  function applyQuotes(scope, quotes) {
    if (!scope || !quotes || !quotes.length) return;
    quotes.forEach(function (q) {
      var id = String(q.id);
      scope.querySelectorAll('[data-pair-id="' + id + '"]').forEach(function (el) {
        el.setAttribute('data-buy', q.buy);
        el.setAttribute('data-sell', q.sell);
        if (q.code) {
          el.setAttribute('data-code', q.code);
          if (el.hasAttribute('data-calc-code')) el.setAttribute('data-calc-code', q.code);
        }
      });
    });
    recalc(scope);
  }

  function syncQuotes() {
    var board = 'retail';
    var tab = document.querySelector('#rates-panel .rates-tabs__btn.is-active');
    if (tab) {
      var qa = tab.getAttribute('data-qa') || '';
      board = qa.replace('rates-tab-', '') || 'retail';
    }
    fetch('/partials/quotes.json?board=' + encodeURIComponent(board), { credentials: 'same-origin' })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (!data || !data.quotes) return;
        document.querySelectorAll('[data-calc]').forEach(function (scope) {
          applyQuotes(scope, data.quotes);
        });
      })
      .catch(function () {});
  }

  function initFaq() {
    /* handled in pages/home.js */
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-calc]').forEach(bindCalc);
    initFaq();
  });

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var calc = evt.target.querySelector
      ? evt.target.querySelector('[data-calc]')
      : null;
    if (!calc && evt.target.matches && evt.target.matches('[data-calc]')) {
      calc = evt.target;
    }
    if (calc) {
      calc.dataset.calcBound = '0';
      bindCalc(calc);
    }
  });

  window.Obmin21 = window.Obmin21 || {};
  window.Obmin21.syncQuotes = syncQuotes;
})();
