# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

def start_scheduler():
    scheduler = BackgroundScheduler(settings.SCHEDULER_CONFIG)
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    if settings.DEBUG:
        # Log scheduler events
        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.DEBUG)
    
    # Add cleanup job
    scheduler.add_job(
        delete_old_job_executions,
        trigger='cron',
        day_of_week='mon', 
        hour=0,
        minute=0,
        id='cleanup_old_jobs',
        replace_existing=True
    )
    
    try:
        logger.info("Starting scheduler...")
        scheduler.start()
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        
    return scheduler

def delete_old_job_executions(max_age=604_800):  # 7 days
    """Delete job execution entries older than `max_age` seconds."""
    try:
        from django_apscheduler.models import DjangoJobExecution
        DjangoJobExecution.objects.delete_old_job_executions(max_age)
        logger.info("Deleted old job executions")
    except Exception as e:
        logger.error(f"Error deleting old job executions: {e}")

def get_scheduler():
    """Get or create the scheduler instance"""
    from django_apscheduler.jobstores import register_job, register_events
    
    scheduler = BackgroundScheduler(settings.SCHEDULER_CONFIG)
    register_events(scheduler)
    register_job(scheduler)
    
    return scheduler

def schedule_translation_reminders(translation):
    """Schedule reminders for a translation based on its type"""
    scheduler = get_scheduler()
    job_prefix = f"translation_{translation.id}"
    
    try:
        # Remove any existing reminders for this translation
        existing_jobs = scheduler.get_jobs()
        for job in existing_jobs:
            if job.id.startswith(job_prefix):
                scheduler.remove_job(job.id)
        
        # Schedule new reminders based on translation type
        if translation.translation_type == 'DOCUMENT':
            for days in [7, 3, 1]:
                reminder_time = translation.deadline - timedelta(days=days)
                if reminder_time > timezone.now():
                    scheduler.add_job(
                        'translation.services.DocumentReminderService.send_document_reminder',
                        'date',
                        run_date=reminder_time,
                        args=[translation.id, days],
                        id=f"{job_prefix}_doc_{days}days",
                        replace_existing=True
                    )
        else:  # Live interpretations
            for hours in [24, 3, 1]:
                reminder_time = translation.start_date - timedelta(hours=hours)
                if reminder_time > timezone.now():
                    scheduler.add_job(
                        'translation.services.MeetingReminderService.send_meeting_reminder',
                        'date',
                        run_date=reminder_time,
                        args=[translation.id, hours],
                        id=f"{job_prefix}_meeting_{hours}hrs",
                        replace_existing=True
                    )
                    
        logger.info(f"Successfully scheduled reminders for translation {translation.id}")
        
    except Exception as e:
        logger.error(f"Error scheduling reminders for translation {translation.id}: {e}")
        raise