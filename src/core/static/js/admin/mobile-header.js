(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var nodes = document.querySelectorAll(
      "#header-inner h1 > a, #header-inner h1 > span:not(.material-symbols-outlined)"
    );

    Array.prototype.forEach.call(nodes, function (node) {
      if (node.hasAttribute("title")) {
        return;
      }

      var text = node.textContent.trim();
      if (!text) {
        return;
      }

      node.setAttribute("title", text);
    });
  });
})();
