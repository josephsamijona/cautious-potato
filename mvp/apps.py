from django.apps import AppConfig
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class MvpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mvp"

    def ready(self):
        """
        Initialize application scheduler and register signal handlers
        """
        # Import here to avoid circular import
        try:
            if hasattr(settings, 'SCHEDULER_AUTOSTART') and settings.SCHEDULER_AUTOSTART:
                from .scheduler import start_scheduler
                scheduler = start_scheduler()
                logger.info("Scheduler started successfully")
                
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            
        # Import signals at startup
        try:
            from . import signals
            logger.info("Signals registered successfully")
        except Exception as e:
            logger.error(f"Failed to register signals: {e}")