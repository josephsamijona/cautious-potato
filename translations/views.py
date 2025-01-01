from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from translations.utils import send_otp_email
from datetime import timedelta
from .models import EmailVerification, OTPVerification, UserProfile
from .forms import (
    UserRegistrationForm, 
    OTPVerificationForm,
    ClientProfileForm,
    TranslatorProfileForm
)
from django.conf import settings
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
import stripe
from .models import TranslationRequest
from .forms import QuoteRequestForm
from .models import NotificationPreference, TranslationRequest
from .forms import ClientProfileUpdateForm, NotificationPreferenceForm

def generate_otp():
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # User won't be able to login until email verification
            user.save()
            
            # Create OTP
            otp = generate_otp()
            expires_at = timezone.now() + timedelta(minutes=15)
            OTPVerification.objects.create(
                user=user,
                otp=otp,
                expires_at=expires_at
            )
            
            # Send email with OTP
            send_otp_email(user.email, otp)
            
            # Store user_id in session for the verification step
            request.session['registration_user_id'] = user.id
            
            messages.success(
                request, 
                'Account created successfully. Please check your email for verification code.'
            )
            return redirect('verify_otp')
        
        messages.error(request, 'Error creating account. Please check the form.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'authentication/register.html', {'form': form})

def verify_otp(request):
    user_id = request.session.get('registration_user_id')
    if not user_id:
        messages.error(request, 'Invalid session. Please register again.')
        return redirect('register')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found. Please register again.')
        return redirect('register')
        
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            verification = OTPVerification.objects.filter(
                user=user,
                otp=otp,
                is_used=False,
                expires_at__gt=timezone.now()
            ).first()
            
            if verification:
                user.is_active = True
                user.save()
                verification.is_used = True
                verification.save()
                
                # Create empty profile
                profile = UserProfile.objects.create(
                    user=user,
                    role=request.session.get('user_role', 'CLIENT')
                )
                
                login(request, user)
                messages.success(request, 'Email verified successfully. Please complete your profile.')
                
                # Redirect based on role
                if profile.role == 'TRANSLATOR':
                    return redirect('translator_profile_setup')
                return redirect('client_profile_setup')
                
            messages.error(request, 'Invalid or expired OTP. Please try again.')
    else:
        form = OTPVerificationForm()
    
    return render(request, 'authentication/verify_otp.html', {'form': form})

@login_required
def client_profile_setup(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        messages.error(request, 'Profile not found.')
        return redirect('home')
        
    if request.method == 'POST':
        form = ClientProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('dashboard')
    else:
        form = ClientProfileForm(instance=profile)
    
    return render(request, 'profiles/client_profile_setup.html', {'form': form})

@login_required
def translator_profile_setup(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        messages.error(request, 'Profile not found.')
        return redirect('home')
        
    if request.method == 'POST':
        form = TranslatorProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('dashboard')
    else:
        form = TranslatorProfileForm(instance=profile)
    
    return render(request, 'profiles/translator_profile_setup.html', {'form': form})


@login_required
def create_quote(request):
    if request.method == 'POST':
        form = QuoteRequestForm(request.POST, request.FILES)
        if form.is_valid():
            quote = form.save(commit=False)
            quote.client = request.user
            quote.status = 'QUOTE'
            quote.save()
            
            messages.success(
                request,
                'Quote request submitted successfully. We will review and get back to you shortly.'
            )
            return redirect('client:quote_list')
    else:
        form = QuoteRequestForm()
    
    return render(request, 'client/create_quote.html', {'form': form})

@login_required
def quote_list(request):
    quotes = TranslationRequest.objects.filter(
        client=request.user,
        status__in=['QUOTE', 'QUOTED']
    ).order_by('-created_at')
    
    paginator = Paginator(quotes, 10)
    page = request.GET.get('page')
    quotes = paginator.get_page(page)
    
    return render(request, 'client/quote_list.html', {'quotes': quotes})

@login_required
def translation_list(request):
    translations = TranslationRequest.objects.filter(
        client=request.user,
        status__in=['PAID', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED']
    ).order_by('-created_at')
    
    # Filtrage
    status = request.GET.get('status')
    if status:
        translations = translations.filter(status=status)
    
    paginator = Paginator(translations, 10)
    page = request.GET.get('page')
    translations = paginator.get_page(page)
    
    return render(request, 'client/translation_list.html', {
        'translations': translations,
    })

@login_required
def quote_detail(request, pk):
    quote = get_object_or_404(
        TranslationRequest,
        pk=pk,
        client=request.user,
        status__in=['QUOTE', 'QUOTED']
    )
    
    # Si la quote a un prix et n'est pas payée, créer session Stripe
    stripe_session = None
    if quote.status == 'QUOTED' and quote.client_price and not quote.is_paid:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': int(quote.client_price * 100),  # Stripe utilise les centimes
                    'product_data': {
                        'name': f'Translation Service: {quote.title}',
                        'description': f'From {quote.source_language} to {quote.target_language}',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri(f'/client/quote/{pk}/payment-success/'),
            cancel_url=request.build_absolute_uri(f'/client/quote/{pk}/'),
        )
        stripe_session = session.id
    
    return render(request, 'client/quote_detail.html', {
        'quote': quote,
        'stripe_session': stripe_session,
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLISHABLE_KEY
    })

@login_required
def payment_success(request, pk):
    quote = get_object_or_404(
        TranslationRequest,
        pk=pk,
        client=request.user
    )
    
    if not quote.is_paid:
        quote.status = 'PAID'
        quote.is_paid = True
        quote.save()
        
        messages.success(
            request,
            'Payment successful! Your translation request has been confirmed.'
        )
    
    return redirect('authentication:translation_list')

@login_required
def translation_detail(request, pk):
    translation = get_object_or_404(
        TranslationRequest,
        pk=pk,
        client=request.user,
        status__in=['PAID', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED']
    )
    
    return render(request, 'client/translation_detail.html', {
        'translation': translation
    })
    
@login_required
def client_profile(request):
    if request.method == 'POST':
        form = ClientProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=request.user.profile,
            user=request.user
        )
        if form.is_valid():
            # Update User model
            user = request.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            
            # Update Profile model
            form.save()
            
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('client_profile')
    else:
        form = ClientProfileUpdateForm(instance=request.user.profile, user=request.user)
    
    return render(request, 'client/profile.html', {'form': form})

@login_required
def notification_settings(request):
    notification_pref, created = NotificationPreference.objects.get_or_create(
        user=request.user
    )
    
    if request.method == 'POST':
        form = NotificationPreferenceForm(request.POST, instance=notification_pref)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification preferences updated successfully!')
            return redirect('notification_settings')
    else:
        form = NotificationPreferenceForm(instance=notification_pref)
    
    return render(request, 'client/notification_settings.html', {'form': form})

@login_required
def notification_list(request):
    # Récupérer les 30 dernières notifications relatives aux traductions
    translations = TranslationRequest.objects.filter(
        client=request.user
    ).order_by('-updated_at')[:30]
    
    notifications = []
    for translation in translations:
        if translation.status == 'QUOTED':
            notifications.append({
                'type': 'quote',
                'message': f'Quote received for "{translation.title}"',
                'date': translation.updated_at,
                'is_read': True,  # Vous pouvez ajouter un modèle de Notification si nécessaire
                'link': f'/client/quote/{translation.id}/'
            })
        elif translation.status == 'IN_PROGRESS':
            notifications.append({
                'type': 'progress',
                'message': f'Translation for "{translation.title}" is in progress',
                'date': translation.updated_at,
                'is_read': True,
                'link': f'/client/translation/{translation.id}/'
            })
        elif translation.status == 'COMPLETED':
            notifications.append({
                'type': 'completed',
                'message': f'Translation for "{translation.title}" is completed',
                'date': translation.updated_at,
                'is_read': True,
                'link': f'/client/translation/{translation.id}/'
            })

    return render(request, 'client/notifications.html', {
        'notifications': sorted(notifications, key=lambda x: x['date'], reverse=True)
    })