from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django.db.models import Q

from ..models import TranslationRequest, Language
from ..forms.client import QuoteRequestForm
from ..services.payment import StripePaymentService
from ..decorators import client_required

@login_required
@client_required
def client_dashboard(request):
    """
    Dashboard view for clients showing recent quotes, active translations,
    and important notifications
    """
    # Get recent quotes (last 5)
    recent_quotes = TranslationRequest.objects.filter(
        client=request.user,
        status__in=['QUOTE', 'QUOTED']
    ).order_by('-created_at')[:5]
    
    # Get active translations
    active_translations = TranslationRequest.objects.filter(
        client=request.user,
        status__in=['PAID', 'ASSIGNED', 'IN_PROGRESS']
    ).order_by('-updated_at')[:5]
    
    # Get completed translations (last 5)
    completed_translations = TranslationRequest.objects.filter(
        client=request.user,
        status='COMPLETED'
    ).order_by('-completed_date')[:5]
    
    context = {
        'recent_quotes': recent_quotes,
        'active_translations': active_translations,
        'completed_translations': completed_translations,
    }
    
    return render(request, 'client/dashboard.html', context)

@login_required
@client_required
def create_quote_request(request):
    """
    View for creating a new translation quote request
    """
    if request.method == 'POST':
        form = QuoteRequestForm(request.POST, request.FILES)
        if form.is_valid():
            quote = form.save(commit=False)
            quote.client = request.user
            quote.status = 'QUOTE'
            quote.save()
            
            messages.success(request, 'Quote request submitted successfully. Our team will review it shortly.')
            return redirect('client:quote_list')
    else:
        form = QuoteRequestForm()
    
    return render(request, 'client/create_quote.html', {'form': form})

@login_required
@client_required
def quote_list_view(request):
    """
    View for listing all quotes requested by the client
    """
    quotes = TranslationRequest.objects.filter(
        client=request.user
    ).order_by('-created_at')
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status:
        quotes = quotes.filter(status=status)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        quotes = quotes.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(quotes, 10)  # 10 quotes per page
    page = request.GET.get('page')
    quotes_page = paginator.get_page(page)
    
    context = {
        'quotes': quotes_page,
        'status_choices': TranslationRequest.STATUS_CHOICES,
        'search_query': search_query
    }
    
    return render(request, 'client/quote_list.html', context)

@login_required
@client_required
def translation_list_view(request):
    """
    View for listing all translations (active and completed)
    """
    translations = TranslationRequest.objects.filter(
        client=request.user,
        status__in=['PAID', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED']
    ).order_by('-updated_at')
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status:
        translations = translations.filter(status=status)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        translations = translations.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(translations, 10)
    page = request.GET.get('page')
    translations_page = paginator.get_page(page)
    
    context = {
        'translations': translations_page,
        'status_choices': TranslationRequest.STATUS_CHOICES,
        'search_query': search_query
    }
    
    return render(request, 'client/translation_list.html', context)

@login_required
@client_required
def translation_detail_view(request, translation_id):
    """
    Detailed view of a specific translation
    """
    translation = get_object_or_404(
        TranslationRequest,
        id=translation_id,
        client=request.user
    )
    
    context = {
        'translation': translation,
        'can_pay': translation.status == 'QUOTED',
        'can_download': translation.status == 'COMPLETED' and translation.translated_document
    }
    
    return render(request, 'client/translation_detail.html', context)

@login_required
@client_required
def handle_payment_view(request, translation_id):
    """
    Handle payment for a quoted translation
    """
    translation = get_object_or_404(
        TranslationRequest,
        id=translation_id,
        client=request.user,
        status='QUOTED'
    )
    
    try:
        # Initialize payment service
        payment_service = StripePaymentService()
        
        # Create payment session
        session = payment_service.create_payment_session(
            translation=translation,
            success_url=request.build_absolute_uri(f'/client/translations/{translation.id}/payment-success/'),
            cancel_url=request.build_absolute_uri(f'/client/translations/{translation.id}/')
        )
        
        # Redirect to payment page
        return redirect(session.url)
        
    except Exception as e:
        messages.error(request, 'Payment processing failed. Please try again later.')
        return redirect('client:translation_detail', translation_id=translation.id)