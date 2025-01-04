from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django.db.models import Q
from django.utils import timezone

from ..models import TranslationRequest
from ..decorators import translator_required

@login_required
@translator_required
def translator_dashboard(request):
    """
    Dashboard for translators showing active translations, pending offers,
    and recent earnings
    """
    # Get pending translation offers
    pending_translations = TranslationRequest.objects.filter(
        translator=request.user,
        status='ASSIGNED'
    ).order_by('-updated_at')[:5]
    
    # Get active translations
    active_translations = TranslationRequest.objects.filter(
        translator=request.user,
        status='IN_PROGRESS'
    ).order_by('deadline')[:5]
    
    # Get recently completed translations
    completed_translations = TranslationRequest.objects.filter(
        translator=request.user,
        status='COMPLETED'
    ).order_by('-completed_date')[:5]
    
    # Calculate recent earnings (last 30 days)
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    recent_earnings = TranslationRequest.objects.filter(
        translator=request.user,
        status='COMPLETED',
        completed_date__gte=thirty_days_ago
    ).aggregate(Sum('translator_price'))['translator_price__sum'] or 0
    
    context = {
        'pending_translations': pending_translations,
        'active_translations': active_translations,
        'completed_translations': completed_translations,
        'recent_earnings': recent_earnings,
    }
    
    return render(request, 'translator/dashboard.html', context)

@login_required
@translator_required
def translation_list_view(request):
    """
    List all translations assigned to the translator
    """
    translations = TranslationRequest.objects.filter(
        translator=request.user
    ).order_by('-updated_at')
    
    # Filter by status
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
    
    return render(request, 'translator/translation_list.html', context)

@login_required
@translator_required
def translation_detail_view(request, translation_id):
    """
    Detailed view of a specific translation
    """
    translation = get_object_or_404(
        TranslationRequest,
        id=translation_id,
        translator=request.user
    )
    
    context = {
        'translation': translation,
        'can_accept': translation.status == 'ASSIGNED',
        'can_reject': translation.status in ['ASSIGNED', 'IN_PROGRESS'],
        'can_complete': translation.status == 'IN_PROGRESS',
        'can_upload': translation.status == 'IN_PROGRESS'
    }
    
    return render(request, 'translator/translation_detail.html', context)

@login_required
@translator_required
def accept_translation_view(request, translation_id):
    """
    Accept a translation assignment
    """
    translation = get_object_or_404(
        TranslationRequest,
        id=translation_id,
        translator=request.user,
        status='ASSIGNED'
    )
    
    translation.status = 'IN_PROGRESS'
    translation.start_date = timezone.now()
    translation.save()
    
    # Create translation history record
    translation.translationhistory_set.create(
        status='IN_PROGRESS',
        changed_by=request.user,
        notes='Translation accepted by translator'
    )
    
    messages.success(request, 'Translation assignment accepted successfully.')
    return redirect('translator:translation_detail', translation_id=translation.id)

@login_required
@translator_required
def reject_translation_view(request, translation_id):
    """
    Reject a translation assignment
    """
    translation = get_object_or_404(
        TranslationRequest,
        id=translation_id,
        translator=request.user,
        status__in=['ASSIGNED', 'IN_PROGRESS']
    )
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason')
        
        translation.status = 'REJECTED'
        translation.translator = None
        translation.save()
        
        # Create translation history record
        translation.translationhistory_set.create(
            status='REJECTED',
            changed_by=request.user,
            notes=f'Translation rejected by translator. Reason: {rejection_reason}'
        )
        
        messages.success(request, 'Translation assignment rejected successfully.')
        return redirect('translator:translation_list')
        
    return render(request, 'translator/reject_translation.html', {'translation': translation})

@login_required
@translator_required
def complete_translation_view(request, translation_id):
    """
    Mark a translation as completed and upload translated document
    """
    translation = get_object_or_404(
        TranslationRequest,
        id=translation_id,
        translator=request.user,
        status='IN_PROGRESS'
    )
    
    if request.method == 'POST':
        if 'translated_document' in request.FILES:
            translation.translated_document = request.FILES['translated_document']
            translation.status = 'COMPLETED'
            translation.completed_date = timezone.now()
            translation.save()
            
            # Create translation history record
            translation.translationhistory_set.create(
                status='COMPLETED',
                changed_by=request.user,
                notes='Translation completed and document uploaded'
            )
            
            messages.success(request, 'Translation marked as completed successfully.')
            return redirect('translator:translation_detail', translation_id=translation.id)
        else:
            messages.error(request, 'Please upload the translated document.')
            
    return render(request, 'translator/complete_translation.html', {'translation': translation})

@login_required
@translator_required
def payment_history_view(request):
    """
    View translator's payment history
    """
    # Get completed translations with payments
    completed_translations = TranslationRequest.objects.filter(
        translator=request.user,
        status='COMPLETED'
    ).order_by('-completed_date')
    
    # Calculate totals
    total_earnings = completed_translations.aggregate(
        Sum('translator_price')
    )['translator_price__sum'] or 0
    
    # Monthly earnings
    current_month = timezone.now().replace(day=1)
    monthly_earnings = completed_translations.filter(
        completed_date__gte=current_month
    ).aggregate(Sum('translator_price'))['translator_price__sum'] or 0
    
    # Pagination
    paginator = Paginator(completed_translations, 10)
    page = request.GET.get('page')
    payments_page = paginator.get_page(page)
    
    context = {
        'payments': payments_page,
        'total_earnings': total_earnings,
        'monthly_earnings': monthly_earnings
    }
    
    return render(request, 'translator/payment_history.html', context)