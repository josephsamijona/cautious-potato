from django.core.mail import send_mail
from django.conf import settings

def send_otp_email(email, otp):
    subject = 'Verify your email - Translation Platform'
    message = f'''
    Thank you for registering with our Translation Platform!
    
    Your verification code is: {otp}
    
    This code will expire in 15 minutes.
    
    If you didn't request this code, please ignore this email.
    '''
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )