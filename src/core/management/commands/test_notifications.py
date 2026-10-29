from django.core.management.base import BaseCommand

from src.core.notifications.resend import send_staff_email
from src.core.notifications.telegram import send_telegram_html


class Command(BaseCommand):
    help = 'Перевірка Telegram / Resend сповіщень для персоналу (без виводу секретів).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--telegram',
            action='store_true',
            help='Перевірити лише Telegram',
        )
        parser.add_argument(
            '--email',
            action='store_true',
            help='Перевірити лише email (Resend)',
        )
        parser.add_argument(
            '--to',
            dest='to',
            default='',
            help='Override email recipient for this test',
        )

    def handle(self, *args, **options):
        do_telegram = options['telegram']
        do_email = options['email']
        if not do_telegram and not do_email:
            do_telegram = True
            do_email = True

        if do_telegram:
            ok = send_telegram_html(
                '<b>Обмін21</b>\nТестове сповіщення Telegram (test_notifications).',
            )
            if ok:
                self.stdout.write('Telegram: OK')
            else:
                self.stdout.write('Telegram: FAIL (send returned false; check token/chat and logs)')

        if do_email:
            override = None
            raw_to = (options.get('to') or '').strip()
            if raw_to:
                override = [part.strip() for part in raw_to.split(',') if part.strip()]
            ok = send_staff_email(
                'Обмін21: тест сповіщень',
                'Тестове email-сповіщення (test_notifications).',
                to_override=override,
            )
            if ok:
                self.stdout.write('Email: OK')
            else:
                self.stdout.write('Email: FAIL (send returned false; check key/recipients and logs)')
