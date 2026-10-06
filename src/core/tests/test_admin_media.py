from io import BytesIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from src.content.models import HomePage
from src.core.admin_guidelines import text_limit_for
from src.core.media_webp import image_file_validator, to_webp


def _png(width=20, height=20):
    buf = BytesIO()
    Image.new('RGB', (width, height), (200, 40, 40)).save(buf, format='PNG')
    return SimpleUploadedFile('shot.png', buf.getvalue(), content_type='image/png')


class AdminMediaLimitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='tester',
            email='tester@example.com',
            password='pass-12345',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_admin_shows_image_and_text_hints(self):
        HomePage.load()
        promo = self.client.get(reverse('admin:content_homepromosettings_change', args=[1]))
        self.assertContains(promo, '1600×1200')
        self.assertContains(promo, '1,5 МБ')
        self.assertContains(promo, 'До 80 символів')
        header = self.client.get(reverse('admin:core_headersettings_changelist'), follow=True)
        self.assertContains(header, '800×400')
        self.assertContains(header, '0,5 МБ')

    def test_png_upload_becomes_webp(self):
        HomePage.load()
        url = reverse('admin:content_homepromosettings_change', args=[1])
        post = self.client.post(url, {
            'promo_kicker': 'USD та EUR',
            'promo_title': 'Вигідний курс',
            'promo_title_accent': 'USD та EUR',
            'promo_text': 'Обмінюйте валюту за актуальним курсом без зайвих кроків',
            'promo_button': 'Обрати валюту',
            'promo_image': _png(),
        }, follow=True)
        self.assertEqual(post.status_code, 200)
        home = HomePage.objects.get(pk=1)
        self.assertTrue(home.promo_image.name.endswith('.webp'))

    def test_rejects_oversize_file(self):
        huge = SimpleUploadedFile(
            'big.png',
            b'x' * (3 * 1024 * 1024),
            content_type='image/png',
        )
        with self.assertRaises(ValidationError) as caught:
            image_file_validator('promo_image')(huge)
        self.assertIn('завеликий', str(caught.exception))

    def test_to_webp_resizes_and_renames(self):
        converted = to_webp(_png(4000, 3000), 'promo_image', 'photo.png')
        self.assertIsNotNone(converted)
        self.assertTrue(converted.name.endswith('.webp'))
        img = Image.open(converted)
        self.assertLessEqual(img.width, 1600)
        self.assertLessEqual(img.height, 1200)

    def test_text_limit_uses_field_max(self):
        field = HomePage._meta.get_field('promo_kicker')
        limit = text_limit_for('promo_kicker', field)
        self.assertEqual(limit.max_chars, 80)
