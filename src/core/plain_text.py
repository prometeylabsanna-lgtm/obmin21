from html import unescape
import re

from django.utils.html import strip_tags


def plain_text(value: str) -> str:
    return unescape(strip_tags(value or '')).replace('\xa0', ' ').strip()


LEGAL_HEADINGS = (
    'Які cookie застосовуємо',
    'Навіщо вони потрібні',
    'Термін зберігання',
    'Які дані збираємо',
    'Зберігання та передача',
    'Відмова від операції',
    'Заявка та курс',
    'Ваші права',
    'Ідентифікація',
    'Відповідальність',
    'Керування',
    'Предмет',
    'Навіщо',
)


def html_to_plain_legal(value: str) -> str:
    text = str(value or '')
    if re.search(r'<[a-zA-Z][^>]*>', text):
        text = re.sub(r'(?i)</(p|h[1-6]|div|section|li|tr)>', '\n\n', text)
        text = re.sub(r'(?i)<br\s*/?>', '\n', text)
        text = unescape(re.sub(r'<[^>]+>', '', text))
    text = text.replace('\xa0', ' ').replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+\n', '\n', text)
    for heading in LEGAL_HEADINGS:
        text = re.sub(
            rf'(?<!\n)\s+({re.escape(heading)})(?=\s)',
            r'\n\n\1\n\n',
            text,
        )
        text = re.sub(
            rf'({re.escape(heading)})(?=\s+[«"A-ZА-ЯІЇЄҐ])',
            r'\1\n\n',
            text,
        )
    return re.sub(r'\n{3,}', '\n\n', text).strip()
