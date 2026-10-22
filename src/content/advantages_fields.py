from django.db import models
from django.templatetags.static import static

from src.core.exchange_fields import mode_char, mode_image, mode_text

from src.core.colors import COLOR_HELP, hex_color_validator

NAVY = '#052145'

CMP_US_HTML = (
    '<ul>'
    '<li><span class="k">Курс</span><strong>Кращий за банківський</strong></li>'
    '<li><span class="k">Комісія</span><strong>0 ₴ за будь-яку суму</strong></li>'
    '<li><span class="k">Фіксація курсу</span><strong>Онлайн на 30 хвилин</strong></li>'
    '<li><span class="k">Зношені купюри</span><strong>Приймаємо та обмінюємо</strong></li>'
    '<li><span class="k">Криптовалюта</span><strong>USDT, BTC, ETH на готівку</strong></li>'
    '<li><span class="k">Великі суми</span><strong>Індивідуальний курс</strong></li>'
    '</ul>'
)

CMP_THEM_HTML = (
    '<ul>'
    '<li><span class="k">Курс</span><strong>Курс банку з націнкою</strong></li>'
    '<li><span class="k">Комісія</span><strong>Від 1 до 3%</strong></li>'
    '<li><span class="k">Фіксація курсу</span><strong>Лише у відділенні</strong></li>'
    '<li><span class="k">Зношені купюри</span><strong>Часто відмовляють</strong></li>'
    '<li><span class="k">Криптовалюта</span><strong>Недоступно</strong></li>'
    '<li><span class="k">Великі суми</span><strong>Стандартні умови</strong></li>'
    '</ul>'
)

CMP_US_HTML_MODE = (
    '<ul>'
    '<li><span class="k">Курс</span><strong>Кращий за банківський</strong></li>'
    '<li><span class="k">Комісія</span><strong>0 ₴ за будь-яку суму</strong></li>'
    '<li><span class="k">Фіксація курсу</span><strong>Онлайн на 30 хвилин</strong></li>'
    '<li><span class="k">Купюри</span><strong>Приймаємо та обмінюємо</strong></li>'
    '<li><span class="k">Готівка</span><strong>Долар, євро та фунт</strong></li>'
    '<li><span class="k">Великі суми</span><strong>Індивідуальний курс</strong></li>'
    '</ul>'
)

CMP_THEM_HTML_MODE = (
    '<ul>'
    '<li><span class="k">Курс</span><strong>Курс банку з націнкою</strong></li>'
    '<li><span class="k">Комісія</span><strong>Від 1 до 3%</strong></li>'
    '<li><span class="k">Фіксація курсу</span><strong>Лише у відділенні</strong></li>'
    '<li><span class="k">Купюри</span><strong>Часто відмовляють</strong></li>'
    '<li><span class="k">Готівка</span><strong>Менше валют у касі</strong></li>'
    '<li><span class="k">Великі суми</span><strong>Стандартні умови</strong></li>'
    '</ul>'
)

CMP_MODE_COPY = {
    'cmp_us_html_mode': CMP_US_HTML_MODE,
    'cmp_them_html_mode': CMP_THEM_HTML_MODE,
}

STAT_1_TEXT = (
    'Постійних клієнтів — нам довіряють тисячі людей, які обирають нас '
    'для швидкого та зручного обміну валют і криптоактивів'
)
STAT_1_TEXT_MODE = (
    'Постійних клієнтів — нам довіряють тисячі людей, які обирають нас '
    'для швидкого та зручного обміну готівкової валюти'
)
STAT_2_TEXT = (
    'Відділень в Україні — обмінюйте валюту у зручному для вас відділенні '
    'та отримуйте якісний сервіс'
)
STAT_3_TEXT = (
    'Прозорість обміну — жодних прихованих платежів: ви заздалегідь бачите '
    'актуальний курс та умови операції'
)
STAT_4_TEXT = (
    'Років досвіду — понад 10 років ми працюємо у сфері обміну, забезпечуючи '
    'стабільність, професійність та прозорі умови'
)
STAT_TEXTS = {
    1: STAT_1_TEXT,
    2: STAT_2_TEXT,
    3: STAT_3_TEXT,
    4: STAT_4_TEXT,
}
WHY_COINS_FALLBACK = 'images/coins.png'


def _color(label, default=NAVY):
    return models.CharField(
        label,
        max_length=7,
        default=default,
        validators=[hex_color_validator],
        help_text=COLOR_HELP,
    )


class AdvantagesSectionsMixin(models.Model):
    hero_kicker = models.CharField('Підпис над заголовком', max_length=80, default='Переваги')
    hero_title = models.CharField('Заголовок банера', max_length=120, default='Чому обирають')
    hero_title_accent = models.CharField('Акцент у заголовку', max_length=80, default='Обмін21')
    hero_lead = models.TextField(
        'Підзаголовок банера',
        default=(
            'Вигідний курс без комісій, фіксація онлайн і перевірка кожної купюри. '
            'Ось що цінують наші клієнти.'
        ),
    )
    hero_lead_mode = mode_text('Підзаголовок банера для режиму «Лише обмін»')
    hero_btn_primary = models.CharField(
        'Кнопка 1',
        max_length=80,
        default='Забронювати заявку',
    )
    hero_btn_secondary = models.CharField(
        'Кнопка 2',
        max_length=80,
        default='Усі переваги',
    )
    hero_banner = models.ImageField('Фото банера', upload_to='advantages/', blank=True)
    color_hero_bg = _color('Колір фону банера')
    hero_cards_image = models.ImageField(
        'Картинка карток',
        upload_to='advantages/',
        blank=True,
    )

    stats_kicker = models.CharField('Підпис блоку', max_length=80, default='Цифри')
    stats_title = models.CharField('Заголовок', max_length=120, default='Обмін21')
    stats_title_accent = models.CharField('Акцент у заголовку', max_length=80, default='у цифрах')
    stat_1_title = models.CharField('Перевага 1 — заголовок', max_length=40, default='7K')
    stat_1_text = models.TextField(
        'Перевага 1 — підзаголовок',
        default=STAT_1_TEXT,
    )
    stat_1_text_mode = mode_text(
        'Перевага 1 — підзаголовок для режиму «Лише обмін»',
    )
    stat_2_title = models.CharField('Перевага 2 — заголовок', max_length=40, default='20+')
    stat_2_text = models.TextField(
        'Перевага 2 — підзаголовок',
        default=STAT_2_TEXT,
    )
    stat_2_text_mode = mode_text('Перевага 2 — підзаголовок для режиму «Лише обмін»')
    stat_3_title = models.CharField('Перевага 3 — заголовок', max_length=40, default='100%')
    stat_3_text = models.TextField(
        'Перевага 3 — підзаголовок',
        default=STAT_3_TEXT,
    )
    stat_3_text_mode = mode_text('Перевага 3 — підзаголовок для режиму «Лише обмін»')
    stat_4_title = models.CharField('Перевага 4 — заголовок', max_length=40, default='10+')
    stat_4_text = models.TextField(
        'Перевага 4 — підзаголовок',
        default=STAT_4_TEXT,
    )
    stat_4_text_mode = mode_text('Перевага 4 — підзаголовок для режиму «Лише обмін»')

    why_kicker = models.CharField('Підпис блоку', max_length=80, default='Чому ми')
    why_kicker_mode = mode_char('Підпис блоку для режиму «Лише обмін»', 80)
    why_title = models.CharField(
        'Заголовок',
        max_length=160,
        default='Чому люди обирають обмінювати',
    )
    why_title_mode = mode_char('Заголовок для режиму «Лише обмін»', 160)
    why_title_accent = models.CharField('Акцент у заголовку', max_length=80, default='в Обмін21')
    why_title_accent_mode = mode_char('Акцент у заголовку для режиму «Лише обмін»', 80)
    why_lead = models.TextField(
        'Підзаголовок',
        default='П’ять причин, через які клієнти повертаються до нас знову і радять друзям',
    )
    why_lead_mode = mode_text('Підзаголовок для режиму «Лише обмін»')
    why_banner = models.ImageField('Банер блоку', upload_to='advantages/', blank=True)
    why_banner_mode = mode_image('Банер блоку для режиму «Лише обмін»', 'advantages/')
    color_why_banner = _color('Фон банера')
    why_coins = models.ImageField('Картинка монет', upload_to='advantages/', blank=True)
    why_coins_mode = mode_image(
        'Картинка монет для режиму «Лише обмін»',
        'advantages/',
    )
    why_banner_title = models.CharField(
        'Заголовок на банері',
        max_length=120,
        default='Курс кращий,',
    )
    why_banner_title_mode = mode_char('Заголовок на банері для режиму «Лише обмін»', 120)
    why_banner_accent = models.CharField(
        'Акцент на банері',
        max_length=80,
        default='ніж у банку',
    )
    why_banner_accent_mode = mode_char('Акцент на банері для режиму «Лише обмін»', 80)
    why_banner_text = models.TextField(
        'Текст на банері',
        default=(
            'Щодня порівнюємо курси з ринком і тримаємо різницю між купівлею '
            'та продажем мінімальною.'
        ),
    )
    why_banner_text_mode = mode_text('Текст на банері для режиму «Лише обмін»')
    why_1_title = models.CharField('Перевага 1 — заголовок', max_length=120, default='Жодних комісій')
    why_1_title_mode = mode_char('Перевага 1 — заголовок для режиму «Лише обмін»', 120)
    why_1_text = models.TextField(
        'Перевага 1 — підзаголовок',
        default='Сума в калькуляторі дорівнює сумі, яку ви отримаєте на руки',
    )
    why_1_text_mode = mode_text('Перевага 1 — підзаголовок для режиму «Лише обмін»')
    why_2_title = models.CharField(
        'Перевага 2 — заголовок',
        max_length=120,
        default='Фіксація курсу на 30 хвилин',
    )
    why_2_title_mode = mode_char('Перевага 2 — заголовок для режиму «Лише обмін»', 120)
    why_2_text = models.TextField(
        'Перевага 2 — підзаголовок',
        default='Забронюйте курс онлайн і приходьте без ризику, що він зміниться дорогою',
    )
    why_2_text_mode = mode_text('Перевага 2 — підзаголовок для режиму «Лише обмін»')
    why_3_title = models.CharField(
        'Перевага 3 — заголовок',
        max_length=120,
        default='Перевірка кожної купюри',
    )
    why_3_title_mode = mode_char('Перевага 3 — заголовок для режиму «Лише обмін»', 120)
    why_3_text = models.TextField(
        'Перевага 3 — підзаголовок',
        default='Детектори валют у кожному відділенні: видаємо лише справні банкноти',
    )
    why_3_text_mode = mode_text('Перевага 3 — підзаголовок для режиму «Лише обмін»')
    why_4_title = models.CharField(
        'Перевага 4 — заголовок',
        max_length=120,
        default='Конфіденційно і безпечно',
    )
    why_4_title_mode = mode_char('Перевага 4 — заголовок для режиму «Лише обмін»', 120)
    why_4_text = models.TextField(
        'Перевага 4 — підзаголовок',
        default='Окрема зона для великих сум, дані клієнтів під захистом',
    )
    why_4_text_mode = mode_text('Перевага 4 — підзаголовок для режиму «Лише обмін»')
    why_5_title = models.CharField('Перевага 5 — заголовок', max_length=120, default='Поруч з вами')
    why_5_title_mode = mode_char('Перевага 5 — заголовок для режиму «Лише обмін»', 120)
    why_5_text = models.TextField(
        'Перевага 5 — підзаголовок',
        default='Відділення в 11 містах України з розширеним графіком роботи',
    )
    why_5_text_mode = mode_text('Перевага 5 — підзаголовок для режиму «Лише обмін»')

    cmp_kicker = models.CharField('Підпис блоку', max_length=80, default='Порівняння')
    cmp_kicker_mode = mode_char('Підпис блоку для режиму «Лише обмін»', 80)
    cmp_title = models.CharField('Заголовок', max_length=120, default='Обмін21 чи')
    cmp_title_mode = mode_char('Заголовок для режиму «Лише обмін»', 120)
    cmp_title_accent = models.CharField(
        'Акцент у заголовку',
        max_length=80,
        default='звичайний обмінник',
    )
    cmp_title_accent_mode = mode_char('Акцент у заголовку для режиму «Лише обмін»', 80)
    cmp_us_html = models.TextField('Список «Рекомендуємо»', default=CMP_US_HTML)
    cmp_us_html_mode = mode_text('Список «Рекомендуємо» для режиму «Лише обмін»')
    cmp_them_html = models.TextField('Список «Інші обмінники»', default=CMP_THEM_HTML)
    cmp_them_html_mode = mode_text('Список «Інші обмінники» для режиму «Лише обмін»')
    cmp_btn = models.CharField('Кнопка', max_length=80, default='Зафіксувати курс')
    cmp_btn_mode = mode_char('Кнопка для режиму «Лише обмін»', 80)

    class Meta:
        abstract = True

    def _file_src(self, field_name, fallback=''):
        field = getattr(self, field_name)
        if field:
            try:
                return field.url
            except ValueError:
                pass
        return static(fallback) if fallback else ''

    def hero_banner_src(self):
        return self._file_src('hero_banner')

    def hero_cards_src(self):
        return self._file_src('hero_cards_image')

    def why_banner_src(self):
        from src.core.exchange_mode import exchange_only

        if exchange_only():
            return self._file_src('why_banner_mode')
        return self._file_src('why_banner')

    def why_coins_src(self):
        from src.core.exchange_mode import exchange_only

        if exchange_only():
            return self._file_src('why_coins_mode')
        return self._file_src('why_coins', WHY_COINS_FALLBACK)

    def iter_stats(self):
        from src.core.crypto_visibility import mentions_crypto
        from src.core.exchange_mode import exchange_only

        hide_crypto = exchange_only()
        rows = []
        for index in range(1, 5):
            title = (getattr(self, f'stat_{index}_title') or '').strip()
            text = stat_text_for(self, index).strip()
            if hide_crypto and index == 1 and not text:
                continue
            if hide_crypto and mentions_crypto(f'{title} {text}'):
                continue
            if title or text:
                rows.append({'title': title, 'text': text})
        return rows

    def iter_why(self):
        from src.core.crypto_visibility import mentions_crypto
        from src.core.exchange_mode import exchange_only

        hide_crypto = exchange_only()
        rows = []
        for index in range(1, 6):
            title = advantage_text(self, f'why_{index}_title').strip()
            text = advantage_text(self, f'why_{index}_text').strip()
            if hide_crypto and mentions_crypto(f'{title} {text}'):
                continue
            if title or text:
                rows.append({'title': title, 'text': text})
        return rows


def advantage_default(name):
    from django.db.models.fields import NOT_PROVIDED

    field = AdvantagesSectionsMixin._meta.get_field(name)
    default = field.default
    if default is None or default is NOT_PROVIDED or callable(default):
        return ''
    return str(default)


def advantage_text(page, name):
    from src.core.exchange_fields import resolved_text

    return resolved_text(page, name, advantage_default(name))


def stat_text_for(page, index):
    from src.core.exchange_fields import resolved_text

    return resolved_text(page, f'stat_{index}_text', STAT_TEXTS.get(index, ''))


def cmp_us_html_for(page):
    from src.core.exchange_fields import resolved_text

    return resolved_text(page, 'cmp_us_html', CMP_US_HTML)


def cmp_them_html_for(page):
    from src.core.exchange_fields import resolved_text

    return resolved_text(page, 'cmp_them_html', CMP_THEM_HTML)
