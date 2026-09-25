(function () {
  'use strict';

  function activeCodeBtn(scope) {
    return scope.querySelector('.calc-codes__btn.is-active');
  }

  function parseNum(value) {
    var raw = String(value || '0').replace(',', '.').replace(/\s/g, '');
    var num = parseFloat(raw);
    return isNaN(num) ? 0 : num;
  }

  /** Strip trailing zeros: 4120.00 → 4120, 41.20 → 41.2, 1.16 → 1.16 */
  function formatNum(value, maxDecimals) {
    var decimals = typeof maxDecimals === 'number' ? maxDecimals : 2;
    if (!isFinite(value)) {
      return '0';
    }
    var text = Number(value).toFixed(decimals);
    if (text.indexOf('.') !== -1) {
      text = text.replace(/0+$/, '').replace(/\.$/, '');
    }
    return text;
  }

  function recalc(scope) {
    var amountInput = scope.querySelector('[data-calc-amount]');
    var resultEl = scope.querySelector('[data-calc-result]');
    var labelEl = scope.querySelector('[data-calc-rate-label]');
    var btn = activeCodeBtn(scope);
    if (!amountInput || !resultEl || !btn) return;
    var amount = parseNum(amountInput.value);
    var buyRaw = btn.getAttribute('data-buy') || '0';
    var buy = parseNum(buyRaw);
    var out = amount * buy;
    resultEl.textContent = formatNum(out, 2);
    if (labelEl) {
      var rateLabel = buyRaw || formatNum(buy, 4);
      labelEl.textContent =
        'за курсом купівлі ' + rateLabel + ' · ' + btn.getAttribute('data-calc-code');
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
    scope.querySelectorAll('[data-calc-code]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        scope.querySelectorAll('[data-calc-code]').forEach(function (b) {
          b.classList.remove('is-active');
        });
        btn.classList.add('is-active');
        recalc(scope);
      });
    });
    var cont = scope.querySelector('[data-calc-continue]');
    if (cont) {
      cont.addEventListener('click', function () {
        var btn = activeCodeBtn(scope);
        var amountInput = scope.querySelector('[data-calc-amount]');
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
          encodeURIComponent(buy);
        window.Obmin21.openModal(url);
      });
    }
    recalc(scope);
  }

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var calc = evt.target.querySelector
      ? evt.target.querySelector('[data-calc]')
      : null;
    if (!calc && evt.target.matches && evt.target.matches('[data-calc]')) {
      calc = evt.target;
    }
    if (calc) bindCalc(calc);
  });
})();
