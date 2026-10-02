(function () {
  'use strict';

  function parseNum(value) {
    var raw = String(value || '0').replace(',', '.').replace(/\s/g, '');
    var num = parseFloat(raw);
    return isNaN(num) ? 0 : num;
  }

  function formatNum(value, maxDecimals) {
    var decimals = typeof maxDecimals === 'number' ? maxDecimals : 2;
    if (!isFinite(value)) return '0';
    var text = Number(value).toFixed(decimals);
    if (text.indexOf('.') !== -1) {
      text = text.replace(/0+$/, '').replace(/\.$/, '');
    }
    return text;
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
    if (flagEl) flagEl.textContent = code.slice(0, 3);
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
    resultEl.textContent = formatNum(amount * buy, 2);
    if (labelEl) {
      labelEl.textContent = 'За поточним курсом 1 ' + code + ' = ' + (buyRaw || formatNum(buy, 4)) + ' UAH';
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
        var receive = formatNum(parseNum(amount) * parseNum(buy), 2);
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

  function initFaq() {
    document.querySelectorAll('[data-faq]').forEach(function (list) {
      list.querySelectorAll('.faq-item__q').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var item = btn.closest('.faq-item');
          var open = item.classList.contains('is-open');
          list.querySelectorAll('.faq-item').forEach(function (el) {
            el.classList.remove('is-open');
            var q = el.querySelector('.faq-item__q');
            if (q) q.setAttribute('aria-expanded', 'false');
          });
          if (!open) {
            item.classList.add('is-open');
            btn.setAttribute('aria-expanded', 'true');
          }
        });
      });
    });
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
})();
