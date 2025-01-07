# management/commands/run_scheduler.py
from django.core.management.base import BaseCommand
from django.conf import settings
from mvp.scheduler import start_scheduler
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the APScheduler for translation reminders'

    def handle(self, *args, **options):
        self.stdout.write('Starting scheduler...')
        
        try:
            scheduler = start_scheduler()
            
            self.stdout.write(self.style.SUCCESS('Scheduler started successfully'))
            self.stdout.write('Press Ctrl+C to exit')
            
            try:
                # Keep the main thread alive
                scheduler.print_jobs()
                while True:
                    pass
            except KeyboardInterrupt:
                if scheduler.running:
                    scheduler.shutdown()
                    self.stdout.write('Scheduler shut down successfully')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error starting scheduler: {e}'))
            logger.error(f"Scheduler error: {e}", exc_info=True)