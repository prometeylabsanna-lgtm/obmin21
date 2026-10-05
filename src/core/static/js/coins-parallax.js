(function () {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (window.matchMedia('(hover: none)').matches) return;

  function bind(scene) {
    var host = scene.closest('[data-coin-host]') || scene;
    var layers = scene.querySelectorAll('[data-depth]');
    if (!layers.length) return;

    function move(e) {
      var rect = host.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      var nx = (e.clientX - rect.left) / rect.width - 0.5;
      var ny = (e.clientY - rect.top) / rect.height - 0.5;
      layers.forEach(function (el) {
        var d = Number(el.getAttribute('data-depth')) || 0;
        el.style.transform = 'translate3d(' + (nx * d) + 'px,' + (ny * d) + 'px,0)';
      });
    }

    function leave() {
      layers.forEach(function (el) {
        el.style.transform = '';
      });
    }

    host.addEventListener('mousemove', move);
    host.addEventListener('mouseleave', leave);
  }

  document.querySelectorAll('[data-coin-scene]').forEach(bind);
})();
