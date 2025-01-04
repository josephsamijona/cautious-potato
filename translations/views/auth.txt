from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
import random

from ..forms.auth import (
    UserRegistrationForm, OTPVerificationForm,
    ClientProfileForm, TranslatorProfileForm
)
from ..models import OTPVerification, UserProfile, TranslatorLanguage
from ..services.email import send_otp_email
# views/auth.py (ajouter ces nouvelles vues)

from django.contrib.auth import login, logout
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.template.loader import render_to_string
from ..forms.auth import EmailAuthenticationForm, CustomPasswordResetForm, CustomSetPasswordForm
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404

from ..forms.auth import ClientProfileForm, TranslatorProfileForm
from ..models import TranslatorLanguage

@login_required
def profile_update_view(request):
    """
    View for updating user profile. Handles both client and translator profiles
    with their specific fields.
    """
    user_profile = request.user.profile
    
    # Determine which form to use based on user role
    if user_profile.role == 'CLIENT':
        form_class = ClientProfileForm
    elif user_profile.role == 'TRANSLATOR':
        form_class = TranslatorProfileForm
    else:
        raise Http404("Invalid user role")

    if request.method == 'POST':
        form = form_class(
            request.POST,
            request.FILES,
            instance=user_profile
        )
        
        if form.is_valid():
            profile = form.save(commit=False)
            
            # Handle translator-specific logic
            if user_profile.role == 'TRANSLATOR':
                # Get selected languages
                languages = form.cleaned_data.get('languages', [])
                
                # Update translator languages
                TranslatorLanguage.objects.filter(translator=profile).delete()
                for language in languages:
                    TranslatorLanguage.objects.create(
                        translator=profile,
                        language=language,
                        proficiency='BASIC'  # Default value, can be enhanced to accept proficiency level
                    )
                    
                # Handle bank information
                # If bank information is partially filled, validate required fields
                bank_fields = ['bank_name', 'bank_account_name', 'bank_account_number', 'bank_routing_number']
                has_bank_info = any(form.cleaned_data.get(field) for field in bank_fields)
                
                if has_bank_info:
                    missing_fields = [
                        field for field in bank_fields 
                        if not form.cleaned_data.get(field)
                    ]
                    if missing_fields:
                        form.add_error(
                            None, 
                            f"Please complete all required bank fields: {', '.join(missing_fields)}"
                        )
                        return render(request, 'profile/update.html', {'form': form})
            
            profile.save()
            messages.success(request, 'Profile updated successfully')
            
            # Redirect based on user role
            if profile.role == 'CLIENT':
                return redirect('client_dashboard')
            else:
                return redirect('translator_dashboard')
    else:
        # For translators, pre-populate languages field
        initial_data = {}
        if user_profile.role == 'TRANSLATOR':
            initial_data['languages'] = user_profile.languages.all()
        
        form = form_class(
            instance=user_profile,
            initial=initial_data
        )
    
    context = {
        'form': form,
        'profile_type': user_profile.role.lower()
    }
    
    return render(request, 'profile/update.html', context)

def login_view(request):
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)
        
    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Check if user came from a specific page
            next_page = request.GET.get('next')
            if next_page:
                return redirect(next_page)
                
            return redirect_user_by_role(user)
    else:
        form = EmailAuthenticationForm(request)
    
    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('auth:login')

class CustomPasswordResetView(PasswordResetView):
    template_name = 'auth/password_reset_form.html'
    email_template_name = 'emails/password_reset_email.html'
    success_url = reverse_lazy('auth:password_reset_done')
    form_class = CustomPasswordResetForm
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        user = get_user_model().objects.get(email=email)
        
        # Generate token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build reset URL
        reset_url = self.request.build_absolute_uri(
            reverse('auth:password_reset_confirm', kwargs={
                'uidb64': uid,
                'token': token
            })
        )
        
        # Send email
        context = {
            'user': user,
            'reset_url': reset_url,
            'site_name': 'Translation Platform'
        }
        
        send_mail(
            subject='Password Reset Request',
            message=render_to_string('emails/password_reset_email.txt', context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=render_to_string('emails/password_reset_email.html', context),
        )
        
        messages.success(self.request, 'Password reset email has been sent.')
        return super().form_valid(form)

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'auth/password_reset_confirm.html'
    success_url = reverse_lazy('auth:login')
    form_class = CustomSetPasswordForm
    
    def form_valid(self, form):
        messages.success(self.request, 'Your password has been successfully reset.')
        return super().form_valid(form)

def redirect_user_by_role(user):
    """Helper function to redirect users based on their role"""
    if hasattr(user, 'profile'):
        if user.profile.role == 'CLIENT':
            return redirect('client_dashboard')
        elif user.profile.role == 'TRANSLATOR':
            return redirect('translator_dashboard')
        elif user.profile.role == 'ADMIN':
            return redirect('admin_dashboard')
    return redirect('home')

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Generate OTP
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            # Create OTP verification record
            OTPVerification.objects.create(
                user=user,
                otp=otp,
                expires_at=timezone.now() + timedelta(minutes=15)
            )
            
            # Send OTP email
            try:
                send_otp_email(user.email, otp)
                messages.success(request, 'Registration successful. Please check your email for verification code.')
            except Exception as e:
                messages.error(request, 'Failed to send verification email. Please try again.')
                user.delete()  # Rollback if email fails
                return render(request, 'auth/register.html', {'form': form})
            
            # Store user_id in session for OTP verification
            request.session['registration_user_id'] = user.id
            return redirect('auth:verify_otp')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'auth/register.html', {'form': form})

def verify_otp_view(request):
    user_id = request.session.get('registration_user_id')
    if not user_id:
        messages.error(request, 'Invalid session. Please register again.')
        return redirect('auth:register')
    
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            try:
                verification = OTPVerification.objects.get(
                    user_id=user_id,
                    otp=otp,
                    is_used=False,
                    expires_at__gt=timezone.now()
                )
                
                # Mark OTP as used
                verification.is_used = True
                verification.save()
                
                # Update user profile
                user = verification.user
                user_profile = user.profile
                user_profile.is_email_verified = True
                user_profile.save()
                
                # Login user
                login(request, user)
                
                # Clear session
                del request.session['registration_user_id']
                
                # Redirect based on role
                messages.success(request, 'Email verified successfully. Please complete your profile.')
                if user_profile.role == 'CLIENT':
                    return redirect('auth:client_profile_setup')
                else:
                    return redirect('auth:translator_profile_setup')
                    
            except OTPVerification.DoesNotExist:
                messages.error(request, 'Invalid or expired verification code.')
    else:
        form = OTPVerificationForm()
    
    return render(request, 'auth/verify_otp.html', {'form': form})

def resend_otp_view(request):
    user_id = request.session.get('registration_user_id')
    if not user_id:
        messages.error(request, 'Invalid session. Please register again.')
        return redirect('auth:register')
    
    try:
        user = User.objects.get(id=user_id)
        
        # Generate new OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Create new OTP verification record
        OTPVerification.objects.create(
            user=user,
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # Send new OTP email
        send_otp_email(user.email, otp)
        messages.success(request, 'New verification code sent to your email.')
    except Exception as e:
        messages.error(request, 'Failed to send verification code. Please try again.')
    
    return redirect('auth:verify_otp')

@login_required
def client_profile_setup(request):
    if hasattr(request.user, 'profile') and request.user.profile.role != 'CLIENT':
        messages.error(request, 'Access denied.')
        return redirect('home')
        
    if request.method == 'POST':
        form = ClientProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            profile = form.save()
            messages.success(request, 'Profile completed successfully.')
            return redirect('client_dashboard')
    else:
        form = ClientProfileForm(instance=request.user.profile)
    
    return render(request, 'profile/client.html', {'form': form})

@login_required
def translator_profile_setup(request):
    if hasattr(request.user, 'profile') and request.user.profile.role != 'TRANSLATOR':
        messages.error(request, 'Access denied.')
        return redirect('home')
        
    if request.method == 'POST':
        form = TranslatorProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            profile = form.save()
            
            # Save selected languages
            languages = form.cleaned_data.get('languages', [])
            TranslatorLanguage.objects.filter(translator=profile).delete()
            for language in languages:
                TranslatorLanguage.objects.create(
                    translator=profile,
                    language=language,
                    proficiency='BASIC'  # Default value
                )
                
            messages.success(request, 'Profile completed successfully.')
            return redirect('translator_dashboard')
    else:
        form = TranslatorProfileForm(instance=request.user.profile)
    
    return render(request, 'profile/translator.html', {'form': form})