#!/usr/bin/env python3
"""Перевірка горизонтального переповнення адмінки Unfold на вузьких ширинах."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

from admin_mobile_check_2 import MEASURE, SHELL_CODE, TABS

ROOT = Path(__file__).resolve().parents[1]
MANAGE = ROOT / 'manage.py'
PY = ROOT / '.venv' / 'bin' / 'python'
DEFAULT_PREFIX = 'admin/'
LOOPBACK = {'127.0.0.1', 'localhost', '::1'}


def normalize_prefix(value: str) -> str:
    text = (value or '').strip().lstrip('/')
    if not text:
        text = DEFAULT_PREFIX.strip('/')
    if not text.endswith('/'):
        text += '/'
    return text


def scrub(text: str, secret: str) -> str:
    if not text:
        return ''
    if secret:
        text = text.replace(secret, '***')
    return text


def extract_json(text: str) -> dict:
    start = text.find('{')
    end = text.rfind('}')
    if start < 0 or end < start:
        raise RuntimeError('shell не повернув JSON')
    return json.loads(text[start:end + 1])


def prepare_pages(prefix: str, password: str) -> list[dict]:
    if not PY.is_file():
        raise RuntimeError('немає .venv/bin/python')
    env = os.environ.copy()
    env['ADMIN_URL'] = prefix
    env.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.develop')
    proc = subprocess.run(
        [str(PY), str(MANAGE), 'shell', '-c', SHELL_CODE],
        input=password + '\n',
        text=True,
        capture_output=True,
        cwd=str(ROOT),
        env=env,
        timeout=180,
        check=False,
    )
    if proc.returncode != 0:
        detail = scrub((proc.stderr or proc.stdout or '').strip(), password)
        raise RuntimeError(detail or 'manage.py shell завершився з помилкою')
    payload = extract_json(proc.stdout or '')
    pages = payload.get('pages') or []
    if not pages:
        raise RuntimeError('порожній список сторінок')
    return pages


def wait_server(base: str, prefix: str) -> None:
    url = urljoin(base.rstrip('/') + '/', prefix + 'login/')
    last = 'немає відповіді'
    for _ in range(30):
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status < 500:
                    return
                last = str(response.status)
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                return
            last = str(exc.code)
        except Exception as exc:
            last = exc.__class__.__name__
        time.sleep(0.4)
    raise RuntimeError('локальний сервер недоступний: ' + last)


def parse_widths(raw: str) -> list[int]:
    widths = []
    for part in raw.split(','):
        part = part.strip()
        if not part:
            continue
        widths.append(int(part))
    if not widths:
        raise RuntimeError('порожній список ширин')
    return widths


def shot_name(width: int, path: str, tab: str) -> str:
    raw = f'{width}__{path.strip("/")}__{tab}'
    raw = re.sub(r'[^\w.\-]+', '_', raw, flags=re.UNICODE)
    return raw[:180] + '.png'


def wait_ready(page, rich: bool = False) -> None:
    page.wait_for_function(
        "() => !document.documentElement.hasAttribute('x-cloak')",
        timeout=15000,
    )
    try:
        page.wait_for_function("() => document.fonts.status === 'loaded'", timeout=8000)
    except Exception:
        pass
    if rich or page.locator('script[src*="tinymce"], .tox-tinymce').count():
        try:
            page.wait_for_selector('.tox-tinymce', timeout=8000)
        except Exception:
            pass
    page.wait_for_timeout(120)


def record(rows: list[str], ok: bool, width: int, path: str, tab: str, items: list[str]) -> bool:
    status = 'PASS' if ok else 'FAIL'
    detail = ''
    if items and not ok:
        detail = ' | ' + ' | '.join(items[:5])
    line = f'{status}\t{width}\t{path}\t{tab}{detail}'
    rows.append(line)
    print(line, flush=True)
    return ok


def login(page, base: str, prefix: str, password: str) -> None:
    url = urljoin(base.rstrip('/') + '/', prefix + 'login/')
    page.goto(url, wait_until='domcontentloaded', timeout=30000)
    page.locator('input[name="username"]').fill('local_qa')
    page.locator('input[name="password"]').fill(password)
    page.locator('#login-form button[type="submit"]').click()
    page.wait_for_selector('#main', timeout=20000)
    if '/login/' in page.url:
        raise RuntimeError('вхід не вдався')


def open_page(page, base: str, path: str, width: int) -> None:
    page.set_viewport_size({'width': width, 'height': 900})
    target = urljoin(base.rstrip('/') + '/', path.lstrip('/'))
    response = page.goto(target, wait_until='domcontentloaded', timeout=30000)
    wait_ready(page)
    status = response.status if response is not None else 0
    if status >= 400:
        raise RuntimeError(f'HTTP {status}')
    if '/login/' in page.url:
        raise RuntimeError('сесію скинуто')


def click_tabs(page, base: str, path: str, width: int, rows: list[str], out_dir: Path | None) -> bool:
    ok = True
    clicked: set[tuple] = set()
    origin = page.url.split('#', 1)[0]
    for _ in range(40):
        tabs = page.evaluate(TABS)
        pending = []
        for tab in tabs:
            key = (tab['scope'], tab['text'], tab['href'], tab['nth'])
            if key not in clicked:
                pending.append((key, tab))
        if not pending:
            break
        key, tab = pending[0]
        clicked.add(key)
        label = tab['text'] or tab['scope']
        try:
            locator = page.locator(tab['selector']).nth(tab['nth'])
            href = tab['href'] or ''
            if href.startswith('/') or href.startswith('http'):
                with page.expect_navigation(wait_until='domcontentloaded', timeout=15000):
                    locator.click(timeout=5000)
                wait_ready(page)
            else:
                locator.click(timeout=5000)
                page.wait_for_timeout(180)
                wait_ready(page, rich=False)
        except Exception as exc:
            ok = record(rows, False, width, path, label, [exc.__class__.__name__]) and ok
            continue
        passed, items = measure(page, width)
        save_shot(page, out_dir, width, path, label)
        ok = record(rows, passed, width, path, label, items) and ok
        if page.url.split('#', 1)[0] != origin:
            page.goto(origin, wait_until='domcontentloaded', timeout=30000)
            wait_ready(page)
    return ok


def measure(page, width: int) -> tuple[bool, list[str]]:
    data = page.evaluate(MEASURE, width < 768)
    return bool(data.get('ok')), list(data.get('items') or [])


def save_shot(page, out_dir: Path | None, width: int, path: str, tab: str) -> None:
    if out_dir is None:
        return
    target = out_dir / shot_name(width, path, tab)
    full = ('/city/' in path) or ('/post/' in path) or ('contactcity' in path)
    try:
        page.screenshot(path=str(target), full_page=full, timeout=20000)
    except Exception:
        try:
            page.screenshot(path=str(target), full_page=False, timeout=10000)
        except Exception:
            return


def run_checks(base: str, prefix: str, widths: list[int], pages: list[dict], password: str, out_dir: Path | None) -> list[str]:
    from playwright.sync_api import sync_playwright

    rows: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': widths[0], 'height': 900},
            locale='uk-UA',
            device_scale_factor=1,
        )
        page = context.new_page()
        page.set_default_timeout(20000)
        try:
            login(page, base, prefix, password)
            for info in pages:
                path = info['path']
                for width in widths:
                    try:
                        open_page(page, base, path, width)
                    except Exception as exc:
                        record(rows, False, width, path, 'завантаження', [str(exc)[:180]])
                        continue
                    passed, items = measure(page, width)
                    save_shot(page, out_dir, width, path, 'початкова')
                    record(rows, passed, width, path, 'початкова', items)
                    if info.get('tabs') and width:
                        click_tabs(page, base, path, width, rows, out_dir)
        finally:
            context.close()
            browser.close()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description='Перевірка мобільної верстки адмінки')
    parser.add_argument('--base', default='http://127.0.0.1:8791')
    parser.add_argument('--admin-prefix', default=DEFAULT_PREFIX)
    parser.add_argument('--widths', default='360,390,430,1440')
    parser.add_argument('--out', default='')
    parser.add_argument('--report', default='')
    args = parser.parse_args()

    host = urlparse(args.base).hostname or ''
    if host not in LOOPBACK:
        print('Дозволено лише локальний хост', file=sys.stderr)
        return 2
    prefix = normalize_prefix(args.admin_prefix)
    try:
        widths = parse_widths(args.widths)
        wait_server(args.base, prefix)
        password = secrets.token_urlsafe(18)
        pages = prepare_pages(prefix, password)
        out_dir = Path(args.out) if args.out else None
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
        rows = run_checks(args.base, prefix, widths, pages, password, out_dir)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    failed = sum(1 for row in rows if row.startswith('FAIL'))
    passed = sum(1 for row in rows if row.startswith('PASS'))
    summary = f'RESULT pass={passed} fail={failed}'
    text = '\n'.join(rows + [summary]) + '\n'
    sys.stdout.write(text)
    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(text, encoding='utf-8')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
