/* Підписи полів мобільної картки TabularInline: data-label з thead.
   Стилі не пишемо — їх читає mobile-inlines.css.
   Повторний запуск безпечний: атрибут ставиться лише коли значення змінилось. */
(function () {
  'use strict';

  if (window.__obminMobileInlinesInit) {
    return;
  }
  window.__obminMobileInlinesInit = true;

  var jqueryBound = false;

  function fieldName(el, prefix) {
    var list = el.classList;
    var i;
    var cls;
    var name;

    if (!list) {
      return '';
    }

    for (i = 0; i < list.length; i += 1) {
      cls = list[i];
      if (cls.indexOf(prefix) !== 0) {
        continue;
      }
      name = cls.slice(prefix.length);
      if (!name || name === 'tabular') {
        continue;
      }
      return name;
    }

    return '';
  }

  function hasClassToken(el, token) {
    return (' ' + (el.className || '') + ' ').indexOf(' ' + token + ' ') !== -1;
  }

  function columnIsHidden(el) {
    if (!el) {
      return false;
    }
    return hasClassToken(el, 'hidden') || hasClassToken(el, 'hidden!');
  }

  function columnLabel(th) {
    var clone = th.cloneNode(true);
    var noise = clone.querySelectorAll('.material-symbols-outlined, .cursor-help, .asteriskField');
    var i;
    var text;

    for (i = noise.length - 1; i >= 0; i -= 1) {
      if (noise[i].parentNode) {
        noise[i].parentNode.removeChild(noise[i]);
      }
    }

    text = clone.textContent || '';
    return text.replace(/\*/g, '').replace(/\s+/g, ' ').trim();
  }

  function setAttr(el, name, value) {
    if (value) {
      if (el.getAttribute(name) !== value) {
        el.setAttribute(name, value);
      }
      return;
    }
    if (el.hasAttribute(name)) {
      el.removeAttribute(name);
    }
  }

  function directChildren(parent, tagName) {
    var found = [];
    var kids = parent ? parent.children : null;
    var i;

    if (!kids) {
      return found;
    }

    for (i = 0; i < kids.length; i += 1) {
      if (kids[i].tagName === tagName) {
        found.push(kids[i]);
      }
    }

    return found;
  }

  function headerCells(table) {
    var heads = directChildren(table, 'THEAD');
    var rows;
    var cells = [];
    var i;
    var j;
    var rowCells;

    if (!heads.length) {
      return cells;
    }

    rows = directChildren(heads[0], 'TR');
    for (i = 0; i < rows.length; i += 1) {
      rowCells = directChildren(rows[i], 'TH');
      for (j = 0; j < rowCells.length; j += 1) {
        cells.push(rowCells[j]);
      }
    }

    return cells;
  }

  function formRows(table) {
    var bodies = directChildren(table, 'TBODY');
    var rows = [];
    var i;
    var j;
    var bodyRows;

    for (i = 0; i < bodies.length; i += 1) {
      bodyRows = directChildren(bodies[i], 'TR');
      for (j = 0; j < bodyRows.length; j += 1) {
        if (hasClassToken(bodyRows[j], 'form-row')) {
          rows.push(bodyRows[j]);
        }
      }
    }

    return rows;
  }

  function labelTable(table) {
    var ths = headerCells(table);
    var byName = {};
    var i;
    var name;
    var rows;
    var r;
    var tds;
    var c;
    var td;
    var th;
    var label;

    if (!ths.length) {
      return;
    }

    for (i = 0; i < ths.length; i += 1) {
      name = fieldName(ths[i], 'column-');
      if (name) {
        byName[name] = ths[i];
      }
    }

    rows = formRows(table);
    for (r = 0; r < rows.length; r += 1) {
      tds = directChildren(rows[r], 'TD');
      for (c = 0; c < tds.length; c += 1) {
        td = tds[c];
        if (hasClassToken(td, 'delete')) {
          setAttr(td, 'data-label', '');
          setAttr(td, 'data-inline-hidden', '');
          continue;
        }

        name = fieldName(td, 'field-');
        th = (name && byName[name]) || ths[c] || null;
        if (!th) {
          continue;
        }

        if (columnIsHidden(th) || columnIsHidden(td)) {
          setAttr(td, 'data-inline-hidden', '1');
        } else {
          setAttr(td, 'data-inline-hidden', '');
        }

        label = columnLabel(th);
        setAttr(td, 'data-label', label);
      }
    }
  }

  function pushUnique(list, node) {
    if (!node || list.indexOf(node) !== -1) {
      return;
    }
    list.push(node);
  }

  function tablesUnder(root, list) {
    var nodes;
    var i;
    var parentTable;

    if (!root || root.nodeType !== 1 || !root.querySelectorAll) {
      return;
    }

    if (root.matches('table.formset') || (root.matches('table') && root.closest('[data-inline-type="tabular"]'))) {
      pushUnique(list, root);
    }

    nodes = root.querySelectorAll('table.formset, [data-inline-type="tabular"] table');
    for (i = 0; i < nodes.length; i += 1) {
      pushUnique(list, nodes[i]);
    }

    if (root.closest) {
      parentTable = root.closest('table.formset, [data-inline-type="tabular"] table');
      if (parentTable) {
        pushUnique(list, parentTable);
      }
    }
  }

  function labelAll(root) {
    var list = [];
    var nodes;
    var i;

    if (root && root.nodeType === 1) {
      tablesUnder(root, list);
    } else {
      nodes = document.querySelectorAll('table.formset, [data-inline-type="tabular"] table');
      for (i = 0; i < nodes.length; i += 1) {
        pushUnique(list, nodes[i]);
      }
    }

    for (i = 0; i < list.length; i += 1) {
      labelTable(list[i]);
    }
  }

  function elementFrom(value) {
    if (!value) {
      return null;
    }
    if (value.jquery && value.get) {
      return value.get(0) || null;
    }
    if (value.nodeType === 1) {
      return value;
    }
    return null;
  }

  function onFormsetAdded(event, row) {
    var el = elementFrom(row) || elementFrom(event && event.target);
    if (!el) {
      labelAll(document);
      return;
    }
    labelAll(el);
  }

  function bindJquery() {
    if (jqueryBound || !(window.django && window.django.jQuery)) {
      return;
    }
    jqueryBound = true;
    window.django.jQuery(document).on('formset:added', onFormsetAdded);
  }

  function watchNewRows() {
    if (!window.MutationObserver || !document.body) {
      return;
    }

    var scheduled = false;
    var observer = new MutationObserver(function (mutations) {
      var relevant = false;
      var i;
      var j;
      var node;

      for (i = 0; i < mutations.length; i += 1) {
        for (j = 0; j < mutations[i].addedNodes.length; j += 1) {
          node = mutations[i].addedNodes[j];
          if (!node || node.nodeType !== 1) {
            continue;
          }
          if (
            (node.matches && (node.matches('tbody, table, [data-inline-type="tabular"]') || node.matches('tr'))) ||
            (node.querySelector && node.querySelector('tbody, table.formset, [data-inline-type="tabular"]'))
          ) {
            relevant = true;
            break;
          }
        }
        if (relevant) {
          break;
        }
      }

      if (!relevant || scheduled) {
        return;
      }

      scheduled = true;
      window.requestAnimationFrame(function () {
        scheduled = false;
        labelAll(document);
      });
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  function init() {
    bindJquery();
    labelAll(document);
    watchNewRows();
  }

  document.addEventListener('formset:added', onFormsetAdded);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  bindJquery();
})();
