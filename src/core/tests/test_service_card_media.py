import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

_ROOT = Path(settings.BASE_DIR)
_CSS = _ROOT / 'src/core/static/css/components/home.css'
_BASE = _ROOT / 'templates/base.html'
_CSS_VERSION = 37
_LINK = "{% static 'css/components/home.css' %}?v="


def _blocks(css, selector):
    pattern = re.compile(
        r'(?:^|[{},])\s*%s\s*\{([^}]*)\}' % re.escape(selector),
        re.M,
    )
    return pattern.findall(css)


class ServiceCardMediaTests(SimpleTestCase):
    def test_media_covers_any_image_and_css_version_is_bumped(self):
        css = _CSS.read_text(encoding='utf-8')
        base = _BASE.read_text(encoding='utf-8')
        media = '\n'.join(_blocks(css, '.svc-card__media'))
        image = '\n'.join(_blocks(css, '.svc-card__media img'))
        cards = '\n'.join(_blocks(css, '.svc-card'))

        self.assertTrue(media.strip())
        self.assertIn('aspect-ratio: 3 / 2', media)
        self.assertNotRegex(media, r'height:\s*\d+px')
        self.assertIn('width: 100%', media)
        self.assertIn('min-width: 0', media)

        self.assertTrue(image.strip())
        self.assertIn('width: 100%', image)
        self.assertIn('height: 100%', image)
        self.assertIn('object-fit: cover', image)
        self.assertNotIn('!important', image)
        self.assertNotIn('!important', media)

        self.assertIn('min-width: 0', cards)
        self.assertRegex(cards, r'flex:\s*0\s+0\s+calc\(')

        self.assertIn(_LINK + str(_CSS_VERSION), base)
        self.assertNotIn(_LINK + str(_CSS_VERSION - 1), base)
