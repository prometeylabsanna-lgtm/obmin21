(function () {
  var PARENT_CLASS = "mobile-crumb-parent";
  var READY_CLASS = "mobile-crumbs-ready";

  function crumbText(node) {
    return (node.textContent || "").replace(/\s+/g, " ").trim();
  }

  function isCrumb(node) {
    if (!node || !node.tagName) {
      return false;
    }

    if (node.classList.contains("material-symbols-outlined")) {
      return false;
    }

    return node.tagName === "A" || node.tagName === "SPAN";
  }

  function markChangeFormParent() {
    var h1;
    var crumbs;
    var parent;
    var label;
    var i;

    if (!document.body.classList.contains("change-form")) {
      return;
    }

    h1 = document.querySelector("#header-inner .grow > h1");
    if (!h1) {
      return;
    }

    crumbs = [];
    for (i = 0; i < h1.children.length; i += 1) {
      if (isCrumb(h1.children[i])) {
        crumbs.push(h1.children[i]);
      }
    }

    if (crumbs.length < 2) {
      return;
    }

    parent = crumbs[crumbs.length - 2];
    if (parent.tagName !== "A" || !parent.getAttribute("href")) {
      return;
    }

    parent.classList.add(PARENT_CLASS);
    h1.classList.add(READY_CLASS);

    label = crumbText(parent);
    if (label && !parent.hasAttribute("aria-label")) {
      parent.setAttribute("aria-label", label);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var nodes = document.querySelectorAll(
      "#header-inner h1 > a, #header-inner h1 > span:not(.material-symbols-outlined)"
    );

    Array.prototype.forEach.call(nodes, function (node) {
      if (node.hasAttribute("title")) {
        return;
      }

      var text = crumbText(node);
      if (!text) {
        return;
      }

      node.setAttribute("title", text);
    });

    markChangeFormParent();
  });
})();
