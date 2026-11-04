(function () {
  'use strict';

  function initFaq() {
    document.querySelectorAll('[data-faq]').forEach(function (list) {
      list.querySelectorAll('.faq-card__q, .faq-item__q').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var item = btn.closest('.faq-card, .faq-item');
          if (!item) return;
          var open = item.classList.contains('is-open');
          list.querySelectorAll('.faq-card, .faq-item').forEach(function (el) {
            el.classList.remove('is-open');
            var q = el.querySelector('.faq-card__q, .faq-item__q');
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

  var sliderControllers = new WeakMap();
  var sliderTracks = [];
  var SLIDER_CARDS = '.review-slide, .article-slide, .svc-card';

  function initSliders() {
    document.querySelectorAll('[data-slider-nav]').forEach(function (nav) {
      if (nav.getAttribute('data-slider-bound') === '1') return;
      var name = nav.getAttribute('data-slider-nav');
      if (!name || !/^[A-Za-z0-9_-]+$/.test(name)) return;
      var track = document.querySelector('[data-slider="' + name + '"]');
      if (!track) return;
      nav.setAttribute('data-slider-bound', '1');
      sliderController(track, name).bind(nav);
    });
  }

  function sliderController(track, name) {
    var existing = sliderControllers.get(track);
    if (existing) return existing;
    var created = createSliderController(track, name);
    sliderControllers.set(track, created);
    sliderTracks.push(track);
    return created;
  }

  function releaseDetachedSliders() {
    sliderTracks = sliderTracks.filter(function (track) {
      if (track.isConnected) return true;
      var ctrl = sliderControllers.get(track);
      if (ctrl) {
        ctrl.destroy();
        sliderControllers.delete(track);
      }
      return false;
    });
  }

  function offsetInTrack(track, card) {
    if (card.offsetParent === track) return card.offsetLeft;
    var left = 0;
    var node = card;
    while (node && node !== track) {
      left += node.offsetLeft || 0;
      node = node.offsetParent;
    }
    if (node === track) return left;
    var cardBox = card.getBoundingClientRect();
    var trackBox = track.getBoundingClientRect();
    return cardBox.left - trackBox.left + track.scrollLeft;
  }

  function clampLeft(left, max) {
    if (!(left > 0)) left = 0;
    if (left > max) left = max;
    return left;
  }

  function sliderState(track) {
    var cards = track.querySelectorAll(SLIDER_CARDS);
    var layoutMax = track.scrollWidth - track.clientWidth;
    if (!(layoutMax > 0)) layoutMax = 0;
    var positions = [];
    var origin = 0;
    var i;
    for (i = 0; i < cards.length; i++) {
      var offset = offsetInTrack(track, cards[i]);
      if (i === 0) origin = offset;
      positions.push(offset - origin);
    }
    var max = layoutMax;
    if (track.getAttribute('data-slider') === 'articles' && cards.length) {
      var last = cards[cards.length - 1];
      if (last.offsetParent === track) {
        var padRight = parseFloat(window.getComputedStyle(track).paddingRight) || 0;
        var contentMax = last.offsetLeft + last.offsetWidth + padRight - track.clientWidth - origin;
        if (!(contentMax > 0)) contentMax = 0;
        if (contentMax < max) max = contentMax;
      }
    }
    for (i = 0; i < positions.length; i++) {
      positions[i] = clampLeft(positions[i], max);
    }
    var lastReachableIndex = 0;
    for (i = 0; i < positions.length; i++) {
      if (i > 0 && positions[i] <= positions[i - 1] + 0.5) break;
      lastReachableIndex = i;
      if (positions[i] >= max - 0.5) break;
    }
    return {
      positions: positions,
      max: max,
      lastReachableIndex: lastReachableIndex
    };
  }

  function indexFromScroll(track, state) {
    var left = clampLeft(track.scrollLeft, state.max);
    var index = 0;
    var best = Infinity;
    var last = state.lastReachableIndex;
    var i;
    for (i = 0; i <= last && i < state.positions.length; i++) {
      var dist = Math.abs(state.positions[i] - left);
      if (dist < best) {
        best = dist;
        index = i;
      }
    }
    return index;
  }

  function createSliderController(track, name) {
    var pendingIndex = null;
    var pendingUntil = 0;
    var recoveries = 0;
    var clampAttempts = 0;
    var settling = false;
    var rafId = 0;
    var settleTimer = 0;
    var resizeTimer = 0;

    function clampIndex(index, state) {
      if (index < 0) index = 0;
      if (index > state.lastReachableIndex) index = state.lastReachableIndex;
      return index;
    }

    function edges(state) {
      var index = pendingIndex === null ? indexFromScroll(track, state) : pendingIndex;
      index = clampIndex(index, state);
      var atStart;
      var atEnd;
      if (pendingIndex !== null) {
        atStart = index <= 0;
        atEnd = index >= state.lastReachableIndex;
      } else {
        var left = track.scrollLeft;
        if (left < 0) left = 0;
        atStart = left <= 8;
        atEnd = left >= state.max - 4;
      }
      if (!state.positions.length || !(state.max > 4)) {
        atStart = true;
        atEnd = true;
      }
      return { index: index, atStart: atStart, atEnd: atEnd };
    }

    function applyArrow(btn, atEdge) {
      if (!btn) return;
      btn.classList.toggle('is-active', !atEdge);
      if (atEdge) {
        btn.disabled = true;
        btn.setAttribute('aria-disabled', 'true');
      } else {
        btn.disabled = false;
        btn.removeAttribute('aria-disabled');
      }
    }

    function sync() {
      if (!track.isConnected) return;
      var edge = edges(sliderState(track));
      document.querySelectorAll('[data-slider-nav="' + name + '"]').forEach(function (item) {
        applyArrow(item.querySelector('[data-slider-prev]'), edge.atStart);
        applyArrow(item.querySelector('[data-slider-next]'), edge.atEnd);
      });
    }

    function scheduleSettle() {
      window.clearTimeout(settleTimer);
      settleTimer = window.setTimeout(finish, 120);
    }

    function finish() {
      if (settling || !track.isConnected) return;
      settling = true;
      try {
        var state = sliderState(track);
        var left = track.scrollLeft;
        if (pendingIndex !== null) {
          var want = clampIndex(pendingIndex, state);
          var target = clampLeft(state.positions[want] || 0, state.max);
          var inRange = left >= -1 && left <= state.max + 1;
          var arrived = inRange && indexFromScroll(track, state) === want;
          if (!arrived && Date.now() < pendingUntil) {
            if (recoveries < 1 && !inRange) {
              recoveries += 1;
              track.scrollTo({ left: target, behavior: 'smooth' });
            }
            scheduleSettle();
            sync();
            return;
          }
          pendingIndex = null;
          recoveries = 0;
          left = track.scrollLeft;
        }
        if (left < -1 || left > state.max + 1) {
          if (clampAttempts < 3) {
            clampAttempts += 1;
            track.scrollTo({ left: left < 0 ? 0 : state.max, behavior: 'auto' });
          }
        } else {
          clampAttempts = 0;
        }
        sync();
      } finally {
        settling = false;
      }
    }

    function go(dir) {
      var state = sliderState(track);
      if (!state.positions.length) return;
      var base = pendingIndex === null ? indexFromScroll(track, state) : pendingIndex;
      var index = clampIndex(base + dir, state);
      var left = clampLeft(state.positions[index] || 0, state.max);
      pendingIndex = index;
      pendingUntil = Date.now() + 900;
      recoveries = 0;
      track.scrollTo({ left: left, behavior: 'smooth' });
      sync();
      scheduleSettle();
    }

    function onScroll() {
      if (rafId) return;
      rafId = window.requestAnimationFrame(function () {
        rafId = 0;
        if (!track.isConnected) return;
        sync();
        scheduleSettle();
      });
    }

    function onResize() {
      if (!track.isConnected) {
        window.removeEventListener('resize', onResize);
        if (window.visualViewport) {
          window.visualViewport.removeEventListener('resize', onResize);
        }
        return;
      }
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(sync, 150);
    }

    function cancelPending() {
      if (pendingIndex === null) return;
      pendingIndex = null;
      recoveries = 0;
      sync();
    }

    track.setAttribute('data-slider-bound', '1');
    track.addEventListener('scroll', onScroll, { passive: true });
    if ('onscrollend' in window) {
      track.addEventListener('scrollend', function () {
        window.clearTimeout(settleTimer);
        finish();
      }, { passive: true });
    }
    track.addEventListener('touchstart', cancelPending, { passive: true });
    track.addEventListener('pointerdown', cancelPending, { passive: true });
    window.addEventListener('resize', onResize);
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', onResize);
    }
    sync();

    return {
      destroy: function () {
        window.removeEventListener('resize', onResize);
        if (window.visualViewport) {
          window.visualViewport.removeEventListener('resize', onResize);
        }
        window.clearTimeout(settleTimer);
        window.clearTimeout(resizeTimer);
        if (rafId) window.cancelAnimationFrame(rafId);
      },
      bind: function (nav) {
        var prev = nav.querySelector('[data-slider-prev]');
        var next = nav.querySelector('[data-slider-next]');
        if (prev) {
          prev.addEventListener('click', function () {
            if (prev.disabled || prev.getAttribute('aria-disabled') === 'true') return;
            if (edges(sliderState(track)).atStart) return;
            go(-1);
          });
        }
        if (next) {
          next.addEventListener('click', function () {
            if (next.disabled || next.getAttribute('aria-disabled') === 'true') return;
            if (edges(sliderState(track)).atEnd) return;
            go(1);
          });
        }
        sync();
      }
    };
  }

  function swapHasSlider(target) {
    if (!target || target.nodeType !== 1) return false;
    if (target.matches && target.matches('[data-slider], [data-slider-nav]')) return true;
    return !!(target.querySelector && target.querySelector('[data-slider], [data-slider-nav]'));
  }

  function initPromo() {
    var root = document.querySelector('[data-promo]');
    if (!root) return;
    var slides = Array.prototype.slice.call(root.querySelectorAll('[data-promo-slide]'));
    var dots = Array.prototype.slice.call(root.querySelectorAll('[data-promo-dot]'));
    if (!slides.length) return;
    var index = 0;
    var timer = 0;

    function autoplayOn() {
      if (root.getAttribute('data-autoplay') === '0') return false;
      if (root.getAttribute('data-slides') === '1') return false;
      return slides.length > 1;
    }

    function show(next) {
      index = (next + slides.length) % slides.length;
      slides.forEach(function (slide, i) {
        slide.classList.toggle('is-active', i === index);
      });
      dots.forEach(function (dot, i) {
        dot.classList.toggle('is-active', i === index);
        dot.setAttribute('aria-current', i === index ? 'true' : 'false');
      });
    }

    function start() {
      window.clearInterval(timer);
      if (!autoplayOn()) return;
      timer = window.setInterval(function () {
        if (document.hidden || root.dataset.pause === '1') return;
        show(index + 1);
      }, 4000);
    }

    dots.forEach(function (dot, i) {
      dot.addEventListener('click', function (event) {
        event.stopPropagation();
        show(i);
        start();
      });
    });

    root.addEventListener('click', function (event) {
      if (window.innerWidth >= 768) return;
      if (event.target.closest('a, button, [data-promo-dot]')) return;
      var slide = slides[index];
      if (!slide) return;
      if (slide.getAttribute('data-modal') === '1') {
        var opener = slide.querySelector('[data-open-modal]');
        if (opener) opener.click();
        return;
      }
      var href = slide.getAttribute('data-href');
      if (!href) return;
      if (slide.getAttribute('data-blank') === '1') {
        window.open(href, '_blank', 'noopener');
      } else {
        window.location.href = href;
      }
    });

    root.addEventListener('mouseenter', function () {
      root.dataset.pause = '1';
    });
    root.addEventListener('mouseleave', function () {
      delete root.dataset.pause;
    });
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) start();
    });
    show(0);
    start();
  }

  document.addEventListener('DOMContentLoaded', function () {
    initFaq();
    initSliders();
    initPromo();
  });

  if (document.body) {
    document.body.addEventListener('htmx:afterSwap', function (evt) {
      var target = evt.target;
      if (!swapHasSlider(target) && evt.detail) target = evt.detail.target;
      if (!swapHasSlider(target)) return;
      releaseDetachedSliders();
      initSliders();
    });
  }
})();
