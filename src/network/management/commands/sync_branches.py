from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from src.network.branch_sync import apply_branch_catalog


class Command(BaseCommand):
    help = (
        'Вирівнює міста й відділення під 18 адрес. '
        'Зайві рядки деактивує, не видаляє. '
        '--dry-run лише друкує план. '
        'Щоб migrate не записав адреси до перегляду, '
        'запустіть його з SYNC_BRANCHES_ON_MIGRATE=0.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показати план і нічого не записувати',
        )

    def handle(self, *args, **options):
        branch = apps.get_model('network', 'Branch')
        if not any(field.name == 'name' for field in branch._meta.fields):
            raise CommandError(
                'Спочатку виконайте migrate: у відділення немає поля назви.',
            )
        report = apply_branch_catalog(apps, dry_run=options['dry_run'])
        if options['dry_run']:
            self.stdout.write('Режим перегляду, базу не змінено.')
        if report.lines:
            for line in report.lines:
                self.stdout.write(line)
        else:
            self.stdout.write('Без змін.')
        self.stdout.write('')
        self.stdout.write('Прогалини:')
        for line in report.gaps:
            self.stdout.write(line)
        if report.city_visibility:
            self.stdout.write(f'Видимість міста: {report.city_visibility}.')
        else:
            self.stdout.write(
                'Поля видимості міста немає — міста без відділень не ховаються.',
            )
        if report.branch_visibility:
            self.stdout.write(
                f'Видимість відділення: {report.branch_visibility}.',
            )
        else:
            self.stdout.write(
                'Поля видимості відділення немає — зайві рядки не приховано.',
            )
