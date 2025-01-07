# management/commands/cleanup_jobs.py
from django.core.management.base import BaseCommand
from django.conf import settings
from mvp.tasks import clean_old_jobs
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up old scheduler jobs and their execution records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days of history to keep (default: 7)'
        )

    def handle(self, *args, **options):
        days = options['days']
        
        self.stdout.write(f'Cleaning up jobs older than {days} days...')
        
        try:
            clean_old_jobs(days)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleaned up old jobs')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error cleaning up jobs: {e}')
            )