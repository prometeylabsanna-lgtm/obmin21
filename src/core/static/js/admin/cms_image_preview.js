(function () {
  function bindInput(input) {
    if (input.dataset.cmsImageBound) return;
    input.dataset.cmsImageBound = '1';
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      var wrap = input.closest('[data-cms-image]');
      if (!wrap || !file || (file.type && file.type.indexOf('image/') !== 0)) return;
      var img = wrap.querySelector('[data-cms-image-preview]');
      var frame = wrap.querySelector('.cms-image__frame');
      var placeholder = wrap.querySelector('[data-cms-image-placeholder]');
      if (img.dataset.objectUrl) {
        URL.revokeObjectURL(img.dataset.objectUrl);
      }
      var url = URL.createObjectURL(file);
      img.dataset.objectUrl = url;
      img.src = url;
      img.hidden = false;
      img.classList.remove('is-empty');
      if (frame) frame.classList.remove('is-empty');
      if (placeholder) placeholder.hidden = true;
    });
  }

  function bindAll(root) {
    (root || document).querySelectorAll('[data-cms-image-input]').forEach(bindInput);
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindAll(document);
  });
  document.body.addEventListener('htmx:afterSwap', function (event) {
    bindAll(event.target);
  });
})();
