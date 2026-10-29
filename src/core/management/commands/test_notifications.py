from django.core.management.base import BaseCommand

from src.core.notifications.telegram import send_telegram_html


class Command(BaseCommand):
    help = 'Перевірка Telegram-сповіщень для персоналу (без виводу секретів).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--telegram',
            action='store_true',
            help='Перевірити Telegram (за замовчуванням увімкнено)',
        )

    def handle(self, *args, **options):
        # --telegram is optional; Telegram is always the channel under test.
        ok = send_telegram_html(
            '<b>Обмін21</b>\nТестове сповіщення Telegram (test_notifications).',
        )
        if ok:
            self.stdout.write('Telegram: OK')
        else:
            self.stdout.write('Telegram: FAIL (send returned false; check token/chat and logs)')
