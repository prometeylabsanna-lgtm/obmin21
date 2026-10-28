"""Сторінка «Що буде сховано» і підтверджене перемикання режиму."""

import json
import re
from dataclasses import dataclass

from django.apps import apps
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from src.core.models import ExchangeModeLog, SiteSettings

ENV_LOCK_NOTICE = 'Режим задано змінною сервера, кнопка тимчасово не діє.'

# Джерело: /Users/olegbonislavskyi/Sites/Obmin21-wt-filter/src/core/exchange_stopwords.py
_FALLBACK_STOP_WORDS = (
    'крипт',
    'krypto',
    'crypto',
    'bitcoin',
    'бітко',
    'битко',
    'ethereum',
    'ефіріум',
    'етериум',
    'usdt',
    'usdc',
    'tether',
    'тезер',
    'стейблко',
    'btc',
    'eth',
    'bnb',
    'sol',
    'trx',
    'ton',
    'біткоїн',
    'swift',
    'переказ',
    'transfer',
    'золот',
    'gold',
    'оптов',
    'зношен',
    'електронн валют',
)
_HIDDEN_LABELS = (
    'content.Service',
    'rates.CurrencyPair',
    'reviews.Review',
    'blog.Post',
    'content.FaqItem',
    'content.AdvantageItem',
    'content.HomeStat',
)
_POST_FIELDS = (
    'title',
    'slug',
    'excerpt',
    'body',
    'faq',
    'seo_title',
    'seo_description',
    'layout',
)
_SETTINGS_SKIP = {
    'id',
    'exchange_only',
    'hidden_page_status',
    'retry_after_seconds',
    'exchange_only_since',
    'rate_hold_minutes',
}
_STRING_FIELDS = {'CharField', 'TextField', 'EmailField', 'URLField', 'SlugField'}
_POST_LINK = re.compile(r'/blog/(?!kategoriya(?:/|$))([0-9A-Za-z_-]+)')


class ExchangeOnlyToggleRejected(Exception):
    pass


@dataclass(frozen=True)
class RecordRow:
    label: str
    admin_url: str = ''


@dataclass(frozen=True)
class RecordGroup:
    title: str
    records: tuple


@dataclass(frozen=True)
class UrlRow:
    label: str
    url: str


@dataclass(frozen=True)
class BlockRow:
    model_title: str
    object_label: str
    field_label: str
    admin_url: str = ''


@dataclass(frozen=True)
class WarningRow:
    place: str
    words: str
    admin_url: str = ''


@dataclass(frozen=True)
class LinkRow:
    source: str
    target: str
    url: str
    admin_url: str = ''


@dataclass(frozen=True)
class HideReport:
    groups: tuple
    urls: tuple
    blocks: tuple
    mode_warnings: tuple
    settings_warnings: tuple
    city_warnings: tuple
    post_warnings: tuple
    links: tuple


def load_stop_words():
    try:
        from src.core.exchange_stopwords import STOP_WORDS, matches_stop_words
    except ImportError:
        return _FALLBACK_STOP_WORDS, _fallback_matches
    return STOP_WORDS, matches_stop_words


def _fallback_matches(*values):
    parts = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parts.append(text.casefold())
    if not parts:
        return False
    blob = '\n'.join(parts)
    return any(word.casefold() in blob for word in _FALLBACK_STOP_WORDS)


def mode_button_label(enabled):
    if enabled:
        return 'Вимкнути режим «Лише обмін валют»'
    return 'Увімкнути режим «Лише обмін валют»'


def confirm_label(enabled):
    if enabled:
        return 'Підтвердити вимкнення'
    return 'Підтвердити увімкнення'


def stored_exchange_only():
    value = SiteSettings.objects.filter(pk=1).values_list(
        'exchange_only', flat=True,
    ).first()
    return bool(value)


def toggle_exchange_only(user):
    from src.core.exchange_mode import is_mode_forced_by_env

    if is_mode_forced_by_env():
        raise ExchangeOnlyToggleRejected(ENV_LOCK_NOTICE)
    row = SiteSettings.objects.filter(pk=1).first()
    if row is None:
        row = SiteSettings(pk=1)
    before = bool(row.exchange_only)
    row.exchange_only = not before
    row.exchange_only_since = timezone.now() if row.exchange_only else None
    row.save()
    log_user = user if getattr(user, 'is_authenticated', False) else None
    ExchangeModeLog.objects.create(
        user=log_user,
        from_value=before,
        to_value=bool(row.exchange_only),
        source=ExchangeModeLog.Source.ADMIN,
    )
    return row


def build_hide_report():
    blocks, mode_warnings = _scan_mode_fields()
    post_warnings, links = _scan_visible_posts()
    return HideReport(
        groups=_hidden_groups(),
        urls=_unavailable_urls(),
        blocks=blocks,
        mode_warnings=mode_warnings,
        settings_warnings=_scan_settings(),
        city_warnings=_scan_cities(),
        post_warnings=post_warnings,
        links=links,
    )


def _hidden_groups():
    groups = []
    for label in _HIDDEN_LABELS:
        model = apps.get_model(label)
        records = tuple(
            RecordRow(_label(obj), _change_url(obj))
            for obj in model.objects.filter(exchange_safe=False).order_by('pk')
        )
        groups.append(RecordGroup(str(model._meta.verbose_name_plural), records))
    return tuple(groups)


def _unavailable_urls():
    rows = []
    post_model = apps.get_model('blog.Post')
    published = post_model.Status.PUBLISHED
    hidden_posts = post_model.objects.filter(
        exchange_safe=False,
        status=published,
    ).exclude(slug='').order_by('pk')
    for post in hidden_posts:
        url = _reverse('blog:post_detail', slug=post.slug)
        if url:
            rows.append(UrlRow(f'Стаття: {_label(post)}', url))
    pair_model = apps.get_model('rates.CurrencyPair')
    hidden_pairs = pair_model.objects.filter(
        exchange_safe=False,
        is_active=True,
    ).exclude(slug='').order_by('pk')
    for pair in hidden_pairs:
        url = _reverse('rates:pair_detail', slug=pair.slug)
        if url:
            rows.append(UrlRow(f'Валютна пара: {_label(pair)}', url))
    category_model = apps.get_model('blog.Category')
    categories = category_model.objects.filter(show_in_filter=True).exclude(slug='')
    for category in categories.order_by('pk'):
        published_posts = post_model.objects.filter(
            category=category,
            status=published,
        )
        if not published_posts.exists():
            continue
        if published_posts.filter(exchange_safe=True).exists():
            continue
        url = _reverse('blog:category', category_slug=category.slug)
        if url:
            rows.append(UrlRow(
                f'Рубрика без видимих статей: {_label(category)}',
                url,
            ))
    return tuple(rows)


def _scan_mode_fields():
    blocks = []
    warnings = []
    for model in apps.get_models():
        opts = model._meta
        if opts.proxy or opts.abstract:
            continue
        fields = [field for field in opts.fields if field.name.endswith('_mode')]
        if not fields:
            continue
        model_title = str(opts.verbose_name_plural)
        for obj in model.objects.all().order_by('pk'):
            label = _label(obj)
            admin_url = _change_url(obj)
            for field in fields:
                value = getattr(obj, field.name)
                field_label = str(field.verbose_name)
                if _is_blank(field, value):
                    blocks.append(BlockRow(
                        model_title, label, field_label, admin_url,
                    ))
                    continue
                words = _matched(_text_for_words(field, value))
                if words:
                    warnings.append(WarningRow(
                        f'{model_title}: {label} — {field_label}',
                        ', '.join(words),
                        admin_url,
                    ))
    blocks.sort(key=lambda row: (row.model_title, row.object_label, row.field_label))
    warnings.sort(key=lambda row: row.place)
    return tuple(blocks), tuple(warnings)


def _scan_settings():
    row = SiteSettings.objects.filter(pk=1).first()
    if row is None:
        return ()
    admin_url = _change_url(row)
    found = []
    for field in row._meta.fields:
        if field.name in _SETTINGS_SKIP or field.name.startswith('color_'):
            continue
        if field.name.endswith('_mode'):
            continue
        if field.get_internal_type() not in _STRING_FIELDS:
            continue
        words = _matched(getattr(row, field.name) or '')
        if words:
            found.append(WarningRow(
                f'Загальні налаштування — {field.verbose_name}',
                ', '.join(words),
                admin_url,
            ))
    found.sort(key=lambda item: item.place)
    return tuple(found)


def _scan_cities():
    city_model = apps.get_model('network.City')
    found = []
    for city in city_model.objects.all().order_by('pk'):
        admin_url = _change_url(city)
        for field in city._meta.fields:
            if field.name.endswith('_mode'):
                continue
            if field.get_internal_type() not in _STRING_FIELDS:
                continue
            words = _matched(getattr(city, field.name) or '')
            if words:
                found.append(WarningRow(
                    f'{city} — {field.verbose_name}',
                    ', '.join(words),
                    admin_url,
                ))
    found.sort(key=lambda item: item.place)
    return tuple(found)


def _scan_visible_posts():
    post_model = apps.get_model('blog.Post')
    visible = post_model.objects.filter(
        exchange_safe=True,
        status=post_model.Status.PUBLISHED,
    ).prefetch_related('related_posts').order_by('pk')
    hidden_by_slug = {
        post.slug: post
        for post in post_model.objects.filter(exchange_safe=False).exclude(slug='')
    }
    warnings = []
    links = []
    for post in visible:
        admin_url = _change_url(post)
        chunks = []
        for name in _POST_FIELDS:
            field = post._meta.get_field(name)
            text = _text_for_words(field, getattr(post, name))
            chunks.append(text)
            words = _matched(text)
            if words:
                warnings.append(WarningRow(
                    f'{_label(post)} — {field.verbose_name}',
                    ', '.join(words),
                    admin_url,
                ))
        seen = set()
        for slug in _POST_LINK.findall('\n'.join(chunks)):
            target = hidden_by_slug.get(slug)
            if target is None or target.pk == post.pk or target.pk in seen:
                continue
            seen.add(target.pk)
            links.append(_link_row(post, target, admin_url))
        for target in post.related_posts.all():
            if target.exchange_safe or target.pk in seen:
                continue
            seen.add(target.pk)
            links.append(_link_row(post, target, admin_url))
    warnings.sort(key=lambda item: item.place)
    links.sort(key=lambda item: (item.source, item.target, item.url))
    return tuple(warnings), tuple(links)


def _link_row(source, target, admin_url):
    url = _reverse('blog:post_detail', slug=target.slug) if target.slug else ''
    return LinkRow(_label(source), _label(target), url, admin_url)


def _matched(value):
    words, matcher = load_stop_words()
    text = (value or '').strip()
    if not text or not matcher(text):
        return ()
    blob = text.casefold()
    return tuple(word for word in words if word.casefold() in blob)


def _text_for_words(field, value):
    kind = field.get_internal_type()
    if kind in {'FileField', 'ImageField'}:
        return ''
    if value is None:
        return ''
    if kind == 'JSONField':
        if value in ({}, []):
            return ''
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _is_blank(field, value):
    kind = field.get_internal_type()
    if kind in {'FileField', 'ImageField'}:
        return not getattr(value, 'name', '')
    if value is None:
        return True
    if kind == 'JSONField':
        return value in ('', {}, [])
    if isinstance(value, str):
        return not value.strip()
    return False


def _label(obj):
    text = str(obj).strip() or f'#{obj.pk}'
    if len(text) > 160:
        return f'{text[:157]}…'
    return text


def _change_url(obj):
    opts = obj._meta
    try:
        return reverse(
            f'admin:{opts.app_label}_{opts.model_name}_change',
            args=[obj.pk],
        )
    except NoReverseMatch:
        return ''


def _reverse(name, **kwargs):
    try:
        return reverse(name, kwargs=kwargs)
    except NoReverseMatch:
        return ''
