from src.content.home_copy import home_copy_text
from src.content.models import HomePage


class HomeCalcSettings(HomePage):
    class Meta:
        proxy = True
        verbose_name = 'Розрахунок обміну'
        verbose_name_plural = 'Розрахунок обміну'


class HomePromoSettings(HomePage):
    class Meta:
        proxy = True
        verbose_name = 'Вигідний курс'
        verbose_name_plural = 'Вигідний курс'


class HomeWhySettings(HomePage):
    class Meta:
        proxy = True
        verbose_name = 'Чому нас обирають'
        verbose_name_plural = 'Чому нас обирають'


class HomeServicesSettings(HomePage):
    class Meta:
        proxy = True
        verbose_name = 'Наші послуги'
        verbose_name_plural = 'Наші послуги'

    def resolved_services_lead(self):
        return home_copy_text(self, 'services_lead')


class HomeFaqSettings(HomePage):
    class Meta:
        proxy = True
        verbose_name = 'Відповіді на поширені запитання'
        verbose_name_plural = 'Відповіді на поширені запитання'


class HomeReviewsSettings(HomePage):
    class Meta:
        proxy = True
        verbose_name = 'Відгуки на головній'
        verbose_name_plural = 'Відгуки на головній'


class HomeArticlesSettings(HomePage):
    class Meta:
        proxy = True
        verbose_name = 'Корисні статті'
        verbose_name_plural = 'Корисні статті'

    def resolved_articles_lead(self):
        return home_copy_text(self, 'articles_lead')


class HomeSearchSettings(HomePage):
    class Meta:
        proxy = True
        verbose_name = 'Оформлення головної'
        verbose_name_plural = 'Оформлення головної'


class HomeSeoSettings(HomePage):
    class Meta:
        proxy = True
        verbose_name = 'Пошук головної'
        verbose_name_plural = 'Пошук головної'


__all__ = (
    'HomeArticlesSettings',
    'HomeCalcSettings',
    'HomeFaqSettings',
    'HomePromoSettings',
    'HomeReviewsSettings',
    'HomeSearchSettings',
    'HomeSeoSettings',
    'HomeServicesSettings',
    'HomeStat',
    'HomeWhySettings',
)
