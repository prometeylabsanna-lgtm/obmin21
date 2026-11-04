(function () {
  var LABEL_MORE = 'Інші дії';
  var LABEL_SEARCH = 'Шукати';
  var LABEL_DATE = 'Обрати дату';
  var LABEL_TIME = 'Обрати час';
  var LABEL_RELATED = "Дії зі зв'язаним записом";

  function iconName(el) {
    return (el.textContent || '').replace(/\s+/g, '');
  }

  function setMissing(el, name, value) {
    if (!el.hasAttribute(name)) {
      el.setAttribute(name, value);
    }
  }

  function labelPair(el, label) {
    setMissing(el, 'aria-label', label);
    setMissing(el, 'title', label);
  }

  function hasDirectIcon(el, name) {
    var kids = el.children;
    var i;
    var kid;
    for (i = 0; i < kids.length; i += 1) {
      kid = kids[i];
      if (
        kid.classList &&
        kid.classList.contains('material-symbols-outlined') &&
        iconName(kid) === name
      ) {
        return true;
      }
    }
    return false;
  }

  function labelMoreHoriz() {
    var controls = document.querySelectorAll('a, button');
    var i;
    for (i = 0; i < controls.length; i += 1) {
      if (hasDirectIcon(controls[i], 'more_horiz')) {
        labelPair(controls[i], LABEL_MORE);
      }
    }
  }

  function labelSearch() {
    var button = document.getElementById('searchbar-submit');
    if (button && button.tagName === 'BUTTON') {
      labelPair(button, LABEL_SEARCH);
    }
  }

  function labelShortcuts(selector, label) {
    var links = document.querySelectorAll(selector);
    var i;
    for (i = 0; i < links.length; i += 1) {
      labelPair(links[i], label);
    }
  }

  function labelRelated() {
    var wrappers = document.querySelectorAll('.related-widget-wrapper');
    var i;
    var scopes;
    var s;
    var icons;
    var j;
    var trigger;
    var tag;
    for (i = 0; i < wrappers.length; i += 1) {
      scopes = [wrappers[i]];
      if (wrappers[i].parentElement) {
        scopes.push(wrappers[i].parentElement);
      }
      for (s = 0; s < scopes.length; s += 1) {
        icons = scopes[s].querySelectorAll('span.material-symbols-outlined');
        for (j = 0; j < icons.length; j += 1) {
          if (iconName(icons[j]) !== 'more_vert') {
            continue;
          }
          trigger = icons[j].parentElement;
          if (!trigger) {
            continue;
          }
          labelPair(trigger, LABEL_RELATED);
          tag = trigger.tagName;
          if (tag !== 'A' && tag !== 'BUTTON') {
            setMissing(trigger, 'role', 'button');
            setMissing(trigger, 'tabindex', '0');
          }
        }
      }
    }
  }

  function hideIcons() {
    var hosts = document.querySelectorAll('a, button, [role="button"]');
    var i;
    var icons;
    var j;
    for (i = 0; i < hosts.length; i += 1) {
      icons = hosts[i].querySelectorAll('span.material-symbols-outlined, .material-icons');
      for (j = 0; j < icons.length; j += 1) {
        setMissing(icons[j], 'aria-hidden', 'true');
      }
    }
  }

  function apply() {
    labelMoreHoriz();
    labelSearch();
    labelShortcuts('a[id^="calendarlink"]', LABEL_DATE);
    labelShortcuts('a[id^="clocklink"]', LABEL_TIME);
    labelRelated();
    hideIcons();
  }

  function boot() {
    var pending = false;
    apply();
    if (!document.body) {
      return;
    }
    var observer = new MutationObserver(function () {
      if (pending) {
        return;
      }
      pending = true;
      requestAnimationFrame(function () {
        pending = false;
        apply();
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
}());
