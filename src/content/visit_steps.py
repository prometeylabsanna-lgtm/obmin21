from django.db import models

STEP_DEFAULTS = {
    'title': 'Три кроки до',
    'title_accent': 'обміну',
    'step_1_title': 'Оберіть послугу',
    'step_1_text': 'Розрахуйте суму в калькуляторі або зателефонуйте консультанту.',
    'step_2_title': 'Зафіксуйте курс',
    'step_2_text': 'Забронюйте заявку онлайн — курс діє',
    'step_3_title': 'Прийдіть у відділення',
    'step_3_text': (
        'Отримайте гроші у зручному відділенні з паспортом або ID-карткою.'
    ),
}

HOME_FALLBACK = {
    'why_empty_number': '7K',
    'why_empty_label': 'Постійних клієнтів',
    'why_empty_text': (
        'нам довіряють тисячі людей, які обирають нас '
        'для швидкого та зручного обміну валют'
    ),
}


class VisitSteps(models.Model):
    title = models.CharField('Заголовок', max_length=80, default=STEP_DEFAULTS['title'])
    title_accent = models.CharField(
        'Акцент у заголовку',
        max_length=80,
        default=STEP_DEFAULTS['title_accent'],
    )
    step_1_title = models.CharField(
        'Крок 1 — назва',
        max_length=80,
        default=STEP_DEFAULTS['step_1_title'],
    )
    step_1_text = models.CharField(
        'Крок 1 — текст',
        max_length=240,
        default=STEP_DEFAULTS['step_1_text'],
    )
    step_2_title = models.CharField(
        'Крок 2 — назва',
        max_length=80,
        default=STEP_DEFAULTS['step_2_title'],
    )
    step_2_text = models.CharField(
        'Крок 2 — текст',
        max_length=240,
        default=STEP_DEFAULTS['step_2_text'],
        help_text=(
            'Без числа хвилин. Його підставляє поле '
            '«Хвилин фіксації курсу» із загальних налаштувань.'
        ),
    )
    step_3_title = models.CharField(
        'Крок 3 — назва',
        max_length=80,
        default=STEP_DEFAULTS['step_3_title'],
    )
    step_3_text = models.CharField(
        'Крок 3 — текст',
        max_length=240,
        default=STEP_DEFAULTS['step_3_text'],
    )

    class Meta:
        verbose_name = 'Три кроки'
        verbose_name_plural = 'Три кроки'

    def __str__(self):
        return 'Три кроки'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return None

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


def minutes_phrase(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 0
    if number < 0:
        number = 0
    mod100 = number % 100
    mod10 = number % 10
    if 11 <= mod100 <= 14:
        word = 'хвилин'
    elif mod10 == 1:
        word = 'хвилина'
    elif 2 <= mod10 <= 4:
        word = 'хвилини'
    else:
        word = 'хвилин'
    return f'{number} {word}'


def _fill_blank(row, defaults):
    updates = []
    for name, value in defaults.items():
        if not str(getattr(row, name) or '').strip():
            setattr(row, name, value)
            updates.append(name)
    if updates:
        row.save(update_fields=updates)


def fill_visit_steps(apps, schema_editor):
    Model = apps.get_model('content', 'VisitSteps')
    row, _ = Model.objects.get_or_create(pk=1)
    _fill_blank(row, STEP_DEFAULTS)


def fill_home_fallback(apps, schema_editor):
    Home = apps.get_model('content', 'HomePage')
    row = Home.objects.filter(pk=1).first()
    if row is None:
        return
    _fill_blank(row, HOME_FALLBACK)
