from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def send_otp_email(email, otp):
    """
    Send OTP verification email to user
    
    Args:
        email (str): Recipient email address
        otp (str): Generated OTP code
        
    Returns:
        bool: True if email sent successfully, False otherwise
        
    Raises:
        Exception: If email sending fails
    """
    try:
        # Email subject
        subject = "Verify your email address - Translation Platform"

        # Context for email template
        context = {
            'otp': otp,
            'valid_minutes': 15,  # OTP validity in minutes
            'site_name': settings.SITE_NAME,
            'support_email': settings.SUPPORT_EMAIL
        }

        # Render HTML content
        html_content = render_to_string('emails/otp_email.html', context)
        
        # Create plain text version
        text_content = strip_tags(html_content)

        # Create email message
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )

        # Attach HTML content
        msg.attach_alternative(html_content, "text/html")

        # Send email
        msg.send(fail_silently=False)

        # Log success
        logger.info(f"OTP email sent successfully to {email}")
        return True

    except Exception as e:
        # Log error
        logger.error(f"Failed to send OTP email to {email}. Error: {str(e)}")
        raise Exception(f"Failed to send verification email: {str(e)}")

def send_welcome_email(user):
    """
    Send welcome email after successful registration and verification
    
    Args:
        user (User): User object
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        subject = f"Welcome to {settings.SITE_NAME}"
        
        context = {
            'user': user,
            'site_name': settings.SITE_NAME,
            'support_email': settings.SUPPORT_EMAIL,
            'login_url': settings.SITE_URL + '/login'
        }
        
        html_content = render_to_string('emails/welcome_email.html', context)
        text_content = strip_tags(html_content)
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        
        logger.info(f"Welcome email sent successfully to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}. Error: {str(e)}")
        return False