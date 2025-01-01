from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    UserProfile, Language, TranslatorLanguage, TranslationRequest,
    TranslatorRating, EmailVerification, PasswordReset, OTPVerification,
    NotificationPreference, TranslationHistory
)

# Inline pour UserProfile dans l'admin User
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'role', 'profile_picture', 'date_of_birth', 'account_type'
            )
        }),
        ('Contact Information', {
            'fields': (
                'phone_primary', 'phone_secondary'
            )
        }),
        ('Address', {
            'fields': (
                'address_line1', 'address_line2', 'city', 
                'state_province', 'postal_code', 'country'
            )
        }),
        ('Company Information', {
            'fields': ('company_name', 'tax_id')
        }),
        ('Verification Status', {
            'fields': (
                'is_email_verified', 'is_phone_verified', 
                'is_address_verified', 'account_status'
            )
        }),
        ('Banking Information', {
            'fields': (
                'bank_name', 'bank_account_type', 'bank_account_name',
                'bank_account_number', 'bank_routing_number',
                'bank_swift_code', 'bank_iban'
            ),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('last_login_ip', 'timezone', 'preferred_language'),
            'classes': ('collapse',)
        })
    )

# Extension de UserAdmin pour inclure UserProfile
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff', 'get_verification_status')
    list_filter = BaseUserAdmin.list_filter + ('profile__role', 'profile__account_status')
    search_fields = BaseUserAdmin.search_fields + ('profile__phone_primary', 'profile__company_name')

    def get_role(self, obj):
        return obj.profile.get_role_display()
    get_role.short_description = 'Role'

    def get_verification_status(self, obj):
        status = obj.profile.account_status
        colors = {
            'PENDING': 'orange',
            'ACTIVE': 'green',
            'SUSPENDED': 'red',
            'BLOCKED': 'grey'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors[status],
            status
        )
    get_verification_status.short_description = 'Status'

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('name',)

@admin.register(TranslatorLanguage)
class TranslatorLanguageAdmin(admin.ModelAdmin):
    list_display = ('translator', 'language', 'proficiency', 'is_verified')
    list_filter = ('proficiency', 'is_verified', 'language')
    search_fields = ('translator__user__username', 'language__name')
    raw_id_fields = ('translator',)

@admin.register(TranslationRequest)
class TranslationRequestAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'client', 'translator', 'source_language', 
        'target_language', 'status', 'deadline', 'is_paid'
    )
    list_filter = ('status', 'translation_type', 'is_paid')
    search_fields = (
        'title', 'client__username', 'translator__username',
        'description'
    )
    raw_id_fields = ('client', 'translator', 'assigned_by')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title', 'description', 'source_language', 
                'target_language', 'status'
            )
        }),
        ('Dates', {
            'fields': ('deadline', 'start_date', 'completed_date')
        }),
        ('Documents', {
            'fields': ('original_document', 'translated_document')
        }),
        ('Financial', {
            'fields': ('client_price', 'translator_price', 'is_paid', 'stripe_payment_id'),
            'classes': ('collapse',)
        }),
        ('Location', {
            'fields': ('translation_type', 'address'),
            'classes': ('collapse',)
        }),
        ('Assignment', {
            'fields': ('client', 'translator', 'assigned_by', 'notes')
        })
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Si c'est une nouvelle création
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(TranslatorRating)
class TranslatorRatingAdmin(admin.ModelAdmin):
    list_display = ('translation', 'translator', 'rated_by', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('translator__username', 'comment')
    raw_id_fields = ('translation', 'translator', 'rated_by')

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_notifications', 'sms_notifications', 'reminder_frequency')
    list_filter = ('email_notifications', 'sms_notifications')
    search_fields = ('user__username', 'user__email')

@admin.register(TranslationHistory)
class TranslationHistoryAdmin(admin.ModelAdmin):
    list_display = ('translation', 'status', 'changed_by', 'changed_at')
    list_filter = ('status', 'changed_at')
    search_fields = ('translation__title', 'notes')
    raw_id_fields = ('translation', 'changed_by')
    date_hierarchy = 'changed_at'

# Classes pour la vérification
class BaseVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'expires_at', 'is_used', 'is_valid')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('token', 'created_at')

    def is_valid(self, obj):
        valid = obj.is_valid()
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if valid else 'red',
            'Valid' if valid else 'Expired'
        )

@admin.register(EmailVerification)
class EmailVerificationAdmin(BaseVerificationAdmin):
    pass

@admin.register(PasswordReset)
class PasswordResetAdmin(BaseVerificationAdmin):
    pass

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'expires_at', 'is_used', 'is_valid')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('otp', 'created_at')

# Ré-enregistrer UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)