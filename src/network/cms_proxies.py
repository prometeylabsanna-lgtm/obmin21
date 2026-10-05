from src.network.models import City


class BannerCity(City):
    class Meta:
        proxy = True
        verbose_name = 'Банер'
        verbose_name_plural = 'Банер'


class MapCity(City):
    class Meta:
        proxy = True
        verbose_name = 'Знайдіть нас на карті'
        verbose_name_plural = 'Знайдіть нас на карті'


class ContactCity(City):
    class Meta:
        proxy = True
        verbose_name = 'Адреси міст'
        verbose_name_plural = 'Адреси міст'
