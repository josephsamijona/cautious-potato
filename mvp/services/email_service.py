from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

class EmailService:
    @staticmethod
    def send_html_email(subject, template_name, context, recipient_list):
        """Base method to send HTML emails"""
        # Render HTML content
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list
        )
        
        # Attach HTML content
        email.attach_alternative(html_content, "text/html")
        return email.send()