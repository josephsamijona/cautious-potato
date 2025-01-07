from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class MeetingReminderService:
    @staticmethod
    def send_meeting_reminder(translation, hours_remaining):
        """Send a reminder for interpretation session based on hours remaining"""
        template_map = {
            24: 'emails/meeting_reminder_24h.html',
            3: 'emails/meeting_reminder_3h.html',
            1: 'emails/meeting_reminder_1h.html'
        }
        
        subject_map = {
            24: 'Reminder: Interpretation Session in 24 Hours',
            3: '3-Hour Alert: Upcoming Interpretation Session',
            1: 'Urgent: Interpretation Session Starting in 1 Hour'
        }
        
        if hours_remaining not in template_map:
            return False
            
        context = {
            'translation': translation,
            'translator_name': translation.translator.get_full_name() or translation.translator.username,
            'hours_remaining': hours_remaining
        }
        
        template_name = template_map[hours_remaining]
        subject = subject_map[hours_remaining]
        
        # Render email content
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[translation.translator.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        return email.send()

    @staticmethod
    def schedule_meeting_reminders(translation):
        """Schedule all reminders for an interpretation session"""
        from django_apscheduler.jobstores import DjangoJobStore
        from apscheduler.schedulers.background import BackgroundScheduler
        
        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")
        
        # Only schedule if start_date is set
        if not translation.start_date:
            return
        
        # Schedule reminders for 24, 3, and 1 hour before session
        for hours in [24, 3, 1]:
            reminder_time = translation.start_date - timedelta(hours=hours)
            
            # Only schedule if reminder time is in the future
            if reminder_time > timezone.now():
                job_id = f'meeting_reminder_{translation.id}_{hours}h'
                
                scheduler.add_job(
                    MeetingReminderService.send_meeting_reminder,
                    trigger='date',
                    run_date=reminder_time,
                    id=job_id,
                    replace_existing=True,
                    args=[translation, hours]
                )

    @staticmethod
    def cancel_reminders(translation):
        """Cancel all scheduled reminders for a session"""
        from apscheduler.schedulers.background import BackgroundScheduler
        
        scheduler = BackgroundScheduler()
        
        # Remove all jobs related to this translation
        for hours in [24, 3, 1]:
            job_id = f'meeting_reminder_{translation.id}_{hours}h'
            try:
                scheduler.remove_job(job_id)
            except:
                pass