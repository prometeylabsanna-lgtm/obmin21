(function () {
  'use strict';

  var SYM = {
    UAH: '₴', USD: '$', EUR: '€', PLN: 'zł', GBP: '£', CHF: 'CHF',
    CNY: '¥'
  };

  function parseNum(value) {
    var num = parseFloat(String(value || '0').replace(',', '.').replace(/\s/g, ''));
    return isNaN(num) ? 0 : num;
  }

  function fmt(value, maxDecimals) {
    var n = Number(value);
    if (!isFinite(n)) return '0';
    return n.toLocaleString('uk-UA', {
      minimumFractionDigits: 0,
      maximumFractionDigits: typeof maxDecimals === 'number' ? maxDecimals : 2
    });
  }

  function byCode(list, code) {
    var i;
    for (i = 0; i < list.length; i += 1) {
      if (list[i].code === code) return list[i];
    }
    return list[0] || null;
  }

  function fillMenu(menu, list, active) {
    var html = '';
    list.forEach(function (c) {
      html +=
        '<button type="button" data-bk-pick="' + c.code + '"' +
        (c.code === active ? ' class="is-active"' : '') + '>' +
        '<span class="flag" data-code="' + c.code + '"></span>' +
        '<span class="code">' + c.code + '</span>' +
        '<span class="name">' + c.name + '</span></button>';
    });
    menu.innerHTML = html;
  }

  function closeMenus(root) {
    var fromMenu = root.querySelector('[data-bk-from-menu]');
    var toMenu = root.querySelector('[data-bk-to-menu]');
    if (fromMenu) fromMenu.setAttribute('hidden', '');
    if (toMenu) toMenu.setAttribute('hidden', '');
  }

  function bindBooking(root) {
    if (!root || root.dataset.bkBound === '1') return;
    root.dataset.bkBound = '1';

    var jsonEl = document.getElementById('bk-currencies');
    var list = [];
    try {
      list = JSON.parse(jsonEl ? jsonEl.textContent : '[]');
    } catch (e) {
      list = [];
    }
    if (!list.length) return;

    var fromCode = (root.querySelector('[data-bk-from-code]') || {}).textContent || 'USD';
    var toCode = (root.querySelector('[data-bk-to-code]') || {}).textContent || 'UAH';
    var amountEl = root.querySelector('[data-bk-amount]');
    var resultEl = root.querySelector('[data-bk-result]');
    var rateEl = root.querySelector('[data-bk-rate]');
    var fromFlag = root.querySelector('[data-bk-from-flag]');
    var toFlag = root.querySelector('[data-bk-to-flag]');
    var fromCodeEl = root.querySelector('[data-bk-from-code]');
    var toCodeEl = root.querySelector('[data-bk-to-code]');
    var fromMenu = root.querySelector('[data-bk-from-menu]');
    var toMenu = root.querySelector('[data-bk-to-menu]');
    var fixBtn = root.querySelector('[data-bk-fix]');
    var panel1 = root.querySelector('[data-bk-panel="1"]');
    var panel2 = root.querySelector('[data-bk-panel="2"]');
    var fixTextEl = root.querySelector('[data-bk-fix-text]');

    function rateOf() {
      var from = byCode(list, fromCode);
      var to = byCode(list, toCode);
      if (!from || !to) return 0;
      var sellTo = parseNum(to.sell) || 1;
      return parseNum(from.buy) / sellTo;
    }

    function setFlag(el, code) {
      if (!el) return;
      el.setAttribute('data-code', code);
      el.className = 'flag';
    }

    function syncHeads() {
      if (fromCodeEl) fromCodeEl.textContent = fromCode;
      if (toCodeEl) toCodeEl.textContent = toCode;
      setFlag(fromFlag, fromCode);
      setFlag(toFlag, toCode);
      fillMenu(fromMenu, list, fromCode);
      fillMenu(toMenu, list, toCode);
    }

    function recalc() {
      var n = parseNum(amountEl ? amountEl.value : '0');
      var rate = rateOf();
      var to = byCode(list, toCode);
      var dTo = to && parseNum(to.sell) > 1000 ? 6 : 2;
      if (resultEl) resultEl.textContent = fmt(n * rate, dTo);
      if (rateEl) {
        rateEl.textContent =
          'Курс: 1 ' + fromCode + ' = ' + fmt(rate, rate < 1 ? 6 : 2) + ' ' + toCode + ' · без комісій';
      }
      if (fixBtn) {
        fixBtn.classList.toggle('is-off', !n);
        fixBtn.disabled = !n;
      }
    }

    function pick(side, code) {
      if (side === 'from') {
        if (code === toCode) toCode = fromCode;
        fromCode = code;
      } else {
        if (code === fromCode) fromCode = toCode;
        toCode = code;
      }
      closeMenus(root);
      syncHeads();
      recalc();
    }

    function showPanel(n) {
      if (panel1) panel1.hidden = n !== 1;
      if (panel2) panel2.hidden = n !== 2;
    }

    function currencyMark(code) {
      var item = byCode(list, code);
      if (item && item.symbol) return String(item.symbol);
      return SYM[code] || code;
    }

    function goStep2() {
      var n = parseNum(amountEl ? amountEl.value : '0');
      if (!n) return;
      var rate = rateOf();
      var to = byCode(list, toCode);
      var dTo = to && parseNum(to.sell) > 1000 ? 6 : 2;
      var resultText = fmt(n * rate, dTo) + ' ' + currencyMark(toCode);
      var forText = 'за ' + fmt(n, 6) + ' ' + currencyMark(fromCode);
      if (fixTextEl) fixTextEl.textContent = resultText + ' ' + forText;
      var pairCode = fromCode === 'UAH' ? toCode : fromCode;
      var pairItem = byCode(list, pairCode);
      var pairInput = root.querySelector('[name="pair"]');
      var amountInput = root.querySelector('[name="amount_give"]');
      var dirInput = root.querySelector('[name="direction"]');
      if (pairInput && pairItem && pairItem.pair_id) pairInput.value = pairItem.pair_id;
      if (amountInput) amountInput.value = String(n).replace(',', '.');
      if (dirInput) dirInput.value = fromCode === 'UAH' ? 'buy' : 'sell';
      showPanel(2);
    }

    if (amountEl) {
      amountEl.addEventListener('input', function () {
        amountEl.value = amountEl.value.replace(/[^\d.,\s]/g, '');
        recalc();
      });
    }

    var fromToggle = root.querySelector('[data-bk-from-toggle]');
    var toToggle = root.querySelector('[data-bk-to-toggle]');
    if (fromToggle) {
      fromToggle.addEventListener('click', function (e) {
        e.stopPropagation();
        var open = fromMenu.hasAttribute('hidden');
        closeMenus(root);
        if (open) fromMenu.removeAttribute('hidden');
      });
    }
    if (toToggle) {
      toToggle.addEventListener('click', function (e) {
        e.stopPropagation();
        var open = toMenu.hasAttribute('hidden');
        closeMenus(root);
        if (open) toMenu.removeAttribute('hidden');
      });
    }

    root.addEventListener('click', function (e) {
      var pickBtn = e.target.closest('[data-bk-pick]');
      if (pickBtn) {
        var side = pickBtn.closest('[data-bk-from-menu]') ? 'from' : 'to';
        pick(side, pickBtn.getAttribute('data-bk-pick'));
        return;
      }
      if (!e.target.closest('[data-bk-from-toggle], [data-bk-to-toggle], .currency-menu')) {
        closeMenus(root);
      }
    });

    var swap = root.querySelector('[data-bk-swap]');
    if (swap) {
      swap.addEventListener('click', function () {
        var tmp = fromCode;
        fromCode = toCode;
        toCode = tmp;
        closeMenus(root);
        syncHeads();
        recalc();
      });
    }

    var citySel = root.querySelector('[data-bk-city]');
    var branchSel = root.querySelector('[data-bk-branch]');
    var placesEl = root.querySelector('#bk-places');
    var quoteSeq = 0;

    function applyCityQuotes(quotes) {
      var i;
      var j;
      var code;
      for (i = 0; i < quotes.length; i += 1) {
        code = String(quotes[i].code || '').toUpperCase();
        for (j = 0; j < list.length; j += 1) {
          if (String(list[j].pair_id) === String(quotes[i].id) || list[j].code === code) {
            list[j].buy = String(quotes[i].buy);
            list[j].sell = String(quotes[i].sell);
          }
        }
      }
      recalc();
    }

    function loadCityQuotes() {
      if (!citySel) return;
      var option = citySel.options[citySel.selectedIndex];
      var slug = option ? (option.getAttribute('data-city') || '') : '';
      if (!slug) return;
      var base = citySel.getAttribute('data-quotes-url') || '/partials/quotes.json';
      var glue = base.indexOf('?') === -1 ? '?' : '&';
      var url = base + glue + 'board=retail&city=' + encodeURIComponent(slug);
      quoteSeq += 1;
      var seq = quoteSeq;
      fetch(url, { credentials: 'same-origin' })
        .then(function (res) { return res.ok ? res.json() : null; })
        .then(function (data) {
          if (seq !== quoteSeq || !data || !data.quotes) return;
          applyCityQuotes(data.quotes);
        })
        .catch(function () {});
    }

    if (citySel && branchSel && placesEl) {
      var places = [];
      try {
        places = JSON.parse(placesEl.textContent);
      } catch (err) {
        places = [];
      }
      citySel.addEventListener('change', function () {
        var place = null;
        var i;
        for (i = 0; i < places.length; i += 1) {
          if (String(places[i].id) === String(citySel.value)) {
            place = places[i];
            break;
          }
        }
        if (place) {
          var previous = branchSel.value;
          branchSel.replaceChildren();
          place.branches.forEach(function (item) {
            var option = document.createElement('option');
            option.value = String(item.id);
            option.textContent = item.address;
            branchSel.appendChild(option);
          });
          if (previous) branchSel.value = previous;
        }
        loadCityQuotes();
      });
    } else if (citySel) {
      citySel.addEventListener('change', loadCityQuotes);
    }

    if (fixBtn) fixBtn.addEventListener('click', goStep2);

    var back = root.querySelector('[data-bk-back]');
    if (back) {
      back.addEventListener('click', function () {
        showPanel(1);
      });
    }

    syncHeads();
    recalc();
  }

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var node = evt.target.querySelector
      ? evt.target.querySelector('[data-booking]')
      : null;
    if (!node && evt.target.matches && evt.target.matches('[data-booking]')) {
      node = evt.target;
    }
    if (node) bindBooking(node);
  });
})();
