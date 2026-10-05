from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from src.bot.client import telegram_api


class Command(BaseCommand):
    help = 'Знімає webhook Telegram.'

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError('TELEGRAM_BOT_TOKEN порожній')
        data = telegram_api('deleteWebhook', {'drop_pending_updates': True})
        if not data.get('ok'):
            raise CommandError(str(data))
        self.stdout.write(self.style.SUCCESS('Webhook removed'))
