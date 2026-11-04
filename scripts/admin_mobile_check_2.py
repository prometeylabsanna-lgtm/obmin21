"""Фрагменти shell і перевірок для admin_mobile_check.py."""

SHELL_CODE = r'''
import json
import sys

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse

engine = settings.DATABASES["default"]["ENGINE"]
if engine != "django.db.backends.sqlite3":
    sys.stderr.write("default database is not sqlite\n")
    sys.exit(2)

password = sys.stdin.read().strip()
if not password:
    sys.stderr.write("empty password\n")
    sys.exit(2)

User = get_user_model()
user, _created = User.objects.get_or_create(
    username="local_qa",
    defaults={"is_staff": True, "is_superuser": True, "is_active": True},
)
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.set_password(password)
user.save()

request = RequestFactory().get("/")
request.user = user

pages = [{"kind": "index", "path": reverse("admin:index"), "tabs": False}]
seen = {pages[0]["path"]}
apps = set()

for model, model_admin in list(admin.site._registry.items()):
    opts = model._meta
    apps.add(opts.app_label)
    try:
        changelist = reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
    except Exception:
        changelist = ""
    if changelist and changelist not in seen:
        seen.add(changelist)
        pages.append({"kind": "changelist", "path": changelist, "tabs": False})
    try:
        if model_admin.has_add_permission(request):
            add_path = reverse(f"admin:{opts.app_label}_{opts.model_name}_add")
            if add_path not in seen:
                seen.add(add_path)
                pages.append({"kind": "add", "path": add_path, "tabs": False})
    except Exception:
        pass
    obj = None
    try:
        obj = model.objects.order_by("pk").first()
    except Exception:
        obj = None
    if obj is not None and getattr(obj, "pk", None) is not None:
        try:
            change = reverse(
                f"admin:{opts.app_label}_{opts.model_name}_change",
                args=[obj.pk],
            )
        except Exception:
            change = ""
        if change and change not in seen:
            seen.add(change)
            pages.append({"kind": "change", "path": change, "tabs": True})

for app_label in sorted(apps):
    try:
        app_path = reverse("admin:app_list", kwargs={"app_label": app_label})
    except Exception:
        continue
    if app_path not in seen:
        seen.add(app_path)
        pages.append({"kind": "app_index", "path": app_path, "tabs": False})

sys.stdout.write(json.dumps({"pages": pages}, ensure_ascii=False))
'''

MEASURE = r'''
(mobile) => {
  const doc = document.documentElement;
  const body = document.body;
  doc.scrollLeft = 0;
  if (body) body.scrollLeft = 0;
  const pageOverflow = doc.scrollWidth > doc.clientWidth + 1
    || (body && body.scrollWidth > body.clientWidth + 1);
  if (!mobile) {
    return {
      ok: !pageOverflow,
      pageOverflow,
      items: pageOverflow ? ['documentElement scrollWidth'] : [],
    };
  }

  const hiddenCache = new Map();
  const skipTag = new Set([
    'SCRIPT', 'STYLE', 'LINK', 'META', 'TEMPLATE', 'NOSCRIPT', 'OPTION', 'OPTGROUP',
  ]);
  const shells = new Set([
    'page', 'main', 'content', 'content-main', 'changelist', 'header-inner', 'content-related',
  ]);

  function parentOf(el) {
    if (el.parentElement) return el.parentElement;
    const root = el.getRootNode();
    if (root && root.host) return root.host;
    return null;
  }

  function isHidden(el) {
    if (hiddenCache.has(el)) return hiddenCache.get(el);
    const style = getComputedStyle(el);
    let hidden = style.display === 'none'
      || style.visibility === 'hidden'
      || Number(style.opacity) === 0;
    if (!hidden) {
      const parent = parentOf(el);
      if (parent && parent.nodeType === 1 && parent !== doc) hidden = isHidden(parent);
    }
    hiddenCache.set(el, hidden);
    return hidden;
  }

  function hasBox(el) {
    const rect = el.getBoundingClientRect();
    return rect.width >= 0.5 && rect.height >= 0.5;
  }

  function isShown(el) {
    if (!el || el.nodeType !== 1) return false;
    if (skipTag.has(el.tagName)) return false;
    if (isHidden(el)) return false;
    return hasBox(el);
  }

  function scrollHost(el) {
    let node = parentOf(el);
    while (node && node !== doc) {
      if (node.nodeType === 1) {
        const ox = getComputedStyle(node).overflowX;
        if (ox === 'auto' || ox === 'scroll' || ox === 'overlay') return node;
      }
      node = parentOf(node);
    }
    return null;
  }

  function isTableWrapper(el) {
    if (!el || el.nodeType !== 1 || shells.has(el.id)) return false;
    const ox = getComputedStyle(el).overflowX;
    if (ox !== 'auto' && ox !== 'scroll' && ox !== 'overlay') return false;
    const table = el.querySelector('table');
    if (!table) return false;
    let node = table;
    let depth = 0;
    while (node && node !== el && depth < 8) {
      node = parentOf(node);
      depth += 1;
    }
    return node === el;
  }

  function selectorOf(el) {
    if (!el || el.nodeType !== 1) return '';
    if (el.id) return '#' + CSS.escape(el.id);
    const parts = [];
    let node = el;
    let guard = 0;
    while (node && node.nodeType === 1 && guard < 4) {
      let part = node.tagName.toLowerCase();
      const classes = [...node.classList].filter((name) => name && name.length < 48).slice(0, 2);
      if (classes.length) part += classes.map((name) => '.' + CSS.escape(name)).join('');
      const parent = node.parentElement;
      if (parent) {
        const same = [...parent.children].filter((child) => child.tagName === node.tagName);
        if (same.length > 1) part += ':nth-of-type(' + (same.indexOf(node) + 1) + ')';
      }
      parts.unshift(part);
      if (node.id) {
        parts[0] = '#' + CSS.escape(node.id);
        break;
      }
      node = parentOf(node);
      guard += 1;
    }
    return parts.join(' > ');
  }

  const nodes = [];
  function walk(root) {
    if (!root || !root.querySelectorAll) return;
    for (const el of root.querySelectorAll('*')) {
      nodes.push(el);
      if (el.shadowRoot) walk(el.shadowRoot);
    }
  }
  walk(body);

  const found = [];
  const seen = new Set();
  function add(el, kind) {
    const sel = selectorOf(el);
    const key = kind + '|' + sel;
    if (seen.has(key)) return;
    seen.add(key);
    const rect = el.getBoundingClientRect();
    const right = Math.max(0, Math.round(rect.right - window.innerWidth - 1));
    const scroll = Math.max(0, el.scrollWidth - el.clientWidth - 1);
    const amount = Math.max(right, scroll);
    if (amount <= 0 && kind === 'box') return;
    found.push({
      amount,
      text: sel + ' (' + kind + ' right+' + right + ' scroll+' + scroll + ')',
    });
  }

  for (const el of nodes) {
    if (!isShown(el)) continue;
    const rect = el.getBoundingClientRect();
    if (rect.right > window.innerWidth + 1) {
      const host = scrollHost(el);
      if (!host) add(el, 'box');
    }
    if (shells.has(el.id) || ['auto', 'scroll', 'overlay'].includes(getComputedStyle(el).overflowX)) {
      if (el.scrollWidth > el.clientWidth + 1 && !isTableWrapper(el)) add(el, 'scroll');
    }
    if (isTableWrapper(el) && rect.right > window.innerWidth + 1) add(el, 'wrap');
  }

  if (pageOverflow) {
    found.push({
      amount: doc.scrollWidth - doc.clientWidth,
      text: 'documentElement scroll ' + doc.scrollWidth + '/' + doc.clientWidth,
    });
  }
  found.sort((a, b) => b.amount - a.amount);
  const items = found.slice(0, 5).map((item) => item.text);
  return {ok: !pageOverflow && found.length === 0, pageOverflow, items};
}
'''

TABS = r'''
() => {
  const specs = [
    ['#tabs-items > a', 'unfold'],
    ['.cms-seg-tabs a', 'fieldset'],
    ['.cms-board-tabs a, .cms-board-tabs__btn, .cms-board-tabs button', 'board'],
  ];
  const hidden = (el) => {
    let node = el;
    while (node && node.nodeType === 1) {
      const style = getComputedStyle(node);
      if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) {
        return true;
      }
      node = node.parentElement;
    }
    const rect = el.getBoundingClientRect();
    return rect.width < 0.5 || rect.height < 0.5;
  };
  const tabs = [];
  for (const [selector, scope] of specs) {
    const list = [...document.querySelectorAll(selector)];
    list.forEach((el, nth) => {
      if (hidden(el)) return;
      tabs.push({
        selector,
        scope,
        nth,
        text: (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80),
        href: el.getAttribute('href') || '',
      });
    });
  }
  return tabs;
}
'''


