from django.contrib.auth import get_user_model
from django.conf import settings
from .email_service import EmailService

User = get_user_model()

class AcceptanceNotificationService:
    @staticmethod
    def send_all_notifications(translation):
        """Send notifications to all relevant parties"""
        # Send to admin
        AcceptanceNotificationService._notify_admin(translation)
        
        # Send to translator
        AcceptanceNotificationService._notify_translator(translation)
        
        # Send to client if exists
        if translation.client:
            AcceptanceNotificationService._notify_client(translation)
    
    @staticmethod
    def _notify_admin(translation):
        """Send notification to admin"""
        # Get all admin users
        admin_users = User.objects.filter(is_staff=True)
        
        context = {
            'translation': translation,
            'translator_name': translation.translator.get_full_name() or translation.translator.username,
            'client_name': translation.client.get_full_name() or translation.client.username if translation.client else 'No client'
        }
        
        EmailService.send_html_email(
            subject=f'Translation Request Accepted: {translation.title}',
            template_name='emails/admin_translation_accepted.html',
            context=context,
            recipient_list=[user.email for user in admin_users]
        )
    
    @staticmethod
    def _notify_translator(translation):
        """Send confirmation to translator"""
        context = {
            'translation': translation,
            'translator_name': translation.translator.get_full_name() or translation.translator.username
        }
        
        EmailService.send_html_email(
            subject=f'Translation Assignment Confirmation: {translation.title}',
            template_name='emails/translator_confirmation.html',
            context=context,
            recipient_list=[translation.translator.email]
        )
    
    @staticmethod
    def _notify_client(translation):
        """Send notification to client"""
        context = {
            'translation': translation,
            'client_name': translation.client.get_full_name() or translation.client.username,
            'translator_name': translation.translator.get_full_name() or translation.translator.username
        }
        
        EmailService.send_html_email(
            subject=f'Your Translation Request Has Been Accepted: {translation.title}',
            template_name='emails/client_translation_accepted.html',
            context=context,
            recipient_list=[translation.client.email]
        )