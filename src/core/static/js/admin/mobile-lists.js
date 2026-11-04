(function () {
  if (window.__obminMobileLists) {
    return;
  }
  window.__obminMobileLists = true;

  function clean(value) {
    return (value || "").replace(/\s+/g, " ").trim();
  }

  function headerLabel(th) {
    var box = th.querySelector(".text");
    var source = box || th;
    var clone = source.cloneNode(true);
    clone.querySelectorAll(".sortoptions, .sortpriority, .material-symbols-outlined").forEach(function (node) {
      node.remove();
    });
    return clean(clone.textContent);
  }

  function cellsOf(row) {
    return Array.prototype.filter.call(row.children, function (el) {
      return el.tagName === "TD" || el.tagName === "TH";
    });
  }

  function textOf(el) {
    return clean(el.textContent);
  }

  function titleLink(row) {
    var links = row.querySelectorAll('a[href*="/change/"]');
    var fallback = null;
    for (var i = 0; i < links.length; i += 1) {
      if (!fallback) {
        fallback = links[i];
      }
      if (textOf(links[i])) {
        return links[i];
      }
    }
    return fallback;
  }

  function fallbackLabel(cell) {
    if (cell.querySelector(".errorlist, .errornote")) {
      return "Помилки";
    }
    if (cell.classList.contains("field-actions_holder")) {
      return "Дії";
    }
    if (cell.hasAttribute("x-sort:handle") || cell.querySelector(".cursor-move")) {
      return "Порядок";
    }
    if (cell.getAttribute("colspan")) {
      return "Деталі";
    }
    var match = (cell.className || "").match(/field-([A-Za-z0-9_]+)/);
    if (match) {
      return match[1].replace(/_/g, " ");
    }
    return "Поле";
  }

  function isCheck(cell) {
    return cell.classList.contains("action-checkbox")
      || !!cell.querySelector('input.action-select, input[name="_selected_action"]');
  }

  function markTable(table) {
    var heads = table.querySelectorAll("thead th");
    var labels = [];
    var kept = false;
    heads.forEach(function (th) {
      labels.push(headerLabel(th));
      var keep = !!th.querySelector("#action-toggle, .action-toggle");
      th.classList.toggle("ml-head-keep", keep);
      th.classList.toggle("ml-head-hide", !keep);
      kept = kept || keep;
    });
    table.classList.toggle("ml-has-toggle", kept);

    table.querySelectorAll(".ml-top, .ml-title, .ml-photo, .ml-check, .ml-title-link").forEach(function (el) {
      el.classList.remove("ml-top", "ml-title", "ml-photo", "ml-check", "ml-title-link");
    });

    table.querySelectorAll("tbody tr").forEach(function (row) {
      var cells = cellsOf(row);
      var photo = null;
      var check = null;
      cells.forEach(function (cell, index) {
        var label = labels[index] || "";
        if (!label) {
          label = fallbackLabel(cell);
        }
        if (label) {
          cell.setAttribute("data-label", label);
        }
        if (!check && isCheck(cell)) {
          check = cell;
        }
        if (!photo && cell.querySelector("img")) {
          photo = cell;
        }
      });

      var link = titleLink(row);
      var title = link ? link.closest("td, th") : null;
      if (check) {
        check.classList.add("ml-top", "ml-check");
      }
      if (photo) {
        photo.classList.add("ml-top", "ml-photo");
      }
      if (title) {
        title.classList.add("ml-top", "ml-title");
      }
      if (link && textOf(link)) {
        link.classList.add("ml-title-link");
      }
    });

    table.dataset.mlReady = "1";
  }

  function markAll() {
    document.querySelectorAll("#result_list").forEach(markTable);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", markAll);
  } else {
    markAll();
  }
  document.addEventListener("htmx:afterSwap", markAll);
  document.addEventListener("htmx:afterSettle", markAll);
})();
