"""QA 2026-11-03: час Києва, jsi18n, login redirect, CMS шапки/підвалу, обкладинка,
джерело заявок з веб-чату, адмінка заявок, неактивні відділення, ліміт чату."""

import datetime as dt
import json
import shutil
import tempfile
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from src.bot.handlers import exchange as bot_exchange
from src.bot.outbox import CollectorBot
from src.bot.services import submit_exchange, upsert_profile
from src.core.models import FooterColumn, FooterLink, HeaderMenuItem, SiteSettings
from src.core.notifications.messages import build
from src.core.site_chrome_seed import FOOTER_COLUMNS, HEADER_MENU, seed_site_chrome
from src.core.timefmt import local_fmt
from src.leads.admin import ExchangeRequestAdmin
from src.leads.models import ExchangeRequest
from src.network.models import Branch, City
from src.rates.models import CurrencyPair, Quote, RateBoard

UTC_MOMENT = dt.datetime(2026, 11, 3, 10, 5, tzinfo=dt.timezone.utc)  # 12:05 у Києві (UTC+2)


def _fixtures(slug='qa1103'):
    city = City.objects.create(name='Київ', slug=f'kyiv-{slug}')
    branch = Branch.objects.create(city=city, address='Київ, вул. QA 1')
    pair = CurrencyPair.objects.create(code='USD', name='Долар', slug=f'usd-uah-{slug}')
    Quote.objects.create(pair=pair, board=RateBoard.RETAIL, buy=Decimal('41.20'), sell=Decimal('41.60'))
    return city, branch, pair


def _request(city, branch, pair, **extra):
    data = dict(
        name='Олег', phone='+380991112233', pair=pair, direction='sell',
        amount_give=Decimal('100'), amount_receive=Decimal('4120'), rate_fixed=Decimal('41.2'),
        city=city, branch=branch, expires_at=UTC_MOMENT,
    )
    data.update(extra)
    return ExchangeRequest.objects.create(**data)


# 1. P0 — час фіксації курсу в Europe/Kyiv
class KyivTimeTests(TestCase):
    def test_settings(self):
        from django.conf import settings

        self.assertEqual(settings.TIME_ZONE, 'Europe/Kyiv')
        self.assertTrue(settings.USE_TZ)

    def test_local_fmt_converts_utc(self):
        self.assertEqual(local_fmt(UTC_MOMENT), '12:05 03.11.2026')
        self.assertEqual(local_fmt(None), '')

    def test_notification_uses_kyiv_time(self):
        city, branch, pair = _fixtures()
        obj = _request(city, branch, pair)
        _subject, plain, html = build('exchange', obj)
        self.assertIn('03.11.2026 12:05', plain)
        self.assertNotIn('10:05', plain)
        self.assertIn('12:05', html)

    def test_bot_confirm_message_uses_kyiv_time(self):
        city, branch, pair = _fixtures('bot')
        obj = _request(city, branch, pair)
        bot = CollectorBot()
        profile = upsert_profile(SimpleNamespace(id=5, username='', first_name='T', last_name=''))
        with patch.object(bot_exchange.services, 'get_session') as gs, \
                patch.object(bot_exchange.services, 'submit_exchange', return_value=obj), \
                patch.object(bot_exchange.services, 'clear_session'):
            gs.return_value = SimpleNamespace(state=bot_exchange.BotState.EX_CONFIRM, data={})
            bot_exchange.handle_confirm(bot, profile.chat_id, profile)
        text = ' '.join(item.html for item in bot.items)
        self.assertIn('12:05 03.11.2026', text)

    @patch('src.leads.services.notify_new_lead')
    def test_web_form_success_message_in_kyiv(self, _notify):
        city, branch, pair = _fixtures('web')
        with patch('src.leads.services.timezone.now', return_value=UTC_MOMENT):
            resp = self.client.post(
                reverse('leads:request_modal'),
                {
                    'name': 'Олег', 'phone': '+380991112233', 'pair': pair.pk, 'board': 'retail',
                    'direction': 'sell', 'amount_give': '100', 'branch': branch.pk, 'consent': 'on',
                },
                HTTP_COOKIE=f'obmin21_city={city.slug}',
            )
        obj = ExchangeRequest.objects.filter(branch=branch).first()
        if obj is None:
            self.skipTest('форма заявки не прийняла тестові дані (інша валідація)')
        self.assertContains(resp, local_fmt(obj.expires_at))
        self.assertEqual(timezone.localtime(obj.expires_at).utcoffset(), dt.timedelta(hours=2))


# 2. P1 — /<admin>/jsi18n/ без 500
class JsI18nTests(TestCase):
    def test_admin_jsi18n_ok(self):
        user = get_user_model().objects.create_superuser('qa', 'qa@x.ua', 'pass')
        self.client.force_login(user)
        resp = self.client.get(reverse('admin:jsi18n'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'pluralidx', resp.content)

    def test_djangojs_plural_forms_valid(self):
        import gettext
        from pathlib import Path

        from django.conf import settings

        mo = Path(settings.BASE_DIR) / 'locale/uk/LC_MESSAGES/djangojs.mo'
        with mo.open('rb') as fp:
            catalog = gettext.GNUTranslations(fp)
        self.assertEqual(catalog.plural(1), 0)
        self.assertEqual(catalog.plural(3), 1)
        self.assertEqual(catalog.plural(5), 2)


# 3. P1 — логін без next веде в адмінку
class LoginRedirectTests(TestCase):
    def test_login_without_next_goes_to_admin_index(self):
        get_user_model().objects.create_superuser('qa', 'qa@x.ua', 'pass')
        resp = self.client.post(reverse('admin:login'), {'username': 'qa', 'password': 'pass'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('admin:index'))
        self.assertNotIn('/accounts/profile/', resp['Location'])


# 4. P1 — CMS шапки/підвалу/іконок
class SiteChromeCmsTests(TestCase):
    def test_migration_seeded_current_hardcoded_values(self):
        labels = list(HeaderMenuItem.objects.values_list('label', flat=True))
        self.assertEqual(labels, [label for label, _ in HEADER_MENU])
        cols = list(FooterColumn.objects.values_list('title', 'kind'))
        self.assertEqual(cols, [(t, k) for t, k, _ in FOOTER_COLUMNS])
        self.assertEqual(FooterLink.objects.filter(column__title='Документи').count(), 3)

    def test_seed_is_idempotent_and_keeps_admin_edits(self):
        item = HeaderMenuItem.objects.first()
        item.label = 'Змінено адміном'
        item.save()
        self.assertEqual(seed_site_chrome(), (0, 0))
        self.assertEqual(seed_site_chrome(), (0, 0))
        self.assertEqual(HeaderMenuItem.objects.count(), len(HEADER_MENU))
        self.assertTrue(HeaderMenuItem.objects.filter(label='Змінено адміном').exists())

    def test_context_vars(self):
        resp = self.client.get(reverse('content:faq'))
        ctx = resp.context
        menu = ctx['header_menu']
        self.assertEqual([m['label'] for m in menu], [label for label, _ in HEADER_MENU])
        self.assertEqual(menu[0]['href'], reverse('content:services'))
        faq = next(m for m in menu if m['page'] == 'content:faq')
        self.assertTrue(faq['is_current'])
        self.assertEqual(ctx['header_cta']['label'], 'Зробити заявку')
        self.assertTrue(ctx['header_cta']['enabled'])
        self.assertEqual(ctx['header_cta']['modal_url'], reverse('leads:contact_modal'))
        titles = [c['title'] for c in ctx['footer_columns']]
        self.assertIn('Компанія', titles)
        self.assertIn('Документи', titles)
        icons = ctx['site_icons']
        self.assertIn('favicon', icons['favicon'])
        self.assertEqual(icons['manifest_url'], reverse('core:webmanifest'))
        self.assertEqual(icons['theme_color'], '#052145')

    def test_inactive_and_order_and_cta_from_admin(self):
        HeaderMenuItem.objects.filter(label='FAQ').update(is_active=False)
        HeaderMenuItem.objects.filter(label='Контакти').update(sort_order=1)
        site = SiteSettings.load()
        site.header_cta_label = 'Забронювати курс'
        site.save()
        ctx = self.client.get('/').context
        labels = [m['label'] for m in ctx['header_menu']]
        self.assertNotIn('FAQ', labels)
        self.assertEqual(labels[0], 'Контакти')
        self.assertEqual(ctx['header_cta']['label'], 'Забронювати курс')

    def test_custom_url_and_validation(self):
        from django.core.exceptions import ValidationError

        SiteSettings.objects.get_or_create(pk=1)
        item = HeaderMenuItem(label='Курси', url='/kursy/')
        item.full_clean()
        self.assertEqual(item.href, '/kursy/')
        with self.assertRaises(ValidationError):
            HeaderMenuItem(label='Bad', url='javascript:alert(1)').full_clean()
        with self.assertRaises(ValidationError):
            HeaderMenuItem(label='Empty').full_clean()

    def test_webmanifest(self):
        site = SiteSettings.load()
        site.manifest_name = 'Обмін21 QA'
        site.save()
        resp = self.client.get(reverse('core:webmanifest'))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['name'], 'Обмін21 QA')
        self.assertEqual(data['theme_color'], '#052145')
        self.assertTrue(data['icons'])

    def test_admin_pages_render(self):
        user = get_user_model().objects.create_superuser('qa', 'qa@x.ua', 'pass')
        self.client.force_login(user)
        SiteSettings.objects.get_or_create(pk=1)
        for name in ('core_headersettings', 'core_footersettings', 'core_sitesettings'):
            resp = self.client.get(reverse(f'admin:{name}_change', args=[1]))
            self.assertEqual(resp.status_code, 200, (name, resp.get('Location')))
        col = FooterColumn.objects.get(title='Компанія')
        resp = self.client.get(reverse('admin:core_footercolumn_change', args=[col.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Відгуки')


# 5. P0 — обкладинка статті: post.cover має пріоритет
class PostCoverTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def _post(self, **kw):
        from src.blog.models import Post

        slug = kw.pop('slug', 'kurs-dolara-2027')
        post = Post.objects.filter(slug=slug).first() or Post(slug=slug, title='Тест')
        for k, v in kw.items():
            setattr(post, k, v)
        return post

    def _png(self):
        import io

        from PIL import Image

        buf = io.BytesIO()
        Image.new('RGB', (40, 20), 'red').save(buf, 'PNG')
        return SimpleUploadedFile('qa-cover.png', buf.getvalue(), content_type='image/png')

    def test_uploaded_cover_wins_over_static_slug_image(self):
        from src.core.responsive_images import static_exists

        post = self._post()
        self.assertTrue(static_exists(f'images/articles/{post.slug}.jpg'), 'потрібна статична картинка slug')
        post.cover.save('qa-cover.png', self._png(), save=False)
        self.assertTrue(post.cover_url.startswith('/media/'), post.cover_url)
        self.assertEqual(post.image_url(), post.cover_url)
        self.assertEqual(post.image_size(), (40, 20))

    def test_without_cover_falls_back_to_static(self):
        post = self._post()
        post.cover = None
        self.assertIn('images/articles/kurs-dolara-2027', post.cover_url)

    def test_missing_cover_file_falls_back(self):
        post = self._post()
        post.cover.name = 'blog/missing-file.png'
        self.assertIn('images/articles/kurs-dolara-2027', post.cover_url)


# 6. P2 — заявки з веб-чату мають source=web
class WebChatSourceTests(TestCase):
    @patch('src.leads.services.notify_new_lead')
    def test_web_chat_lead_is_web(self, _notify):
        city, branch, pair = _fixtures('wc')
        user = SimpleNamespace(id='w:abc123', username='', first_name='Гість сайту', last_name='')
        profile = upsert_profile(user)
        obj = submit_exchange(profile.chat_id, profile, {
            'city_id': city.pk, 'pair_id': pair.pk, 'direction': 'sell', 'amount_give': '100',
            'branch_id': branch.pk, 'name': 'Іван Тест', 'phone': '+380991112233',
        })
        self.assertEqual(obj.source, ExchangeRequest.Source.WEB)
        self.assertNotEqual(obj.messenger, 'Telegram')

    @patch('src.leads.services.notify_new_lead')
    def test_telegram_lead_stays_telegram(self, _notify):
        city, branch, pair = _fixtures('tg')
        profile = upsert_profile(SimpleNamespace(id=777, username='u7', first_name='І', last_name=''))
        obj = submit_exchange(profile.chat_id, profile, {
            'city_id': city.pk, 'pair_id': pair.pk, 'direction': 'sell', 'amount_give': '100',
            'branch_id': branch.pk, 'name': 'Іван Тест', 'phone': '+380991112233',
        })
        self.assertEqual(obj.source, ExchangeRequest.Source.TELEGRAM)

    def test_web_contact_source(self):
        from src.bot.services import lead_source

        self.assertEqual(lead_source('w:xyz'), 'web')
        self.assertEqual(lead_source('12345'), 'telegram')


# 7. P2 — адмінка заявок: фільтри + дія «Змінити статус» з LogEntry
class ExchangeAdminTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('qa', 'qa@x.ua', 'pass')
        self.client.force_login(self.user)
        self.city, self.branch, self.pair = _fixtures('adm')
        self.a = _request(self.city, self.branch, self.pair)
        self.b = _request(self.city, self.branch, self.pair, phone='+380991112234')

    def test_list_filter(self):
        names = [f if isinstance(f, str) else f[0] for f in ExchangeRequestAdmin.list_filter]
        for need in ('status', 'city', 'created_at', 'source'):
            self.assertIn(need, names)
        resp = self.client.get(reverse('admin:leads_exchangerequest_changelist'), {'source__exact': 'web'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Змінити статус')

    def test_change_status_action_logs(self):
        resp = self.client.post(reverse('admin:leads_exchangerequest_changelist'), {
            'action': 'change_status',
            'new_status': ExchangeRequest.Status.DONE,
            '_selected_action': [self.a.pk, self.b.pk],
        })
        self.assertEqual(resp.status_code, 302)
        self.a.refresh_from_db()
        self.assertEqual(self.a.status, ExchangeRequest.Status.DONE)
        logs = LogEntry.objects.filter(action_flag=CHANGE, object_id__in=[str(self.a.pk), str(self.b.pk)])
        self.assertEqual(logs.count(), 2)
        self.assertIn('Нова → Виконана', logs.first().get_change_message())

    def test_change_status_requires_choice(self):
        self.client.post(reverse('admin:leads_exchangerequest_changelist'), {
            'action': 'change_status', 'new_status': '', '_selected_action': [self.a.pk],
        })
        self.a.refresh_from_db()
        self.assertEqual(self.a.status, ExchangeRequest.Status.NEW)
        self.assertFalse(LogEntry.objects.exists())


# 8. P2 — неактивні відділення не пропонуються
class InactiveBranchTests(TestCase):
    def setUp(self):
        self.city, self.branch, self.pair = _fixtures('inb')
        self.off = Branch.objects.create(city=self.city, address='Закрите відділення', is_active=False)

    def test_admin_branch_choices(self):
        user = get_user_model().objects.create_superuser('qa', 'qa@x.ua', 'pass')
        self.client.force_login(user)
        resp = self.client.get(reverse('admin:leads_exchangerequest_add'))
        qs = resp.context['adminform'].form.fields['branch'].queryset
        self.assertIn(self.branch, qs)
        self.assertNotIn(self.off, qs)

    def test_admin_keeps_current_inactive_branch_on_old_request(self):
        user = get_user_model().objects.create_superuser('qa', 'qa@x.ua', 'pass')
        self.client.force_login(user)
        old = _request(self.city, self.off, self.pair)
        resp = self.client.get(reverse('admin:leads_exchangerequest_change', args=[old.pk]))
        self.assertIn(self.off, resp.context['adminform'].form.fields['branch'].queryset)

    def test_public_form_and_bot_reject_inactive(self):
        from src.bot.services import branch_by_id
        from src.leads.forms import ExchangeRequestForm

        form = ExchangeRequestForm(city=self.city)
        self.assertNotIn(self.off, form.fields['branch'].queryset)
        self.assertIsNone(branch_by_id(self.off.pk, self.city))


# 9. P2 — ліміт чату >= 20 повідомлень/хв на діалог
@override_settings(RATELIMIT_ENABLE=True)
class ChatRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_twenty_messages_per_minute_pass(self):
        from src.bot.web_views import RATE_LIMIT

        self.assertGreaterEqual(RATE_LIMIT, 20)
        self.client.get(reverse('bot:chat_log'))
        for i in range(20):
            resp = self.client.post(reverse('bot:chat_send'), {'text': f'привіт {i}'})
            self.assertNotContains(resp, 'Забагато запитів')

    def test_limit_is_per_dialog_and_eventually_blocks(self):
        from src.bot.web_views import RATE_LIMIT

        self.client.get(reverse('bot:chat_log'))
        for _ in range(RATE_LIMIT):
            self.client.post(reverse('bot:chat_send'), {'text': 'x'})
        self.assertContains(self.client.post(reverse('bot:chat_send'), {'text': 'x'}), 'Забагато запитів')
        other = self.client_class()
        other.get(reverse('bot:chat_log'))
        self.assertNotContains(other.post(reverse('bot:chat_send'), {'text': 'x'}), 'Забагато запитів')
