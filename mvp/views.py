# views.py
# mvp/views.py
from django.http import JsonResponse
import logging
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.views.generic.edit import CreateView
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.views import LogoutView, LoginView
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from .forms import (
    RegistrationForm,
    OTPVerificationForm,
    LoginForm,
    ClientProfileForm,
    TranslatorProfileForm,
    PasswordResetRequestForm,
    PasswordResetForm
)
from .forms import QuoteRequestForm
from translations.models import TranslatorLanguage,Notification
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from translations.models import EmailVerification, UserProfile, PasswordReset, TranslationRequest
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberPrefixWidget
from django_countries.widgets import CountrySelectWidget
from django_countries.fields import CountryField
from .forms import FlexibleLoginForm
from django.db.models import F
from django.views.generic import ListView
import random
import os
import uuid
from datetime import datetime
from django.core.mail import send_mail
from django.conf import settings
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch

logger = logging.getLogger(__name__)

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            otp_code = str(random.randint(100000, 999999))  # Génère un OTP à 6 chiffres
            expiration_time = timezone.now() + timezone.timedelta(minutes=15)
            EmailVerification.objects.create(
                user=user,
                token=otp_code,  # Stocke le OTP à 6 chiffres
                expires_at=expiration_time
            )
            
            # Envoyer l'email avec le code OTP
            send_mail(
                'Your OTP Code',
                f'Your OTP code is {otp_code}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
            
            request.session['user_id'] = user.id
            messages.success(request, 'Registration successful. Please check your email for the OTP code.')
            return redirect('verify_otp')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

def verify_otp_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Session expired. Please register again.')
        return redirect('register')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            try:
                verification = EmailVerification.objects.get(
                    user=user,
                    token=otp_code,
                    is_used=False
                )
                if verification.is_valid():
                    verification.is_used = True
                    verification.save()
                    user.profile.is_email_verified = True
                    user.profile.save()
                    login(request, user)
                    messages.success(request, 'Email verified successfully.')
                    return redirect('profile_setup')
                else:
                    messages.error(request, 'OTP code is invalid or expired.')
            except EmailVerification.DoesNotExist:
                messages.error(request, 'Invalid OTP code.')
    else:
        form = OTPVerificationForm()
    return render(request, 'verify_otp.html', {'form': form})


class CustomLoginView(LoginView):
    form_class = FlexibleLoginForm
    template_name = 'login.html'

    def get_form_kwargs(self):
        """
        Add request to form kwargs to support flexible authentication
        """
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_success_url(self):
        user = self.request.user
        
        # Role-based redirection
        if hasattr(user, 'profile'):
            if user.profile.role == 'ADMIN':
                return reverse_lazy('admin_dashboard')
            elif user.profile.role == 'CLIENT':
                return reverse_lazy('create_quote')
            elif user.profile.role == 'TRANSLATOR':
                return reverse_lazy('create_quote')
        
        return reverse_lazy('dashboard')

    def form_invalid(self, form):
        messages.error(self.request, "Invalid login credentials. Please try again.")
        return super().form_invalid(form)
    


# mvp/views.py
@login_required
def profile_setup_view(request):
    logger.info(f"Profile setup started for user: {request.user.username}")
    
    user = request.user
    profile = user.profile
    
    logger.info(f"User role: {profile.role}")

    if profile.role == 'CLIENT':
        FormClass = ClientProfileForm
        logger.info("Using ClientProfileForm")
    elif profile.role == 'TRANSLATOR':
        FormClass = TranslatorProfileForm
        logger.info("Using TranslatorProfileForm")
    else:
        logger.error(f"Invalid role detected: {profile.role}")
        messages.error(request, 'Invalid user role')
        return redirect('dashboard')

    if request.method == 'POST':
        logger.info("Processing POST request")
        logger.debug(f"POST data: {request.POST}")
        
        form = FormClass(request.POST, instance=profile)
        if form.is_valid():
            logger.info("Form is valid, processing data")
            try:
                profile = form.save(commit=False)
                
                if profile.role == 'TRANSLATOR':
                    logger.info("Processing translator-specific data")
                    languages = form.cleaned_data.get('languages')
                    logger.info(f"Selected languages: {languages}")
                    
                    profile.languages.clear()
                    for language in languages:
                        TranslatorLanguage.objects.create(
                            translator=profile,
                            language=language,
                            proficiency='BASIC'
                        )
                    logger.info("Languages saved successfully")
                
                profile.save()
                logger.info("Profile saved successfully")
                
                messages.success(request, 'Profile setup completed successfully.')
                logger.info(f"Redirecting user {user.username} to dashboard")
                return redirect('dashboard')
                
            except Exception as e:
                logger.error(f"Error saving profile: {str(e)}", exc_info=True)
                messages.error(request, 'An error occurred while saving your profile.')
                
        else:
            logger.warning(f"Form validation failed. Errors: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
    else:
        logger.info("Initializing GET request")
        initial = {}
        if profile.role == 'TRANSLATOR':
            initial['languages'] = profile.languages.all()
            logger.info(f"Initial languages: {initial['languages']}")
        form = FormClass(instance=profile, initial=initial)

    context = {
        'form': form,
        'role': profile.role,
        'is_translator': profile.role == 'TRANSLATOR',
        'show_bank_later': profile.role == 'TRANSLATOR'
    }
    logger.info("Rendering profile setup template")
    return render(request, 'profile_setup.html', context)


# views.py
@login_required
def dashboard_view(request):
    user_profile = request.user.profile
    context = {}

    if user_profile.role == 'CLIENT':
        translation_requests = TranslationRequest.objects.filter(client=request.user)
        context['translation_requests'] = translation_requests
    elif user_profile.role == 'TRANSLATOR':
        missions = TranslationRequest.objects.filter(translator=request.user)
        context['missions'] = missions
    elif user_profile.role == 'ADMIN':
        all_requests = TranslationRequest.objects.all()
        context['all_requests'] = all_requests
    else:
        messages.error(request, 'Invalid user role.')
        return redirect('logout')
    
    return render(request, 'dashboard.html', context)



def password_reset_request_view(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                # Générer un OTP à 6 chiffres
                otp_code = str(random.randint(100000, 999999))
                expiration_time = timezone.now() + timezone.timedelta(minutes=15)
                password_reset = PasswordReset.objects.create(
                    user=user,
                    token=otp_code,  # Utilise le OTP à 6 chiffres
                    expires_at=expiration_time
                )
                
                # Envoyer l'email avec l'OTP
                reset_link = request.build_absolute_uri(
                    reverse('password_reset_confirm') + f"?token={otp_code}"
                )
                send_mail(
                    'Password Reset Request',
                    f'Your OTP for password reset is: {otp_code}\n\nUse this link to reset your password: {reset_link}',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                )
                
                messages.success(request, 'An OTP has been sent to your email. Please check your inbox.')
                return redirect('password_reset_confirm')
            except User.DoesNotExist:
                messages.error(request, 'No user is associated with this email.')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'password_reset_request.html', {'form': form})


# mvp/views.py

def password_reset_confirm_view(request):
    token = request.GET.get('token', None)
    if not token:
        messages.error(request, 'Invalid or missing OTP code.')
        return redirect('password_reset_request')
    
    try:
        password_reset = PasswordReset.objects.get(token=token, is_used=False)
    except PasswordReset.DoesNotExist:
        messages.error(request, 'Invalid or used OTP code.')
        return redirect('password_reset_request')
    
    if not password_reset.is_valid():
        messages.error(request, 'The OTP code has expired.')
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        form = PasswordResetForm(user=password_reset.user, data=request.POST)
        if form.is_valid():
            form.save()
            password_reset.is_used = True
            password_reset.save()
            messages.success(request, 'Your password has been reset successfully.')
            return redirect('login')
    else:
        form = PasswordResetForm(user=password_reset.user)
    
    return render(request, 'password_reset_confirm.html', {'form': form, 'token': token})

class CustomLogoutView(View):
    @method_decorator(csrf_protect)
    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect('login')  # ou remplacez 'login' par votre URL de redirection souhaitée
    
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('login')  # permet aussi le logout via GET pour éviter l'erreur 405
    
    
    
class PasswordResetRequestView(View):
    template_name = 'password_reset_request.html'
    form_class = PasswordResetRequestForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                # Générer OTP de 6 chiffres
                otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                
                # Sauvegarder l'OTP dans la session
                request.session['password_reset_otp'] = otp
                request.session['reset_user_id'] = user.id
                
                # Envoyer l'email avec l'OTP
                send_mail(
                    'Password Reset OTP',
                    f'Your OTP for password reset is: {otp}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, 'OTP has been sent to your email.')
                return redirect('password_reset_verify')
            except User.DoesNotExist:
                messages.error(request, 'No user found with this email address.')
        
        return render(request, self.template_name, {'form': form})

class PasswordResetVerifyView(View):
    template_name = 'password_reset_verify.html'
    form_class = PasswordResetForm

    def get(self, request):
        if 'password_reset_otp' not in request.session:
            messages.error(request, 'Please request OTP first.')
            return redirect('password_reset_request')
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp_code']
            new_password = form.cleaned_data['new_password']
            
            stored_otp = request.session.get('password_reset_otp')
            user_id = request.session.get('reset_user_id')

            if otp == stored_otp and user_id:
                try:
                    user = User.objects.get(id=user_id)
                    user.set_password(new_password)
                    user.save()
                    
                    # Nettoyer la session
                    del request.session['password_reset_otp']
                    del request.session['reset_user_id']
                    
                    messages.success(request, 'Password has been reset successfully.')
                    return redirect('login')
                except User.DoesNotExist:
                    messages.error(request, 'Error resetting password.')
            else:
                messages.error(request, 'Invalid OTP.')
        
        return render(request, self.template_name, {'form': form})




########################################client

def send_quote_confirmation_email(quote_request):
    """
    Send a personalized confirmation email for the quote request
    """
    # Personalization based on translation type
    translation_type_messages = {
        'DOCUMENT': "📄 Document Translation Request",
        'LIVE_ON_SITE': "🌐 On-Site Translation Request",
        'REMOTE_PHONE': "📞 Remote Phone Translation Request",
        'REMOTE_MEETING': "💻 Remote Meeting Translation Request"
    }

    # Custom message
    type_specific_message = translation_type_messages.get(
        quote_request.translation_type, 
        "📝 Translation Request"
    )

    # User's name
    user_name = quote_request.client.get_full_name() or quote_request.client.username

    # Message composition
    message = f"""
╔══════════════════════════════════════════════════
║ Translation Quote Request Confirmation
╠══════════════════════════════════════════════════
║ Hello {user_name}, 
║
║ We are thrilled to work with you! 🌍✨
║
║ {type_specific_message} Received
║ 
║ Quote Details:
║ • Title: {quote_request.title}
║ • Type: {quote_request.get_translation_type_display()}
║ • Languages: {quote_request.source_language.name} → {quote_request.target_language.name}
║
║ Our expert team will review your request shortly. 
║ Thank you for your patience!
║
║ Best regards,
║ DBD I&T Team
╚══════════════════════════════════════════════════
"""

    try:
        send_mail(
            subject=f'Quote Request Received: {quote_request.title}',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[quote_request.client.email],
        )
    except Exception as e:
        # Log email sending error
        print(f"Failed to send confirmation email: {e}")

class CreateClientQuoteRequestView(LoginRequiredMixin, CreateView):
    model = TranslationRequest
    form_class = QuoteRequestForm
    template_name = 'quotes/create_quote.html'
    success_url = reverse_lazy('create_quote')

    def form_valid(self, form):
        try:
            logger.info(f"Processing quote request for user: {self.request.user.email}")
            logger.debug(f"Form data received: {form.cleaned_data}")
            
            form.instance.client = self.request.user
            form.instance.status = 'QUOTE'
            
            # Log all form fields for debugging
            logger.debug("Form field values:")
            for field in form.fields:
                logger.debug(f"{field}: {form.cleaned_data.get(field)}")
            
            # Validate required fields based on translation type
            translation_type = form.cleaned_data.get('translation_type')
            logger.info(f"Translation type selected: {translation_type}")
            
            required_fields = form.get_required_fields()
            logger.debug(f"Required fields for {translation_type}: {required_fields}")
            
            # Check if all required fields are present
            for field in required_fields:
                if not form.cleaned_data.get(field):
                    logger.error(f"Required field '{field}' is missing for translation type {translation_type}")
                    raise ValidationError(f"Field '{field}' is required for {translation_type}")
            
            response = super().form_valid(form)
            logger.info(f"Translation request created successfully with ID: {self.object.id}")
            
            try:
                # Send confirmation email to client
                logger.info(f"Sending confirmation email to client: {self.request.user.email}")
                send_quote_confirmation_email(self.object)
                logger.info("Client confirmation email sent successfully")
            except Exception as e:
                logger.error(f"Failed to send client confirmation email: {str(e)}")
            
            try:
                # Send email notification to admins
                admins = User.objects.filter(profile__role='ADMIN')
                admin_emails = list(admins.values_list('email', flat=True))
                
                if admin_emails:
                    logger.info(f"Sending email notifications to admins: {', '.join(admin_emails)}")
                    send_mail(
                        subject='New Translation Quote Request',
                        message=f'''
                        New translation request received:
                        Title: {form.instance.title}
                        Type: {form.instance.get_translation_type_display()}
                        From: {form.instance.client.email}
                        ''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=admin_emails,
                        fail_silently=False
                    )
                    logger.info("Admin notification emails sent successfully")
                else:
                    logger.warning("No admin emails found for notification")
            
            except Exception as e:
                logger.error(f"Failed to send admin notification emails: {str(e)}")
            
            # Success message for the client
            messages.success(
                self.request,
                'Your quote request has been submitted successfully. We will contact you shortly.'
            )
            logger.info(f"Quote request process completed successfully for user: {self.request.user.email}")
            
            return response
            
        except ValidationError as ve:
            logger.error(f"Validation error: {str(ve)}")
            form.add_error(None, str(ve))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Critical error in form_valid: {str(e)}", exc_info=True)
            logger.error(f"Form data at time of error: {form.cleaned_data}")
            messages.error(
                self.request,
                'An unexpected error occurred. Please try again or contact support.'
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.warning(f"Invalid form submission by user: {self.request.user.email}")
        
        # Log detailed form errors
        logger.error("Form validation failed. Details:")
        for field, errors in form.errors.items():
            logger.error(f"Field '{field}' errors: {errors}")
            
        # Log field values that caused errors
        logger.debug("Current form data:")
        for field in form.fields:
            value = form.data.get(field, 'Not provided')
            logger.debug(f"{field}: {value}")
        
        # Log any non-field errors
        if form.non_field_errors():
            logger.error(f"Non-field errors: {form.non_field_errors()}")
            
        # Add more context to the error message
        error_message = 'Please correct the following errors:\n'
        for field, errors in form.errors.items():
            if field == '__all__':
                error_message += f"• {'; '.join(errors)}\n"
            else:
                field_name = form.fields[field].label or field
                error_message += f"• {field_name}: {'; '.join(errors)}\n"
        
        messages.error(
            self.request,
            error_message
        )
        
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Request a Translation Quote'
        
        # Log the form initialization
        logger.debug(f"Initializing form for user: {self.request.user.email}")
        logger.debug(f"Initial form data: {self.request.GET}")
        
        return context
    
class QuoteListView(ListView):
    model = TranslationRequest
    template_name = 'quotes/quote_list.html'
    context_object_name = 'quotes'

    def get_queryset(self):
        return self.model.objects.filter(client=self.request.user).annotate(
            annotated_translation_type=F('translation_type'),
            annotated_source_language=F('source_language__name'),
            annotated_target_language=F('target_language__name'),
            annotated_client_price=F('client_price'),
            annotated_deadline=F('deadline'),
            annotated_status=F('status')
        )
        
class QuoteDetailView(DetailView):
    model = TranslationRequest
    pk_url_kwarg = 'id'

    def get(self, request, *args, **kwargs):
        quote = self.get_object()
        
        # Créer un dictionnaire avec les données sérialisables
        data = {
            'id': quote.id,
            'quote_type': quote.get_translation_type_display(),
            'title': quote.title,
            'description': quote.description,
            'source_language': quote.source_language.name,
            'target_language': quote.target_language.name,
            'created_at': quote.created_at.strftime('%Y-%m-%d %H:%M'),
            'status': quote.status,
            'client_price': str(quote.client_price) if quote.client_price else None,
            'deadline': quote.deadline.strftime('%Y-%m-%d %H:%M') if quote.deadline else None
        }

        # Ajouter des champs spécifiques selon le type de traduction
        if quote.translation_type == 'DOCUMENT':
            data.update({
                'original_document': quote.original_document.url if quote.original_document else None
            })
        elif quote.translation_type in ['LIVE_ON_SITE', 'REMOTE_PHONE', 'REMOTE_MEETING']:
            data.update({
                'duration_minutes': quote.duration_minutes,
            })
            
            if quote.translation_type == 'LIVE_ON_SITE':
                data['address'] = quote.address
            elif quote.translation_type == 'REMOTE_PHONE':
                data['phone_number'] = quote.phone_number
            elif quote.translation_type == 'REMOTE_MEETING':
                data['meeting_link'] = quote.meeting_link

        return JsonResponse(data)

    def post(self, request, *args, **kwargs):
        quote = self.get_object()
        if 'phone_number' in request.POST:
            quote.phone_number = request.POST['phone_number']
        elif 'meeting_link' in request.POST:
            quote.meeting_link = request.POST['meeting_link']
        quote.save()
        return JsonResponse({'success': True})

    def get_object(self):
        return get_object_or_404(self.model, id=self.kwargs['id'], client=self.request.user)
    #make the payment and invoice later
    
    
def generate_and_send_invoice(request, id):
    quote = get_object_or_404(TranslationRequest, id=id, client=request.user)
    
    # Générer un ID de facture aléatoire
    invoice_id = f'INV-{uuid.uuid4().hex[:8].upper()}'
    
    # Chemin du fichier PDF
    pdf_filename = f'invoice_{invoice_id}.pdf'
    pdf_path = os.path.join(settings.MEDIA_ROOT, 'invoices', pdf_filename)
    
    # Assurer que le répertoire existe
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Informations de l'entreprise
    company_name = 'DBD I&T'
    company_address = '123 Main St, Anytown USA 12345'
    company_phone = '555-1234'
    company_email = 'info@dbdiandt.co'
    company_logo = 'img/logo.png'

    # Informations du client
    client_name = quote.client.get_full_name()
    client_email = quote.client.email

    # Informations de la traduction
    translation_title = quote.title
    translation_type = quote.get_translation_type_display()
    translation_source = quote.source_language.name
    translation_target = quote.target_language.name
    translation_price = quote.client_price

    # Générer le PDF
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elements = []

    # En-tête
    elements.append(Table([[f'Invoice # {invoice_id}', f'Date: {datetime.now().strftime("%Y-%m-%d")}']], 
                         colWidths=[3 * inch, 2 * inch]))
    elements.append(Table([[company_logo, company_name, None], 
                         [company_address, None, None], 
                         [f'Phone: {company_phone}', f'Email: {company_email}', None]], 
                         colWidths=[1.5 * inch, 2.5 * inch, 2 * inch]))
    elements.append(Table([['Bill To:', client_name, client_email]], 
                         colWidths=[1 * inch, 2.5 * inch, 2 * inch]))

    # Détails de la traduction
    data = [['Service', 'Description', 'Amount'], 
            [translation_type, translation_title, f'${translation_price:.2f}']]
    table = Table(data, colWidths=[2 * inch, 3 * inch, 1 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 14),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    elements.append(table)

    # Générer le PDF
    doc.build(elements)

    # Envoyer le PDF par email
    subject = f'Invoice for Translation Service - {translation_title}'
    message = f'Dear {client_name},\n\nPlease find attached the invoice for the translation service you requested.\n\nBest regards,\nMy Translation Agency'
    
    with open(pdf_path, 'rb') as pdf:
        email = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [client_email],
        )
        email.attach(pdf_filename, pdf.read(), 'application/pdf')
        email.send(fail_silently=False)

    # Retourner le PDF pour le téléchargement
    with open(pdf_path, 'rb') as pdf:
        response = HttpResponse(pdf.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        
    # Nettoyer le fichier temporaire
    os.remove(pdf_path)
    
    return response