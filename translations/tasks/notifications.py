from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import timedelta

from .models import TranslationRequest, Notification
from .services.reports import generate_admin_report
from .services.email import (
    send_quote_processed_email,
    send_payment_received_email,
    send_deadline_reminder_email
)

@shared_task
def send_quote_notification(quote_id):
    """
    Send notification when admin processes a quote
    """
    try:
        quote = TranslationRequest.objects.get(id=quote_id)
        
        # Create notification
        Notification.objects.create(
            user=quote.client,
            type='QUOTE',
            title='Quote Processed',
            message=f'Your quote request "{quote.title}" has been processed.',
            link=f'/client/quotes/{quote.id}/'
        )
        
        # Send email notification
        send_quote_processed_email(quote)
        
        return f"Quote notification sent successfully for quote {quote_id}"
    except TranslationRequest.DoesNotExist:
        return f"Quote {quote_id} not found"
    except Exception as e:
        return f"Error sending quote notification: {str(e)}"

@shared_task
def send_translation_reminder(translation_id):
    """
    Send reminders for upcoming deadlines
    """
    try:
        translation = TranslationRequest.objects.get(
            id=translation_id,
            status='IN_PROGRESS'
        )
        
        # Calculate time until deadline
        time_remaining = translation.deadline - timezone.now()
        
        # Send different reminder messages based on time remaining
        if time_remaining <= timedelta(days=1):  # 24 hours remaining
            reminder_type = "urgent"
        elif time_remaining <= timedelta(days=3):  # 3 days remaining
            reminder_type = "warning"
        else:
            reminder_type = "normal"
        
        # Create notification for translator
        Notification.objects.create(
            user=translation.translator,
            type='PROGRESS',
            title=f'Deadline Reminder: {translation.title}',
            message=f'Translation deadline is approaching: {translation.deadline}',
            link=f'/translator/translations/{translation.id}/'
        )
        
        # Send email reminder
        send_deadline_reminder_email(translation, reminder_type)
        
        return f"Reminder sent successfully for translation {translation_id}"
    except TranslationRequest.DoesNotExist:
        return f"Translation {translation_id} not found"
    except Exception as e:
        return f"Error sending reminder: {str(e)}"

@shared_task
def update_translation_status(translation_id):
    """
    Automatically update translation status based on various conditions
    """
    try:
        translation = TranslationRequest.objects.get(id=translation_id)
        
        # Check for overdue translations
        if translation.status == 'IN_PROGRESS' and timezone.now() > translation.deadline:
            translation.status = 'OVERDUE'
            translation.save()
            
            # Create notification
            Notification.objects.create(
                user=translation.translator,
                type='PROGRESS',
                title='Translation Overdue',
                message=f'Translation "{translation.title}" is now overdue.',
                link=f'/translator/translations/{translation.id}/'
            )
            
            # Also notify admin
            Notification.objects.create(
                user=User.objects.filter(profile__role='ADMIN').first(),
                type='SYSTEM',
                title='Translation Overdue',
                message=f'Translation {translation.id} is overdue.',
                link=f'/admin/translations/{translation.id}/'
            )
        
        return f"Status updated successfully for translation {translation_id}"
    except TranslationRequest.DoesNotExist:
        return f"Translation {translation_id} not found"
    except Exception as e:
        return f"Error updating status: {str(e)}"

@shared_task
def process_payment_notification(payment_id):
    """
    Process payment notifications and update relevant records
    """
    try:
        translation = TranslationRequest.objects.get(id=payment_id)
        
        # Create notification for client
        Notification.objects.create(
            user=translation.client,
            type='PAYMENT',
            title='Payment Processed',
            message=f'Your payment for "{translation.title}" has been processed.',
            link=f'/client/translations/{translation.id}/'
        )
        
        # Create notification for translator if assigned
        if translation.translator:
            Notification.objects.create(
                user=translation.translator,
                type='PAYMENT',
                title='New Translation Available',
                message=f'A new paid translation "{translation.title}" is available.',
                link=f'/translator/translations/{translation.id}/'
            )
        
        # Send email notifications
        send_payment_received_email(translation)
        
        return f"Payment notification processed successfully for translation {payment_id}"
    except TranslationRequest.DoesNotExist:
        return f"Translation {payment_id} not found"
    except Exception as e:
        return f"Error processing payment notification: {str(e)}"

@shared_task
def generate_periodic_reports():
    """
    Generate periodic reports for administrators
    Runs daily by default
    """
    try:
        # Get all admin users
        admin_users = User.objects.filter(profile__role='ADMIN')
        
        # Generate report data
        report_data = generate_admin_report()
        
        # Create notification for each admin
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                type='SYSTEM',
                title='Daily Platform Report',
                message='Your daily platform report is now available.',
                link='/admin/reports/'
            )
            
            # Send email with report
            context = {
                'admin_name': admin.get_full_name(),
                'report_data': report_data
            }
            
            send_mail(
                subject='Daily Platform Report',
                message=render_to_string('emails/daily_report.txt', context),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
                html_message=render_to_string('emails/daily_report.html', context)
            )
        
        return "Periodic reports generated and sent successfully"
    except Exception as e:
        return f"Error generating periodic reports: {str(e)}"

# Schedule periodic tasks
@shared_task
def schedule_deadline_checks():
    """
    Scheduled task to check for approaching deadlines
    Runs every hour by default
    """
    translations = TranslationRequest.objects.filter(
        status='IN_PROGRESS',
        deadline__gte=timezone.now(),
        deadline__lte=timezone.now() + timedelta(days=3)
    )
    
    for translation in translations:
        send_translation_reminder.delay(translation.id)

@shared_task
def schedule_status_updates():
    """
    Scheduled task to check and update translation statuses
    Runs every hour by default
    """
    translations = TranslationRequest.objects.filter(
        status__in=['IN_PROGRESS', 'ASSIGNED']
    )
    
    for translation in translations:
        update_translation_status.delay(translation.id)