from django.db.utils import OperationalError, ProgrammingError

from src.core.colors import ACCENT_DEFAULT, LEGACY_ACCENTS
from src.core.theme import bump_theme_cache


def is_legacy_accent(value: str) -> bool:
    return (value or '').lower() in LEGACY_ACCENTS


def replace_legacy_accents() -> int:
    from src.content.models import (
        AdvantagesPage,
        BlogPage,
        CitiesPage,
        ContactsPage,
        CookiePage,
        FaqPage,
        HomePage,
        OfferPage,
        PrivacyPage,
        RatesPage,
        ReviewsPage,
        ServicesPage,
    )
    from src.core.models import SiteSettings

    changed = 0
    settings = SiteSettings.load()
    for field in ('header_color_accent', 'footer_color_accent'):
        if is_legacy_accent(getattr(settings, field)):
            setattr(settings, field, ACCENT_DEFAULT)
            changed += 1
    if changed:
        settings.save()

    pages = (
        HomePage,
        RatesPage,
        ContactsPage,
        ServicesPage,
        AdvantagesPage,
        BlogPage,
        ReviewsPage,
        CitiesPage,
        FaqPage,
        PrivacyPage,
        OfferPage,
        CookiePage,
    )
    for model in pages:
        obj = model.load()
        if is_legacy_accent(obj.color_accent):
            obj.color_accent = ACCENT_DEFAULT
            obj.save()
            changed += 1
    if changed:
        bump_theme_cache()
    return changed


def ensure_vercel_accent() -> None:
    try:
        replace_legacy_accents()
    except (OperationalError, ProgrammingError):
        return
