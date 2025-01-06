# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.admin import AdminSite
from django.db.models import Count, Sum
from django import forms
from .models import UserProfile, Language, TranslatorLanguage,Notification,TranslationRequest,TranslationHistory,NotificationPreference,TranslatorRating
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.db.models import Avg
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
class CustomAdminSite(AdminSite):
    """
    Custom Admin Site Configuration
    Provides a personalized admin interface with dashboard
    """
    site_header = 'Translation Platform Administration'
    site_title = 'Translation Admin'
    index_title = 'Management Dashboard'

    def index(self, request, extra_context=None):
        """Custom admin dashboard with key metrics"""
        extra_context = extra_context or {}
        
        # Key metrics for dashboard
        extra_context.update({
            'total_translations': TranslationRequest.objects.count(),
            'pending_quotes': TranslationRequest.objects.filter(status='QUOTE').count(),
            'active_translators': UserProfile.objects.filter(
                role='TRANSLATOR',
                user__is_active=True
            ).count(),
            'active_clients': UserProfile.objects.filter(
                role='CLIENT',
                user__is_active=True
            ).count(),
            'urgent_translations': TranslationRequest.objects.filter(
                status__in=['ASSIGNED', 'IN_PROGRESS'],
                deadline__lte=timezone.now() + timezone.timedelta(days=2)
            ).count(),
        })
        
        return super().index(request, extra_context)

admin_site = CustomAdminSite(name='admin')

class UserProfileInline(admin.StackedInline):
    """
    Inline Profile Editor for User Management
    Allows editing profile information directly in user admin
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('role', 'profile_picture', 'date_of_birth')
        }),
        ('Contact Details', {
            'fields': ('phone_primary', 'phone_secondary')
        }),
        ('Address Information', {
            'fields': (
                'address_line1', 'address_line2', 'city',
                'state_province', 'postal_code', 'country'
            )
        }),
        ('Company Details', {
            'fields': ('company_name', 'tax_id'),
            'classes': ('collapse',)
        }),
        ('Account Settings', {
            'fields': (
                'account_type', 'account_status',
                'preferred_language', 'timezone'
            )
        }),
        ('Verification Status', {
            'fields': (
                'is_email_verified',
                'is_phone_verified',
                'is_address_verified'
            ),
            'classes': ('collapse',)
        })
    )

class CustomUserAdmin(UserAdmin):
    """
    Enhanced User Admin
    Provides advanced user management capabilities
    """
    inlines = (UserProfileInline,)
    list_display = (
        'username', 'email', 'get_role',
        'get_status', 'date_joined', 'is_active',
        'get_last_login'
    )
    list_filter = ('is_active', 'profile__role', 'profile__account_status')
    search_fields = (
        'username', 'first_name', 'last_name',
        'email', 'profile__phone_primary'
    )
    ordering = ('-date_joined',)
    actions = [
        'activate_users',
        'deactivate_users',
        'reset_password',
        'verify_email'
    ]

    def get_role(self, obj):
        return obj.profile.get_role_display()
    get_role.short_description = 'Role'
    get_role.admin_order_field = 'profile__role'

    def get_status(self, obj):
        status = obj.profile.account_status
        colors = {
            'PENDING': 'orange',
            'ACTIVE': 'green',
            'SUSPENDED': 'red',
            'BLOCKED': 'darkred'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(status, 'black'),
            obj.profile.get_account_status_display()
        )
    get_status.short_description = 'Status'
    
    def get_last_login(self, obj):
        if obj.last_login:
            return format_html(
                '<span title="{}">{} ago</span>',
                obj.last_login.strftime('%Y-%m-%d %H:%M:%S'),
                timezone.now() - obj.last_login
            )
        return 'Never'
    get_last_login.short_description = 'Last Login'

    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} users have been successfully activated.'
        )
    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} users have been successfully deactivated.'
        )
    deactivate_users.short_description = "Deactivate selected users"

    def reset_password(self, request, queryset):
        for user in queryset:
            password = User.objects.make_random_password()
            user.set_password(password)
            user.save()
            # Here you would typically send an email with the new password
            self.message_user(
                request,
                f'Password reset for {user.email}. New password: {password}'
            )
    reset_password.short_description = "Reset passwords for selected users"

    def verify_email(self, request, queryset):
        for user in queryset:
            user.profile.is_email_verified = True
            user.profile.save()
        self.message_user(
            request,
            f'Email verified for {queryset.count()} users.'
        )
    verify_email.short_description = "Mark email as verified"

    # Style configuration
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }

# Re-register User admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    """
    Language Management
    Handles available languages in the system
    """
    list_display = ('name', 'code', 'is_active', 'get_translator_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    actions = ['activate_languages', 'deactivate_languages']

    def get_translator_count(self, obj):
        count = obj.translatorlanguage_set.count()
        return format_html(
            '<a href="{}?language__id__exact={}">{} translators</a>',
            reverse('admin:app_translatorlanguage_changelist'),
            obj.id,
            count
        )
    get_translator_count.short_description = 'Translators'

    def activate_languages(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} languages have been activated.')
    activate_languages.short_description = "Activate selected languages"

    def deactivate_languages(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} languages have been deactivated.')
    deactivate_languages.short_description = "Deactivate selected languages"
    
    
class DeadlineFilter(admin.SimpleListFilter):
    """
    Custom filter for translation deadlines
    """
    title = 'Deadline Status'
    parameter_name = 'deadline_status'

    def lookups(self, request, model_admin):
        return (
            ('urgent', 'Urgent (< 48 hours)'),
            ('this_week', 'This Week'),
            ('next_week', 'Next Week'),
            ('later', 'Later'),
            ('overdue', 'Overdue')
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'urgent':
            return queryset.filter(
                deadline__lte=now + timezone.timedelta(hours=48),
                deadline__gte=now
            )
        elif self.value() == 'this_week':
            week_end = now + timezone.timedelta(days=7)
            return queryset.filter(deadline__range=[now, week_end])
        elif self.value() == 'next_week':
            week_start = now + timezone.timedelta(days=7)
            week_end = now + timezone.timedelta(days=14)
            return queryset.filter(deadline__range=[week_start, week_end])
        elif self.value() == 'overdue':
            return queryset.filter(deadline__lt=now)
        elif self.value() == 'later':
            return queryset.filter(
                deadline__gt=now + timezone.timedelta(days=14)
            )

@admin.register(TranslationRequest)
class TranslationRequestAdmin(admin.ModelAdmin):
    """
    Translation Request Management
    Handles all translation projects and quotes
    """
    list_display = (
        'id', 
        'title', 
        'client_link', 
        'translator_link', 
        'source_language', 
        'target_language',
        'status_colored',
        'deadline_status',
        'formatted_price',
        'created_at'
    )
    
    list_filter = (
        'status',
        'translation_type',
        DeadlineFilter,
        'is_paid',
        'source_language',
        'target_language'
    )
    
    search_fields = (
        'title',
        'description',
        'client__username',
        'client__email',
        'translator__username'
    )
    
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    actions = [
        'approve_quotes',
        'reject_quotes',
        'mark_as_paid',
        'mark_as_completed',
        'assign_urgent',
        'send_reminder',
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title', 'description', 'translation_type',
                'source_language', 'target_language'
            )
        }),
        ('Client and Translator', {
            'fields': ('client', 'translator', 'assigned_by')
        }),
        ('Pricing', {
            'fields': (
                'client_price',
                'translator_price',
                'is_paid',
                'stripe_payment_id'
            )
        }),
        ('Timeline', {
            'fields': (
                'deadline',
                'start_date',
                'completed_date'
            )
        }),
        ('Status and Documents', {
            'fields': (
                'status',
                'original_document',
                'translated_document'
            )
        }),
        ('Additional Details', {
            'classes': ('collapse',),
            'fields': (
                'notes',
                'additional_context',
                'created_at',
                'updated_at'
            )
        })
    )

    def status_colored(self, obj):
        colors = {
            'QUOTE': '#FFA500',      # Orange
            'QUOTED': '#4169E1',     # Royal Blue
            'PAID': '#9370DB',       # Medium Purple
            'ASSIGNED': '#FFD700',   # Gold
            'IN_PROGRESS': '#32CD32', # Lime Green
            'COMPLETED': '#228B22',   # Forest Green
            'REJECTED': '#DC143C',    # Crimson
            'CANCELLED': '#A9A9A9'    # Dark Gray
        }
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#777'),
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'

    def deadline_status(self, obj):
        if not obj.deadline:
            return '-'
        
        now = timezone.now()
        days_remaining = (obj.deadline - now).days
        
        if days_remaining < 0:
            return format_html(
                '<span style="color: red;">Overdue by {} days</span>',
                abs(days_remaining)
            )
        elif days_remaining == 0:
            return format_html(
                '<span style="color: orange;">Due today</span>'
            )
        elif days_remaining <= 2:
            return format_html(
                '<span style="color: orange;">{} days left</span>',
                days_remaining
            )
        else:
            return format_html(
                '<span style="color: green;">{} days left</span>',
                days_remaining
            )
    deadline_status.short_description = 'Deadline'

    def client_link(self, obj):
        if obj.client:
            url = reverse('admin:auth_user_change', args=[obj.client.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.client.email
            )
        return "-"
    client_link.short_description = 'Client'

    def translator_link(self, obj):
        if obj.translator:
            url = reverse('admin:auth_user_change', args=[obj.translator.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.translator.email
            )
        return "-"
    translator_link.short_description = 'Translator'

    def formatted_price(self, obj):
        if obj.client_price:
            return f"${obj.client_price:,.2f}"
        return "-"
    formatted_price.short_description = 'Price'

    # Admin Actions
    def approve_quotes(self, request, queryset):
        updated = queryset.filter(status='QUOTE').update(
            status='QUOTED'
        )
        self.message_user(
            request,
            f'{updated} quotes have been approved.'
        )
    approve_quotes.short_description = "Approve selected quotes"

    def reject_quotes(self, request, queryset):
        updated = queryset.filter(status='QUOTE').update(
            status='REJECTED'
        )
        self.message_user(
            request,
            f'{updated} quotes have been rejected.'
        )
    reject_quotes.short_description = "Reject selected quotes"

    def mark_as_paid(self, request, queryset):
        updated = queryset.filter(status='QUOTED').update(
            status='PAID',
            is_paid=True
        )
        self.message_user(
            request,
            f'{updated} translations marked as paid.'
        )
    mark_as_paid.short_description = "Mark selected as paid"

    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(
            status='IN_PROGRESS'
        ).update(
            status='COMPLETED',
            completed_date=timezone.now()
        )
        self.message_user(
            request,
            f'{updated} translations marked as completed.'
        )
    mark_as_completed.short_description = "Mark selected as completed"

    def assign_urgent(self, request, queryset):
        """
        Quickly assign urgent translations to available translators
        """
        assigned_count = 0
        for translation in queryset.filter(translator__isnull=True):
            # Find suitable translator based on languages and availability
            available_translator = UserProfile.objects.filter(
                role='TRANSLATOR',
                user__is_active=True,
                translatorlanguage__language=translation.target_language,
                translatorlanguage__is_verified=True
            ).first()
            
            if available_translator:
                translation.translator = available_translator.user
                translation.status = 'ASSIGNED'
                translation.assigned_by = request.user
                translation.save()
                assigned_count += 1

        self.message_user(
            request,
            f'{assigned_count} translations have been assigned to translators.'
        )
    assign_urgent.short_description = "Quick assign to available translators"

    def send_reminder(self, request, queryset):
        """Send reminder to relevant parties"""
        for translation in queryset:
            if translation.status == 'IN_PROGRESS':
                # Create notification for translator
                Notification.objects.create(
                    user=translation.translator,
                    type='PROGRESS',
                    title='Translation Reminder',
                    message=f'Reminder: Translation "{translation.title}" is due on {translation.deadline}'
                )
            elif translation.status == 'QUOTED':
                # Create notification for client
                Notification.objects.create(
                    user=translation.client,
                    type='QUOTE',
                    title='Quote Reminder',
                    message=f'Reminder: You have a pending quote for "{translation.title}"'
                )
        
        self.message_user(request, 'Reminders sent successfully.')
    send_reminder.short_description = "Send reminders"

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new translation
            if not obj.client:
                obj.client = request.user
        super().save_model(request, obj, form, change)
        
        
@admin.register(TranslatorRating)
class TranslatorRatingAdmin(admin.ModelAdmin):
    """
    Translator Rating Management
    Handles review and rating system
    """
    list_display = (
        'translation',
        'translator_name',
        'rated_by',
        'rating_stars',
        'created_at'
    )
    list_filter = ('rating', 'created_at')
    search_fields = (
        'translator__username',
        'rated_by__username',
        'comment'
    )
    readonly_fields = ('created_at',)

    def translator_name(self, obj):
        return f"{obj.translator.get_full_name() or obj.translator.username}"
    translator_name.short_description = 'Translator'

    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html(
            '<span style="color: gold;">{}</span>',
            stars
        )
    rating_stars.short_description = 'Rating'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Notification Management
    Handles system notifications and alerts
    """
    list_display = (
        'user',
        'type',
        'title',
        'is_read',
        'created_at_formatted'
    )
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    actions = ['mark_as_read', 'mark_as_unread', 'resend_notification']
    
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M")
    created_at_formatted.short_description = 'Created'

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = "Mark selected as read"

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} notifications marked as unread.')
    mark_as_unread.short_description = "Mark selected as unread"

    def resend_notification(self, request, queryset):
        for notification in queryset:
            # Implement notification resending logic
            pass
    resend_notification.short_description = "Resend selected notifications"

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """
    Notification Preferences Management
    Handles user notification settings
    """
    list_display = (
        'user',
        'email_notifications',
        'sms_notifications',
        'reminder_frequency'
    )
    list_filter = (
        'email_notifications',
        'sms_notifications'
    )
    search_fields = ('user__username', 'user__email')

@admin.register(TranslationHistory)
class TranslationHistoryAdmin(admin.ModelAdmin):
    """
    Translation History Management
    Tracks all changes to translations
    """
    list_display = (
        'translation',
        'status',
        'changed_by',
        'changed_at_formatted'
    )
    list_filter = ('status', 'changed_at')
    search_fields = (
        'translation__title',
        'changed_by__username',
        'notes'
    )
    readonly_fields = ('changed_at',)

    def changed_at_formatted(self, obj):
        return obj.changed_at.strftime("%Y-%m-%d %H:%M")
    changed_at_formatted.short_description = 'Changed At'

# Admin Dashboard Customization
class TranslationDashboard:
    """
    Custom Dashboard Widget
    Provides overview of translation platform
    """
    template = 'admin/dashboard.html'

    def get_context(self):
        return {
            'total_translations': TranslationRequest.objects.count(),
            'pending_quotes': TranslationRequest.objects.filter(
                status='QUOTE'
            ).count(),
            'in_progress': TranslationRequest.objects.filter(
                status='IN_PROGRESS'
            ).count(),
            'completed_today': TranslationRequest.objects.filter(
                status='COMPLETED',
                completed_date__date=timezone.now().date()
            ).count(),
            'revenue_this_month': TranslationRequest.objects.filter(
                is_paid=True,
                created_at__month=timezone.now().month
            ).aggregate(Sum('client_price'))['client_price__sum'] or 0,
            'active_translators': UserProfile.objects.filter(
                role='TRANSLATOR',
                user__is_active=True
            ).count(),
        }

# Custom Admin Site Configuration (continuation)
class CustomAdminSite(AdminSite):
    def get_app_list(self, request):
        """
        Customize the admin sidebar/app list
        """
        app_list = super().get_app_list(request)
        
        # Add custom app groups
        custom_app_list = [
            {
                'name': 'User Management',
                'app_label': 'users',
                'models': [
                    {'name': 'Users', 'object_name': 'User'},
                    {'name': 'Profiles', 'object_name': 'UserProfile'},
                ]
            },
            {
                'name': 'Translation Management',
                'app_label': 'translations',
                'models': [
                    {'name': 'Translations', 'object_name': 'TranslationRequest'},
                    {'name': 'Languages', 'object_name': 'Language'},
                    {'name': 'History', 'object_name': 'TranslationHistory'},
                ]
            },
            {
                'name': 'Reviews & Ratings',
                'app_label': 'reviews',
                'models': [
                    {'name': 'Ratings', 'object_name': 'TranslatorRating'},
                ]
            },
            {
                'name': 'Notifications',
                'app_label': 'notifications',
                'models': [
                    {'name': 'Notifications', 'object_name': 'Notification'},
                    {'name': 'Preferences', 'object_name': 'NotificationPreference'},
                ]
            }
        ]
        
        return custom_app_list + app_list

# Custom Admin Forms
class TranslatorLanguageAdminForm(forms.ModelForm):
    """
    Custom form for TranslatorLanguage admin
    """
    class Meta:
        model = TranslatorLanguage
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('is_verified') and not cleaned_data.get('certification_document'):
            raise ValidationError({
                'is_verified': 'Cannot verify language without certification document'
            })
        return cleaned_data

# Custom CSS for Admin Interface
ADMIN_STYLES = """
/* Custom Admin Styles */
:root {
    --primary-color: #2c3e50;
    --secondary-color: #34495e;
    --success-color: #27ae60;
    --warning-color: #f1c40f;
    --danger-color: #e74c3c;
}

/* Header Styling */
#header {
    background: var(--primary-color);
    color: white;
}

/* Module Headers */
.module h2, .module caption {
    background: var(--secondary-color);
}

/* Status Tags */
.status-tag {
    padding: 3px 8px;
    border-radius: 3px;
    color: white;
}

/* Responsive Design */
@media (max-width: 767px) {
    .change-list .filtered {
        margin-right: 0;
    }
    
    #changelist-filter {
        max-width: 100%;
    }
    
    .change-list .filtered .results {
        margin-right: 0;
    }
}

/* Dashboard Widgets */
.dashboard-widget {
    background: white;
    padding: 15px;
    border-radius: 4px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}

.stat-box {
    text-align: center;
    padding: 20px;
    background: #f8f9fa;
    border-radius: 4px;
}

.stat-number {
    font-size: 24px;
    font-weight: bold;
    color: var(--primary-color);
}

.stat-label {
    color: #666;
    margin-top: 5px;
}
"""