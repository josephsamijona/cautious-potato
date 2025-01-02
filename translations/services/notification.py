from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags

from .models import Notification

class NotificationService:
    def send_email_notification(self, template, context, recipient, subject):
        """
        Generic email sender that handles both HTML and plain text
        
        Args:
            template (str): Base template name without extension
            context (dict): Context data for template rendering
            recipient (str): Email address of the recipient
            subject (str): Email subject
        """
        # Render HTML version
        html_message = render_to_string(f'emails/{template}.html', context)
        
        # Render text version
        plain_message = render_to_string(f'emails/{template}.txt', context)
        if not plain_message:
            plain_message = strip_tags(html_message)
        
        return send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_message
        )

    def create_notification(self, user, notification_type, title, message, link=None):
        """
        Create in-app notification
        """
        return Notification.objects.create(
            user=user,
            type=notification_type,
            title=title,
            message=message,
            link=link
        )

    def send_quote_processed_notification(self, quote):
        """
        Send notification when a quote is processed
        """
        # Context for email
        context = {
            'client_name': quote.client.get_full_name() or quote.client.email,
            'quote_title': quote.title,
            'quote_price': quote.client_price,
            'quote_link': f'/client/quotes/{quote.id}/',
            'site_name': settings.SITE_NAME
        }
        
        # Send email
        self.send_email_notification(
            template='quote_processed',
            context=context,
            recipient=quote.client.email,
            subject='Your Translation Quote is Ready'
        )
        
        # Create in-app notification
        self.create_notification(
            user=quote.client,
            notification_type='QUOTE',
            title='Quote Processed',
            message=f'Your quote for "{quote.title}" has been processed.',
            link=f'/client/quotes/{quote.id}/'
        )

    def send_translation_assigned_notification(self, translation):
        """
        Send notification when a translator is assigned
        """
        # Context for translator email
        translator_context = {
            'translator_name': translation.translator.get_full_name() or translation.translator.email,
            'translation_title': translation.title,
            'deadline': translation.deadline,
            'translation_link': f'/translator/translations/{translation.id}/',
            'site_name': settings.SITE_NAME
        }
        
        # Send email to translator
        self.send_email_notification(
            template='translation_assigned',
            context=translator_context,
            recipient=translation.translator.email,
            subject='New Translation Assignment'
        )
        
        # Create in-app notification for translator
        self.create_notification(
            user=translation.translator,
            notification_type='PROGRESS',
            title='New Translation Assignment',
            message=f'You have been assigned to translate "{translation.title}".',
            link=f'/translator/translations/{translation.id}/'
        )
        
        # Notify client that translator has been assigned
        client_context = {
            'client_name': translation.client.get_full_name() or translation.client.email,
            'translation_title': translation.title,
            'expected_completion': translation.deadline,
            'translation_link': f'/client/translations/{translation.id}/',
            'site_name': settings.SITE_NAME
        }
        
        self.send_email_notification(
            template='translator_assigned',
            context=client_context,
            recipient=translation.client.email,
            subject='Translator Assigned to Your Project'
        )

    def send_payment_received_notification(self, payment):
        """
        Send notification when payment is received
        """
        translation = payment.translation
        
        # Context for client receipt
        client_context = {
            'client_name': translation.client.get_full_name() or translation.client.email,
            'translation_title': translation.title,
            'amount': payment.amount,
            'transaction_id': payment.stripe_payment_id,
            'date': payment.created_at,
            'translation_link': f'/client/translations/{translation.id}/',
            'site_name': settings.SITE_NAME
        }
        
        # Send receipt to client
        self.send_email_notification(
            template='payment_receipt',
            context=client_context,
            recipient=translation.client.email,
            subject='Payment Confirmation - Translation Service'
        )
        
        # Create in-app notification for client
        self.create_notification(
            user=translation.client,
            notification_type='PAYMENT',
            title='Payment Processed',
            message=f'Your payment for "{translation.title}" has been processed.',
            link=f'/client/translations/{translation.id}/'
        )
        
        # If translator is assigned, notify them about the payment
        if translation.translator:
            self.create_notification(
                user=translation.translator,
                notification_type='PAYMENT',
                title='Project Payment Received',
                message=f'Payment received for project "{translation.title}". You can now start the translation.',
                link=f'/translator/translations/{translation.id}/'
            )

    def send_translation_completed_notification(self, translation):
        """
        Send notification when translation is completed
        """
        # Context for client notification
        client_context = {
            'client_name': translation.client.get_full_name() or translation.client.email,
            'translation_title': translation.title,
            'translator_name': translation.translator.get_full_name(),
            'translation_link': f'/client/translations/{translation.id}/',
            'site_name': settings.SITE_NAME
        }
        
        # Send email to client
        self.send_email_notification(
            template='translation_completed',
            context=client_context,
            recipient=translation.client.email,
            subject='Your Translation is Complete'
        )
        
        # Create in-app notification for client
        self.create_notification(
            user=translation.client,
            notification_type='PROGRESS',
            title='Translation Completed',
            message=f'Your translation "{translation.title}" is now complete.',
            link=f'/client/translations/{translation.id}/'
        )
        
        # Notify admin for review
        admin_users = User.objects.filter(profile__role='ADMIN')
        for admin in admin_users:
            self.create_notification(
                user=admin,
                notification_type='SYSTEM',
                title='Translation Ready for Review',
                message=f'Translation "{translation.title}" has been completed and is ready for review.',
                link=f'/admin/translations/{translation.id}/'
            )