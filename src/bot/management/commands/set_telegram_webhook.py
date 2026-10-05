from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from src.bot.client import telegram_api


class Command(BaseCommand):
    help = 'Реєструє HTTPS webhook Telegram (secret header + дозволені апдейти).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            default='',
            help='Повний URL webhook. За замовчуванням PUBLIC_BASE_URL + /telegram/webhook/',
        )
        parser.add_argument(
            '--drop-pending',
            action='store_true',
            help='Відкинути чергу апдейтів на стороні Telegram',
        )

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError('TELEGRAM_BOT_TOKEN порожній')
        secret = settings.TELEGRAM_WEBHOOK_SECRET
        if not secret:
            raise CommandError('TELEGRAM_WEBHOOK_SECRET порожній')
        url = options['url'] or settings.TELEGRAM_WEBHOOK_URL
        if not url:
            base = settings.PUBLIC_BASE_URL.rstrip('/')
            if not base:
                raise CommandError('Вкажіть --url або PUBLIC_BASE_URL')
            url = f'{base}/telegram/webhook/'
        payload = {
            'url': url,
            'secret_token': secret,
            'allowed_updates': ['message', 'callback_query'],
            'drop_pending_updates': bool(options['drop_pending']),
        }
        data = telegram_api('setWebhook', payload)
        if not data.get('ok'):
            raise CommandError(str(data))
        self.stdout.write(self.style.SUCCESS(f'Webhook: {url}'))
