from django.db import models
from django.templatetags.static import static

from src.core.colors import COLOR_HELP, hex_color_validator

NAVY = '#052145'

CMP_US_HTML = (
    '<ul>'
    '<li><span>Курс</span><strong>Кращий за банківський</strong></li>'
    '<li><span>Комісія</span><strong>0 ₴ за будь-яку суму</strong></li>'
    '<li><span>Фіксація курсу</span><strong>Онлайн на 30 хвилин</strong></li>'
    '<li><span>Зношені купюри</span><strong>Приймаємо та обмінюємо</strong></li>'
    '<li><span>Криптовалюта</span><strong>USDT, BTC, ETH на готівку</strong></li>'
    '<li><span>Великі суми</span><strong>Індивідуальний курс</strong></li>'
    '</ul>'
)

CMP_THEM_HTML = (
    '<ul>'
    '<li><span>Курс</span><strong>Курс банку з націнкою</strong></li>'
    '<li><span>Комісія</span><strong>Від 1 до 3%</strong></li>'
    '<li><span>Фіксація курсу</span><strong>Лише у відділенні</strong></li>'
    '<li><span>Зношені купюри</span><strong>Часто відмовляють</strong></li>'
    '<li><span>Криптовалюта</span><strong>Недоступно</strong></li>'
    '<li><span>Великі суми</span><strong>Стандартні умови</strong></li>'
    '</ul>'
)


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
        default=(
            'Постійних клієнтів — нам довіряють тисячі людей, які обирають нас '
            'для швидкого та зручного обміну валют і криптоактивів'
        ),
    )
    stat_2_title = models.CharField('Перевага 2 — заголовок', max_length=40, default='20+')
    stat_2_text = models.TextField(
        'Перевага 2 — підзаголовок',
        default=(
            'Відділень в Україні — обмінюйте валюту у зручному для вас відділенні '
            'та отримуйте якісний сервіс'
        ),
    )
    stat_3_title = models.CharField('Перевага 3 — заголовок', max_length=40, default='100%')
    stat_3_text = models.TextField(
        'Перевага 3 — підзаголовок',
        default=(
            'Прозорість обміну — жодних прихованих платежів: ви заздалегідь бачите '
            'актуальний курс та умови операції'
        ),
    )
    stat_4_title = models.CharField('Перевага 4 — заголовок', max_length=40, default='10+')
    stat_4_text = models.TextField(
        'Перевага 4 — підзаголовок',
        default=(
            'Років досвіду — понад 10 років ми працюємо у сфері обміну, забезпечуючи '
            'стабільність, професійність та прозорі умови'
        ),
    )

    why_kicker = models.CharField('Підпис блоку', max_length=80, default='Чому ми')
    why_title = models.CharField(
        'Заголовок',
        max_length=160,
        default='Чому люди обирають обмінювати',
    )
    why_title_accent = models.CharField('Акцент у заголовку', max_length=80, default='в Обмін21')
    why_lead = models.TextField(
        'Підзаголовок',
        default='П’ять причин, через які клієнти повертаються до нас знову і радять друзям',
    )
    why_banner = models.ImageField('Банер блоку', upload_to='advantages/', blank=True)
    color_why_banner = _color('Фон банера')
    why_coins = models.ImageField('Картинка монет', upload_to='advantages/', blank=True)
    why_banner_title = models.CharField(
        'Заголовок на банері',
        max_length=120,
        default='Курс кращий,',
    )
    why_banner_accent = models.CharField(
        'Акцент на банері',
        max_length=80,
        default='ніж у банку',
    )
    why_banner_text = models.TextField(
        'Текст на банері',
        default=(
            'Щодня порівнюємо курси з ринком і тримаємо різницю між купівлею '
            'та продажем мінімальною.'
        ),
    )
    why_1_title = models.CharField('Перевага 1 — заголовок', max_length=120, default='Жодних комісій')
    why_1_text = models.TextField(
        'Перевага 1 — підзаголовок',
        default='Сума в калькуляторі дорівнює сумі, яку ви отримаєте на руки',
    )
    why_2_title = models.CharField(
        'Перевага 2 — заголовок',
        max_length=120,
        default='Фіксація курсу на 30 хвилин',
    )
    why_2_text = models.TextField(
        'Перевага 2 — підзаголовок',
        default='Забронюйте курс онлайн і приходьте без ризику, що він зміниться дорогою',
    )
    why_3_title = models.CharField(
        'Перевага 3 — заголовок',
        max_length=120,
        default='Перевірка кожної купюри',
    )
    why_3_text = models.TextField(
        'Перевага 3 — підзаголовок',
        default='Детектори валют у кожному відділенні: видаємо лише справні банкноти',
    )
    why_4_title = models.CharField(
        'Перевага 4 — заголовок',
        max_length=120,
        default='Конфіденційно і безпечно',
    )
    why_4_text = models.TextField(
        'Перевага 4 — підзаголовок',
        default='Окрема зона для великих сум, дані клієнтів під захистом',
    )
    why_5_title = models.CharField('Перевага 5 — заголовок', max_length=120, default='Поруч з вами')
    why_5_text = models.TextField(
        'Перевага 5 — підзаголовок',
        default='Відділення в 11 містах України з розширеним графіком роботи',
    )

    cmp_kicker = models.CharField('Підпис блоку', max_length=80, default='Порівняння')
    cmp_title = models.CharField('Заголовок', max_length=120, default='Обмін21 чи')
    cmp_title_accent = models.CharField(
        'Акцент у заголовку',
        max_length=80,
        default='звичайний обмінник',
    )
    cmp_us_html = models.TextField('Список «Рекомендуємо»', default=CMP_US_HTML)
    cmp_them_html = models.TextField('Список «Інші обмінники»', default=CMP_THEM_HTML)
    cmp_btn = models.CharField('Кнопка', max_length=80, default='Зафіксувати курс')

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
        return self._file_src('why_banner')

    def why_coins_src(self):
        return self._file_src('why_coins', 'images/coins.png')

    def iter_stats(self):
        rows = []
        for index in range(1, 5):
            title = (getattr(self, f'stat_{index}_title') or '').strip()
            text = (getattr(self, f'stat_{index}_text') or '').strip()
            if title or text:
                rows.append({'title': title, 'text': text})
        return rows

    def iter_why(self):
        rows = []
        for index in range(1, 6):
            title = (getattr(self, f'why_{index}_title') or '').strip()
            text = (getattr(self, f'why_{index}_text') or '').strip()
            if title or text:
                rows.append({'title': title, 'text': text})
        return rows
