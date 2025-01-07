# tasks.py
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django_apscheduler.models import DjangoJobExecution
from apscheduler.schedulers.background import BackgroundScheduler
from translations.models import TranslationRequest
import logging

logger = logging.getLogger(__name__)

def clean_old_jobs(max_age=7):
    """
    Delete job executions and job records older than `max_age` days.
    """
    try:
        # Delete old job executions
        DjangoJobExecution.objects.delete_old_job_executions(max_age * 86400)  # max_age in days to seconds
        logger.info(f"Cleaned job executions older than {max_age} days")
    except Exception as e:
        logger.error(f"Error cleaning old jobs: {e}")

def check_upcoming_translations():
    """
    Check for upcoming translations and send reminders
    """
    try:
        # Get all active translations
        active_translations = TranslationRequest.objects.filter(
            status__in=['ASSIGNED', 'IN_PROGRESS']
        )

        for translation in active_translations:
            check_and_send_reminders(translation)

    except Exception as e:
        logger.error(f"Error checking upcoming translations: {e}")

def check_and_send_reminders(translation):
    """
    Check if reminders need to be sent for a specific translation
    """
    try:
        now = timezone.now()
        
        if translation.translation_type == 'DOCUMENT':
            days_left = (translation.deadline - now).days
            
            if days_left in [7, 3, 1]:
                send_document_reminder(translation, days_left)
                
        else:  # For live interpretations
            if translation.start_date:
                hours_until_start = (translation.start_date - now).total_seconds() / 3600
                
                if hours_until_start in [24, 3, 1]:
                    send_meeting_reminder(translation, int(hours_until_start))

    except Exception as e:
        logger.error(f"Error checking reminders for translation {translation.id}: {e}")

def send_document_reminder(translation, days_left):
    """
    Send reminder email for document translation
    """
    try:
        subject = f'Reminder: Translation due in {days_left} days'
        template = 'emails/document_reminder.html'
        context = {
            'translation': translation,
            'days_left': days_left,
            'translator_name': translation.translator.get_full_name()
        }
        
        send_mail(
            subject=subject,
            message=_get_email_content(template, context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[translation.translator.email]
        )
        
        logger.info(f"Sent document reminder to translator {translation.translator.id} for translation {translation.id}")

    except Exception as e:
        logger.error(f"Error sending document reminder: {e}")

def send_meeting_reminder(translation, hours_left):
    """
    Send reminder email for live interpretation
    """
    try:
        subject = f'Reminder: Interpretation session in {hours_left} hours'
        template = 'emails/meeting_reminder.html'
        context = {
            'translation': translation,
            'hours_left': hours_left,
            'translator_name': translation.translator.get_full_name()
        }
        
        send_mail(
            subject=subject,
            message=_get_email_content(template, context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[translation.translator.email]
        )
        
        logger.info(f"Sent meeting reminder to translator {translation.translator.id} for translation {translation.id}")

    except Exception as e:
        logger.error(f"Error sending meeting reminder: {e}")

def setup_scheduled_tasks(scheduler):
    """
    Setup all scheduled tasks
    """
    try:
        # Clean old jobs every Monday at 1 AM
        scheduler.add_job(
            clean_old_jobs,
            'cron',
            day_of_week='mon',
            hour=1,
            minute=0,
            id='clean_old_jobs',
            replace_existing=True
        )
        
        # Check for reminders every 15 minutes
        scheduler.add_job(
            check_upcoming_translations,
            'interval',
            minutes=15,
            id='check_reminders',
            replace_existing=True
        )
        
        logger.info("Successfully set up scheduled tasks")
        
    except Exception as e:
        logger.error(f"Error setting up scheduled tasks: {e}")

def _get_email_content(template, context):
    """Helper function to render email content"""
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    
    html_message = render_to_string(template, context)
    return strip_tags(html_message)