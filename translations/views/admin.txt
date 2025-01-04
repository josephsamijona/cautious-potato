from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.http import HttpResponse
import csv
from datetime import timedelta

from ..models import User, UserProfile, TranslationRequest, TranslatorLanguage
from ..decorators import admin_required
from ..forms.admin import QuoteProcessForm, TranslatorAssignmentForm
from ..services.email import send_quote_processed_email, send_translator_assignment_email

@login_required
@admin_required
def admin_dashboard(request):
    """
    Admin dashboard showing platform overview
    """
    # Count statistics
    total_users = UserProfile.objects.count()
    total_clients = UserProfile.objects.filter(role='CLIENT').count()
    total_translators = UserProfile.objects.filter(role='TRANSLATOR').count()
    
    # Translation statistics
    pending_quotes = TranslationRequest.objects.filter(status='QUOTE').count()
    active_translations = TranslationRequest.objects.filter(
        status__in=['PAID', 'ASSIGNED', 'IN_PROGRESS']
    ).count()
    
    # Recent activity
    recent_translations = TranslationRequest.objects.order_by('-created_at')[:10]
    recent_users = UserProfile.objects.order_by('-created_at')[:10]
    
    # Revenue statistics (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_revenue = TranslationRequest.objects.filter(
        status='COMPLETED',
        completed_date__gte=thirty_days_ago
    ).aggregate(Sum('client_price'))['client_price__sum'] or 0
    
    context = {
        'total_users': total_users,
        'total_clients': total_clients,
        'total_translators': total_translators,
        'pending_quotes': pending_quotes,
        'active_translations': active_translations,
        'recent_translations': recent_translations,
        'recent_users': recent_users,
        'monthly_revenue': monthly_revenue
    }
    
    return render(request, 'admin/dashboard.html', context)

@login_required
@admin_required
def manage_users_view(request):
    """
    View to manage all users of the platform
    """
    users = UserProfile.objects.all().select_related('user')
    
    # Filter by role
    role = request.GET.get('role')
    if role:
        users = users.filter(role=role)
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        users = users.filter(account_status=status)
    
    # Search functionality
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(user__email__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    
    paginator = Paginator(users, 20)
    page = request.GET.get('page')
    users_page = paginator.get_page(page)
    
    context = {
        'users': users_page,
        'role_choices': UserProfile.ROLE_CHOICES,
        'status_choices': UserProfile.account_status.field.choices
    }
    
    return render(request, 'admin/manage_users.html', context)

@login_required
@admin_required
def manage_translations_view(request):
    """
    View to manage all translations
    """
    translations = TranslationRequest.objects.all().select_related(
        'client', 'translator', 'source_language', 'target_language'
    )
    
    # Filtering
    status = request.GET.get('status')
    if status:
        translations = translations.filter(status=status)
    
    type_filter = request.GET.get('type')
    if type_filter:
        translations = translations.filter(translation_type=type_filter)
    
    # Search
    search = request.GET.get('search')
    if search:
        translations = translations.filter(
            Q(title__icontains=search) |
            Q(client__email__icontains=search) |
            Q(translator__email__icontains=search)
        )
    
    paginator = Paginator(translations, 20)
    page = request.GET.get('page')
    translations_page = paginator.get_page(page)
    
    context = {
        'translations': translations_page,
        'status_choices': TranslationRequest.STATUS_CHOICES,
        'type_choices': TranslationRequest.TYPE_CHOICES
    }
    
    return render(request, 'admin/manage_translations.html', context)

@login_required
@admin_required
def process_quote_view(request, quote_id):
    """
    Process a quote request by setting prices
    """
    quote = get_object_or_404(TranslationRequest, id=quote_id, status='QUOTE')
    
    if request.method == 'POST':
        form = QuoteProcessForm(request.POST, instance=quote)
        if form.is_valid():
            processed_quote = form.save(commit=False)
            processed_quote.status = 'QUOTED'
            processed_quote.save()
            
            # Send email notification
            send_quote_processed_email(processed_quote)
            
            messages.success(request, 'Quote processed successfully.')
            return redirect('admin:manage_translations')
    else:
        form = QuoteProcessForm(instance=quote)
    
    return render(request, 'admin/process_quote.html', {
        'form': form,
        'quote': quote
    })

@login_required
@admin_required
def assign_translator_view(request, translation_id):
    """
    Assign a translator to a paid translation
    """
    translation = get_object_or_404(
        TranslationRequest,
        id=translation_id,
        status='PAID'
    )
    
    if request.method == 'POST':
        form = TranslatorAssignmentForm(request.POST, translation=translation)
        if form.is_valid():
            translator = form.cleaned_data['translator']
            
            translation.translator = translator
            translation.status = 'ASSIGNED'
            translation.assigned_by = request.user
            translation.save()
            
            # Send email notification
            send_translator_assignment_email(translation)
            
            messages.success(request, 'Translator assigned successfully.')
            return redirect('admin:manage_translations')
    else:
        form = TranslatorAssignmentForm(translation=translation)
    
    return render(request, 'admin/assign_translator.html', {
        'form': form,
        'translation': translation
    })

@login_required
@admin_required
def payment_management_view(request):
    """
    Manage payments and financial reports
    """
    # Get all completed translations
    completed_translations = TranslationRequest.objects.filter(
        status='COMPLETED'
    ).select_related('client', 'translator')
    
    # Calculate total revenue
    total_revenue = completed_translations.aggregate(
        Sum('client_price')
    )['client_price__sum'] or 0
    
    # Calculate translator payments
    total_translator_payments = completed_translations.aggregate(
        Sum('translator_price')
    )['translator_price__sum'] or 0
    
    # Calculate platform profit
    platform_profit = total_revenue - total_translator_payments
    
    context = {
        'completed_translations': completed_translations,
        'total_revenue': total_revenue,
        'total_translator_payments': total_translator_payments,
        'platform_profit': platform_profit
    }
    
    return render(request, 'admin/payment_management.html', context)

@login_required
@admin_required
def reports_view(request):
    """
    Generate various platform reports
    """
    report_type = request.GET.get('type', 'user_activity')
    
    if report_type == 'user_activity':
        data = generate_user_activity_report()
    elif report_type == 'financial':
        data = generate_financial_report()
    elif report_type == 'translation_stats':
        data = generate_translation_stats_report()
    
    # Handle CSV export
    if request.GET.get('format') == 'csv':
        return export_report_to_csv(data, report_type)
    
    context = {
        'report_type': report_type,
        'data': data
    }
    
    return render(request, 'admin/reports.html', context)

def generate_user_activity_report():
    """Helper function to generate user activity report"""
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    return {
        'new_users': UserProfile.objects.filter(
            created_at__gte=thirty_days_ago
        ).count(),
        'active_clients': TranslationRequest.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('client').distinct().count(),
        'active_translators': TranslationRequest.objects.filter(
            status='COMPLETED',
            completed_date__gte=thirty_days_ago
        ).values('translator').distinct().count(),
    }

def generate_financial_report():
    """Helper function to generate financial report"""
    thirty_days_ago = timezone.now() - timedelta(days=30)
    completed_translations = TranslationRequest.objects.filter(
        status='COMPLETED',
        completed_date__gte=thirty_days_ago
    )
    
    return {
        'total_revenue': completed_translations.aggregate(Sum('client_price'))['client_price__sum'] or 0,
        'translator_payments': completed_translations.aggregate(Sum('translator_price'))['translator_price__sum'] or 0,
        'average_translation_price': completed_translations.aggregate(Avg('client_price'))['client_price__avg'] or 0,
    }

def generate_translation_stats_report():
    """Helper function to generate translation statistics report"""
    return {
        'translations_by_type': TranslationRequest.objects.values(
            'translation_type'
        ).annotate(count=Count('id')),
        'translations_by_language': TranslationRequest.objects.values(
            'source_language__name',
            'target_language__name'
        ).annotate(count=Count('id')),
        'completion_rate': calculate_completion_rate(),
    }

def export_report_to_csv(data, report_type):
    """Helper function to export report data to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(data.keys())
    writer.writerow(data.values())
    
    return response