const STATS_SELECTOR = '.stats-section [data-count-up]';
const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';
const MOBILE_QUERY = '(max-width: 767px)';
const DURATION_MOBILE_MS = 1200;
const DURATION_DESKTOP_MS = 1600;
const STAGGER_MS = 120;

function matchesQuery(query) {
  return Boolean(window.matchMedia && window.matchMedia(query).matches);
}

function prefersReducedMotion() {
  return matchesQuery(REDUCED_MOTION_QUERY);
}

function animationDuration() {
  if (matchesQuery(MOBILE_QUERY)) {
    return DURATION_MOBILE_MS;
  }
  return DURATION_DESKTOP_MS;
}

function parseStat(source) {
  const match = source.match(/\d+(?:[.,]\d+)?/);
  if (!match) {
    return null;
  }
  const token = match[0];
  const value = Number(token.replace(',', '.'));
  if (!Number.isFinite(value)) {
    return null;
  }
  const fraction = token.split(/[.,]/)[1] || '';
  return {
    source: source,
    value: value,
    decimals: fraction.length,
    comma: token.indexOf(',') !== -1,
    prefix: source.slice(0, match.index),
    suffix: source.slice(match.index + token.length),
  };
}

function frameText(parsed, current) {
  let digits;
  if (parsed.decimals > 0) {
    digits = current.toFixed(parsed.decimals);
    if (parsed.comma) {
      digits = digits.replace('.', ',');
    }
  } else {
    digits = String(Math.round(current));
  }
  return parsed.prefix + digits + parsed.suffix;
}

function showFinal(item) {
  item.el.textContent = item.parsed.source;
}

function animate(item, delay, duration) {
  const from = 0;
  let startedAt = null;
  item.el.textContent = frameText(item.parsed, from);

  function tick(now) {
    if (startedAt === null) {
      startedAt = now;
    }
    const elapsed = now - startedAt - delay;
    if (elapsed < 0) {
      window.requestAnimationFrame(tick);
      return;
    }
    const progress = Math.min(1, elapsed / duration);
    if (progress >= 1) {
      showFinal(item);
      return;
    }
    const eased = 1 - Math.pow(1 - progress, 4);
    const current = from + (item.parsed.value - from) * eased;
    item.el.textContent = frameText(item.parsed, current);
    window.requestAnimationFrame(tick);
  }

  window.requestAnimationFrame(tick);
}

function readItems(root) {
  const nodes = root.querySelectorAll(STATS_SELECTOR);
  const items = [];
  for (let index = 0; index < nodes.length; index += 1) {
    const el = nodes[index];
    const parsed = parseStat(el.textContent || '');
    if (parsed) {
      items.push({ el: el, parsed: parsed, played: false });
    }
  }
  return items;
}

function play(items) {
  if (!items.length) {
    return;
  }
  if (prefersReducedMotion() || typeof IntersectionObserver !== 'function') {
    items.forEach(showFinal);
    return;
  }

  const pending = items.slice();
  const observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) {
          return;
        }
        const item = pending.find(function (row) {
          return row.el === entry.target;
        });
        if (!item || item.played) {
          return;
        }
        item.played = true;
        observer.unobserve(item.el);
        if (pending.every(function (row) { return row.played; })) {
          observer.disconnect();
        }
        if (prefersReducedMotion()) {
          showFinal(item);
          return;
        }
        const order = pending.indexOf(item);
        animate(item, order * STAGGER_MS, animationDuration());
      });
    },
    { threshold: 0.25, rootMargin: '0px' },
  );

  pending.forEach(function (item) {
    observer.observe(item.el);
  });
}

function mount() {
  if (typeof document === 'undefined') {
    return;
  }
  play(readItems(document));
}

if (typeof document !== 'undefined' && document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mount);
} else {
  mount();
}
