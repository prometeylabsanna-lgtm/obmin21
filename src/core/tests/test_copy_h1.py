import csv
import tempfile
from io import StringIO
from pathlib import Path

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from src.blog.models import Category, Post
from src.core.models import SiteSettings


def _csv(rows):
    tmp = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False, encoding='utf-8', newline='')
    w = csv.writer(tmp)
    w.writerow(['slug', 'status', 'h1a', 'h1b'])
    w.writerows(rows)
    tmp.close()
    return tmp.name


class ApplyCopyH1Tests(TestCase):
    def setUp(self):
        cache.clear()
        SiteSettings.objects.get_or_create(pk=1)
        self.cat = Category.objects.create(name='C', slug='c')

    def _post(self, slug, **kw):
        return Post.objects.create(
            category=self.cat, title=f'T {slug}', slug=slug, body='Текст статті.',
            status=Post.Status.PUBLISHED, exchange_safe=True, **kw,
        )

    def _run(self, path, *args):
        out = StringIO()
        call_command('apply_copy_h1', '--csv', path, *args, stdout=out)
        return out.getvalue()

    def test_dry_run_writes_nothing_apply_fills_only(self):
        a = self._post('a')
        b = self._post('b', layout_mode={'h1a': 'Своє', 'lead': 'L'})
        path = _csv([
            ['a', 'published', 'Нове A', 'хвіст A'],
            ['b', 'published', 'Нове B', 'хвіст B'],
            ['chernetka-seo', 'draft', '□ x', '□ y'],
            ['missing', 'draft', 'M', 'N'],
            ['a2', 'draft', '', 'X'],
        ])
        out = self._run(path)
        self.assertIn('dry-run: applied=2 skipped=3', out)
        a.refresh_from_db()
        self.assertIsNone(a.layout_mode)
        out = self._run(path, '--apply')
        self.assertIn('applied: applied=2 skipped=3', out)
        a.refresh_from_db(); b.refresh_from_db()
        self.assertEqual(a.layout_mode, {'h1a': 'Нове A', 'h1b': 'хвіст A'})
        self.assertEqual(b.layout_mode, {'h1a': 'Своє', 'h1b': 'хвіст B', 'lead': 'L'})
        out = self._run(path, '--apply')
        self.assertIn('applied: applied=0 skipped=5', out)

    def test_default_csv_parses(self):
        out = self._run(str(Path(__file__).resolve().parents[2] / 'blog' / 'data' / 'copy_h1_2026_11_03.csv'))
        self.assertIn('skipped=17', out)  # no posts in test DB

    def test_exchange_only_renders_layout_mode_h1(self):
        post = self._post('eo-h1', layout_mode={'h1a': 'Долар чи євро:', 'h1b': 'у чому зберігати'})
        SiteSettings.objects.filter(pk=1).update(exchange_only=True)
        cache.clear()
        r = self.client.get(reverse('blog:post_detail', kwargs={'slug': post.slug}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['art']['layout_mode']['h1a'], 'Долар чи євро:')
        self.assertContains(r, 'Долар чи євро: <span class="u-accent">у чому зберігати</span>', html=False)


class ApplyCopyH1ForceTests(ApplyCopyH1Tests):
    def test_force_single_slug_overwrites_only_that_slug(self):
        a = self._post('a', layout_mode={'h1a': 'Старе', 'h1b': 'хвіст'})
        b = self._post('b', layout_mode={'h1a': 'Своє B'})
        path = _csv([['a', 'published', 'Нове', 'хвіст'], ['b', 'published', 'B', 'b2']])
        out = self._run(path, '--slug', 'a', '--force', '--apply')
        self.assertIn('applied: applied=1 skipped=0', out)
        a.refresh_from_db(); b.refresh_from_db()
        self.assertEqual(a.layout_mode, {'h1a': 'Нове', 'h1b': 'хвіст'})
        self.assertEqual(b.layout_mode, {'h1a': 'Своє B'})

    def test_force_without_slug_is_rejected(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            self._run(_csv([]), '--force')
