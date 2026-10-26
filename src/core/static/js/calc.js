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

  function formatRateUa(value, decimals) {
    var n = Number(value);
    if (!isFinite(n)) return '0,00';
    return n.toLocaleString('uk-UA', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }

  function esc(value) {
    return String(value || '').replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  function byCode(list, code) {
    var i;
    for (i = 0; i < list.length; i += 1) {
      if (list[i].code === code) return list[i];
    }
    return null;
  }

  function readCurrencies(scope) {
    var el = scope.querySelector('#home-calc-currencies');
    if (!el) return null;
    try {
      var list = JSON.parse(el.textContent);
      return Array.isArray(list) && list.length ? list : null;
    } catch (e) {
      return null;
    }
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
      labelEl.textContent = 'За поточним курсом 1 ' + code + ' = ' + formatRateUa(buy, 2) + ' UAH';
    }
  }

  function bindCross(scope, list) {
    scope._calcCurrencies = list;
    var amountInput = scope.querySelector('[data-calc-amount]');
    var resultEl = scope.querySelector('[data-calc-result]');
    var labelEl = scope.querySelector('[data-calc-rate-label]');
    var fromCodeEl = scope.querySelector('[data-calc-from-code]');
    var toCodeEl = scope.querySelector('[data-calc-to-code]');
    var fromFlag = scope.querySelector('[data-calc-from-flag]');
    var toFlag = scope.querySelector('[data-calc-to-flag]');
    var fromMenu = scope.querySelector('[data-calc-from-menu]');
    var toMenu = scope.querySelector('[data-calc-to-menu]');
    var fromToggle = scope.querySelector('[data-calc-from-toggle]');
    var toToggle = scope.querySelector('[data-calc-to-toggle]');
    var fromCode = (fromCodeEl && fromCodeEl.textContent.trim()) || 'USD';
    var toCode = (toCodeEl && toCodeEl.textContent.trim()) || 'UAH';
    if (!byCode(list, fromCode)) fromCode = (byCode(list, 'USD') || list[0]).code;
    if (!byCode(list, toCode) || toCode === fromCode) {
      toCode = byCode(list, 'UAH') && fromCode !== 'UAH' ? 'UAH' : list[0].code;
    }

    function setFlag(el, code) {
      if (!el) return;
      el.className = 'flag';
      el.setAttribute('data-code', code);
      el.textContent = '';
    }

    function fillMenu(menu, active) {
      if (!menu) return;
      var html = '';
      list.forEach(function (item) {
        html +=
          '<button type="button" data-calc-choose="' + esc(item.code) + '"' +
          (item.code === active ? ' class="is-active"' : '') + '>' +
          '<span class="flag" data-code="' + esc(item.code) + '"></span>' +
          '<span class="code">' + esc(item.code) + '</span>' +
          '<span class="name">' + esc(item.name) + '</span></button>';
      });
      menu.innerHTML = html;
    }

    function closeMenus() {
      if (fromMenu) fromMenu.setAttribute('hidden', '');
      if (toMenu) toMenu.setAttribute('hidden', '');
      if (fromToggle) fromToggle.setAttribute('aria-expanded', 'false');
      if (toToggle) toToggle.setAttribute('aria-expanded', 'false');
    }

    function rateOf() {
      var from = byCode(list, fromCode);
      var to = byCode(list, toCode);
      if (!from || !to) return 0;
      var sellTo = parseNum(to.sell) || 1;
      return parseNum(from.buy) / sellTo;
    }

    function syncHeads() {
      if (fromCodeEl) fromCodeEl.textContent = fromCode;
      if (toCodeEl) toCodeEl.textContent = toCode;
      setFlag(fromFlag, fromCode);
      setFlag(toFlag, toCode);
      fillMenu(fromMenu, fromCode);
      fillMenu(toMenu, toCode);
    }

    function recalcCross() {
      var amount = parseNum(amountInput ? amountInput.value : '0');
      var rate = rateOf();
      var to = byCode(list, toCode);
      var decimals = to && parseNum(to.sell) > 1000 ? 6 : 2;
      if (resultEl) resultEl.textContent = formatUa(amount * rate, decimals);
      if (labelEl) {
        labelEl.textContent =
          'За поточним курсом 1 ' + fromCode + ' = ' +
          formatRateUa(rate, 2) + ' ' + toCode;
      }
    }

    scope._recalc = recalcCross;

    function pick(side, code) {
      if (!byCode(list, code)) return;
      if (side === 'from') {
        if (code === toCode) toCode = fromCode;
        fromCode = code;
      } else {
        if (code === fromCode) fromCode = toCode;
        toCode = code;
      }
      closeMenus();
      syncHeads();
      recalcCross();
    }

    function toggleMenu(menu, toggle) {
      var open = menu && menu.hasAttribute('hidden');
      closeMenus();
      if (open && menu) {
        menu.removeAttribute('hidden');
        if (toggle) toggle.setAttribute('aria-expanded', 'true');
      }
    }

    if (fromToggle && fromMenu) {
      fromToggle.addEventListener('click', function (event) {
        event.stopPropagation();
        toggleMenu(fromMenu, fromToggle);
      });
    }
    if (toToggle && toMenu) {
      toToggle.addEventListener('click', function (event) {
        event.stopPropagation();
        toggleMenu(toMenu, toToggle);
      });
    }

    scope.addEventListener('click', function (event) {
      var choice = event.target.closest('[data-calc-choose]');
      if (choice) {
        var side = choice.closest('[data-calc-to-menu]') ? 'to' : 'from';
        pick(side, choice.getAttribute('data-calc-choose'));
        return;
      }
      if (!event.target.closest('[data-calc-from-toggle], [data-calc-to-toggle], .currency-menu')) {
        closeMenus();
      }
    });

    document.addEventListener('click', function (event) {
      if (!scope.contains(event.target)) closeMenus();
    });

    var swap = scope.querySelector('[data-calc-swap]');
    if (swap) {
      swap.addEventListener('click', function () {
        var tmp = fromCode;
        fromCode = toCode;
        toCode = tmp;
        closeMenus();
        syncHeads();
        recalcCross();
      });
    }

    if (amountInput) {
      amountInput.addEventListener('input', function () {
        recalcCross();
      });
    }

    syncHeads();
    recalcCross();
  }

  function bindCalc(scope) {
    if (!scope || scope.dataset.calcBound === '1') return;
    scope.dataset.calcBound = '1';

    var currencies = readCurrencies(scope);
    if (currencies) {
      bindCross(scope, currencies);
      return;
    }

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

    scope._recalc = function () { recalc(scope); };
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
      if (scope._calcCurrencies) {
        scope._calcCurrencies.forEach(function (item) {
          if (String(item.pair_id) === id || (q.code && item.code === String(q.code).toUpperCase())) {
            item.buy = q.buy;
            item.sell = q.sell;
          }
        });
      }
    });
    if (scope._recalc) scope._recalc();
    else recalc(scope);
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

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-calc]').forEach(bindCalc);
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
