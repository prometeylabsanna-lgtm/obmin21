from django.db import models


class HomeSectionCopy(models.Model):
    calc_kicker = models.CharField(
        'Підпис над заголовком',
        max_length=80,
        default='Калькулятор',
    )
    calc_title = models.CharField(
        'Заголовок',
        max_length=120,
        default='Розрахуйте',
    )
    calc_title_accent = models.CharField(
        'Акцент у заголовку',
        max_length=80,
        default='обмін',
    )
    calc_lead = models.CharField(
        'Підзаголовок',
        max_length=240,
        default='Дізнайтесь, скільки ви отримаєте та зафіксуйте курс онлайн',
    )
    calc_give = models.CharField(
        'Підпис «Віддаю»',
        max_length=40,
        default='Віддаю',
    )
    calc_get = models.CharField(
        'Підпис «Отримую»',
        max_length=40,
        default='Отримую',
    )
    calc_rate_hint = models.CharField(
        'Підказка курсу',
        max_length=80,
        default='За поточним курсом',
    )
    calc_button = models.CharField(
        'Текст кнопки',
        max_length=80,
        default='Забронювати заявку',
    )
    calc_lock = models.CharField(
        'Підпис під кнопкою',
        max_length=80,
        default='Курс діє 30 хв',
    )
    calc_amount = models.CharField(
        'Сума за замовчуванням',
        max_length=16,
        default='1000',
    )
    map_kicker = models.CharField(
        'Підпис над заголовком',
        max_length=80,
        default='Відділення',
    )
    map_title = models.CharField(
        'Заголовок',
        max_length=120,
        default='Знайдіть нас',
    )
    map_title_accent = models.CharField(
        'Акцент у заголовку',
        max_length=80,
        default='на карті',
    )
    map_hours_label = models.CharField(
        'Підпис графіка',
        max_length=40,
        default='Графік:',
    )
    map_phone_label = models.CharField(
        'Підпис телефону',
        max_length=40,
        default='Телефон:',
    )
    map_address_label = models.CharField(
        'Підпис адреси',
        max_length=40,
        default='Адреса:',
    )
    map_button = models.CharField(
        'Текст кнопки карти',
        max_length=80,
        default='Відкрити в Google Maps',
    )
    why_kicker = models.CharField(
        'Підпис над заголовком',
        max_length=80,
        default='Переваги',
    )
    why_title = models.CharField(
        'Заголовок',
        max_length=120,
        default='Чому нас',
    )
    why_title_accent = models.CharField(
        'Акцент у заголовку',
        max_length=80,
        default='обирають',
    )
    services_kicker = models.CharField(
        'Підпис над заголовком',
        max_length=80,
        default='Послуги',
    )
    services_title = models.CharField(
        'Заголовок',
        max_length=120,
        default='Наші',
    )
    services_title_accent = models.CharField(
        'Акцент у заголовку',
        max_length=80,
        default='послуги',
    )
    services_lead = models.CharField(
        'Текст під заголовком',
        max_length=400,
        default=(
            'Окрім обміну валют у мережі Обмін21 доступні грошові перекази '
            'по Україні, міжнародні перекази та обмін електронних валют — '
            'умови та підготовка до візиту нижче.'
        ),
    )
    faq_kicker = models.CharField(
        'Підпис над заголовком',
        max_length=80,
        default='Відповіді',
    )
    faq_title = models.CharField(
        'Заголовок',
        max_length=120,
        default='Відповіді на',
    )
    faq_title_accent = models.CharField(
        'Акцент у заголовку',
        max_length=80,
        default='поширені запитання',
    )
    reviews_kicker = models.CharField(
        'Підпис над заголовком',
        max_length=80,
        default='Відгуки',
    )
    reviews_title = models.CharField(
        'Заголовок',
        max_length=120,
        default='Відгуки',
    )
    articles_kicker = models.CharField(
        'Підпис над заголовком',
        max_length=80,
        default='Статті',
    )
    articles_title = models.CharField(
        'Заголовок',
        max_length=120,
        default='Корисні',
    )
    articles_title_accent = models.CharField(
        'Акцент у заголовку',
        max_length=80,
        default='статті',
    )
    articles_lead = models.CharField(
        'Текст під заголовком',
        max_length=400,
        default=(
            'Окрім обміну валют у мережі Обмін21 доступні грошові перекази '
            'по Україні, міжнародні перекази та обмін електронних валют — '
            'умови та підготовка до візиту нижче.'
        ),
    )
    featured_posts = models.ManyToManyField(
        'blog.Post',
        blank=True,
        related_name='home_features',
        verbose_name='Статті на головній',
        help_text='Якщо порожньо — показуємо останні опубліковані.',
    )

    class Meta:
        abstract = True
