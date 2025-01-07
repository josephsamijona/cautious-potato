from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class DocumentReminderService:
    @staticmethod
    def send_document_reminder(translation, days_remaining):
        """Send a reminder for document translation based on days remaining"""
        template_map = {
            7: 'emails/document_reminder_week.html',
            3: 'emails/document_reminder_urgent.html',
            1: 'emails/document_reminder_critical.html'
        }
        
        subject_map = {
            7: 'Weekly Reminder: Translation Due in 7 Days',
            3: 'Urgent Reminder: Translation Due in 3 Days',
            1: 'Critical Reminder: Translation Due Tomorrow'
        }
        
        if days_remaining not in template_map:
            return False
            
        context = {
            'translation': translation,
            'translator_name': translation.translator.get_full_name() or translation.translator.username,
            'days_remaining': days_remaining
        }
        
        template_name = template_map[days_remaining]
        subject = subject_map[days_remaining]
        
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
    def schedule_document_reminders(translation):
        """Schedule all reminders for a document translation"""
        from django_apscheduler.jobstores import DjangoJobStore
        from apscheduler.schedulers.background import BackgroundScheduler
        
        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")
        
        # Schedule reminders for 7, 3, and 1 day before deadline
        for days in [7, 3, 1]:
            reminder_date = translation.deadline - timedelta(days=days)
            
            # Only schedule if reminder date is in the future
            if reminder_date > timezone.now():
                job_id = f'doc_reminder_{translation.id}_{days}days'
                
                scheduler.add_job(
                    DocumentReminderService.send_document_reminder,
                    trigger='date',
                    run_date=reminder_date,
                    id=job_id,
                    replace_existing=True,
                    args=[translation, days]
                )

    @staticmethod
    def cancel_reminders(translation):
        """Cancel all scheduled reminders for a translation"""
        from apscheduler.schedulers.background import BackgroundScheduler
        
        scheduler = BackgroundScheduler()
        
        # Remove all jobs related to this translation
        for days in [7, 3, 1]:
            job_id = f'doc_reminder_{translation.id}_{days}days'
            try:
                scheduler.remove_job(job_id)
            except:
                pass