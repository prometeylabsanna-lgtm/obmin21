"""Fill exchange-only article H1 (Post.layout_mode h1a/h1b) from the copy CSV.

Dry-run by default; ``--apply`` writes. Fill-only: non-empty values stay.
"""
import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from src.blog.models import Post

DEFAULT_CSV = Path(__file__).resolve().parents[2] / 'data' / 'copy_h1_2026_11_03.csv'
SKIP_SLUGS = {'chernetka-seo'}
KEYS = ('h1a', 'h1b')


def _current(raw):
    """Return (dict, ok). ok=False when stored value is unreadable non-empty."""
    if raw in (None, '', {}):
        return {}, True
    if isinstance(raw, dict):
        return dict(raw), True
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}, False
        if isinstance(parsed, dict):
            return parsed, True
    return {}, False


class Command(BaseCommand):
    help = 'Fill Post.layout_mode h1a/h1b from copy CSV (dry-run unless --apply).'

    def add_arguments(self, parser):
        parser.add_argument('--csv', default=str(DEFAULT_CSV))
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--slug', default='', help='Process only this slug.')
        parser.add_argument(
            '--force', action='store_true',
            help='Overwrite existing h1a/h1b (requires --slug).',
        )

    def handle(self, *args, **opts):
        path = Path(opts['csv'])
        if not path.exists():
            raise CommandError(f'CSV not found: {path}')
        with path.open(encoding='utf-8-sig', newline='') as fh:
            rows = list(csv.DictReader(fh))
        apply = opts['apply']
        only = (opts.get('slug') or '').strip()
        force = opts.get('force')
        if force and not only:
            raise CommandError('--force requires --slug')
        if only:
            rows = [r for r in rows if (r.get('slug') or '').strip() == only]
            if not rows:
                raise CommandError(f'slug not in CSV: {only}')
        applied = skipped = 0
        with transaction.atomic():
            for row in rows:
                slug = (row.get('slug') or '').strip()
                h1a = (row.get('h1a') or '').strip()
                h1b = (row.get('h1b') or '').strip()
                if slug in SKIP_SLUGS or not h1a:
                    skipped += 1
                    self.stdout.write(f'SKIP {slug}: placeholder/empty h1a')
                    continue
                post = Post.objects.filter(slug=slug).first()
                if post is None:
                    skipped += 1
                    self.stdout.write(f'SKIP {slug}: post not found')
                    continue
                data, ok = _current(post.layout_mode)
                if not ok:
                    skipped += 1
                    self.stdout.write(f'SKIP {slug}: layout_mode is not a JSON object')
                    continue
                changes = {}
                for key, value in zip(KEYS, (h1a, h1b)):
                    have = data.get(key)
                    filled = isinstance(have, str) and have.strip()
                    if value and (not filled or (force and have.strip() != value)):
                        changes[key] = value
                if not changes:
                    skipped += 1
                    self.stdout.write(f'SKIP {slug}: already filled')
                    continue
                applied += 1
                verb = 'APPLY' if apply else 'WOULD APPLY'
                self.stdout.write(f'{verb} {slug}: {changes}')
                if apply:
                    data.update(changes)
                    post.layout_mode = data
                    post.save(update_fields=['layout_mode'])
        mode = 'applied' if apply else 'dry-run'
        self.stdout.write(f'{mode}: applied={applied} skipped={skipped}')
