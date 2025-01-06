from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django import forms
from django.utils import timezone
from . import models

# Admin interface configuration
admin.site.site_header = 'Translation Platform - Administration'
admin.site.site_title = 'Translation Admin'
admin.site.index_title = 'Platform Management'

class UserCreationForm(forms.ModelForm):
    role = forms.ChoiceField(choices=models.UserProfile.ROLE_CHOICES, initial='CLIENT')
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            models.UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role']
            )
        return user

class UserProfileInline(admin.StackedInline):
    model = models.UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    extra = 1

class CustomUserAdmin(UserAdmin):
    add_form = UserCreationForm
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_active', 'date_joined')
    list_filter = ('is_active', 'profile__role', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'profile__phone_primary')
    ordering = ('-date_joined',)
    actions = ['activate_users', 'deactivate_users', 'reset_password']

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'role', 'is_staff'),
        }),
    )

    def get_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except models.UserProfile.DoesNotExist:
            return 'No Role'
    get_role.short_description = 'Role'

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_users.short_description = "Deactivate selected users"

    def reset_password(self, request, queryset):
        for user in queryset:
            password = User.objects.make_random_password()
            user.set_password(password)
            user.save()
            self.message_user(request, f"New password for {user.email}: {password}")
    reset_password.short_description = "Reset passwords"

@admin.register(models.TranslationRequest)
class TranslationRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'client_link', 'translator_link', 'status_colored', 
                   'source_language', 'target_language', 'deadline_status', 'is_paid')
    list_filter = ('status', 'is_paid', 'translation_type', 'created_at', 'deadline')
    search_fields = ('title', 'description', 'client__username', 'translator__username')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    actions = ['mark_as_paid', 'approve_quote', 'reject_quote', 'assign_translator', 'mark_completed']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'translation_type', 'status')
        }),
        ('Client and Translator', {
            'fields': ('client', 'translator')
        }),
        ('Languages', {
            'fields': ('source_language', 'target_language')
        }),
        ('Price and Payment', {
            'fields': ('client_price', 'translator_price', 'is_paid')
        }),
        ('Dates', {
            'fields': ('deadline', 'start_date', 'completed_date')
        }),
        ('Documents', {
            'fields': ('original_document', 'translated_document')
        }),
    )

    def status_colored(self, obj):
        colors = {
            'QUOTE': '#007bff',     # Blue
            'QUOTED': '#ffc107',    # Yellow
            'PAID': '#17a2b8',      # Cyan
            'ASSIGNED': '#6f42c1',  # Purple
            'IN_PROGRESS': '#28a745', # Green
            'COMPLETED': '#198754',   # Dark green
            'REJECTED': '#dc3545',    # Red
            'CANCELLED': '#6c757d'    # Gray
        }
        return format_html(
            '<span style="color: {}; font-weight: bold">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'

    def deadline_status(self, obj):
        if not obj.deadline:
            return "-"
        days = (obj.deadline.date() - timezone.now().date()).days
        if days < 0:
            return format_html('<span style="color: red">Overdue ({} days)</span>', abs(days))
        elif days == 0:
            return format_html('<span style="color: orange">Today</span>')
        return format_html('<span style="color: green">{} days</span>', days)
    deadline_status.short_description = 'Deadline'

    def client_link(self, obj):
        if obj.client:
            url = reverse('admin:auth_user_change', args=[obj.client.id])
            return format_html('<a href="{}">{}</a>', url, obj.client.username)
        return "-"
    client_link.short_description = 'Client'

    def translator_link(self, obj):
        if obj.translator:
            url = reverse('admin:auth_user_change', args=[obj.translator.id])
            return format_html('<a href="{}">{}</a>', url, obj.translator.username)
        return "-"
    translator_link.short_description = 'Translator'

    def mark_as_paid(self, request, queryset):
        queryset.update(is_paid=True, status='PAID')
        self.message_user(request, f"{queryset.count()} translation(s) marked as paid")
    mark_as_paid.short_description = "Mark as paid"

    def approve_quote(self, request, queryset):
        count = 0
        for translation in queryset.filter(status='QUOTE'):
            translation.status = 'QUOTED'
            translation.save()
            count += 1
            # Create notification
            models.Notification.objects.create(
                user=translation.client,
                type='QUOTE',
                title='Quote Approved',
                message=f'Your quote for "{translation.title}" has been approved.'
            )
        self.message_user(request, f"{count} quote(s) approved")
    approve_quote.short_description = "Approve quotes"

    def reject_quote(self, request, queryset):
        count = queryset.filter(status='QUOTE').update(status='REJECTED')
        self.message_user(request, f"{count} quote(s) rejected")
    reject_quote.short_description = "Reject quotes"

    def mark_completed(self, request, queryset):
        count = queryset.update(status='COMPLETED', completed_date=timezone.now())
        self.message_user(request, f"{count} translation(s) marked as completed")
    mark_completed.short_description = "Mark as completed"

@admin.register(models.Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'translator_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    
    def translator_count(self, obj):
        return obj.translatorlanguage_set.count()
    translator_count.short_description = 'Translators'

@admin.register(models.TranslatorLanguage)
class TranslatorLanguageAdmin(admin.ModelAdmin):
    list_display = ('translator', 'language', 'proficiency', 'is_verified')
    list_filter = ('proficiency', 'is_verified', 'language')
    search_fields = ('translator__user__username', 'language__name')
    actions = ['verify_languages', 'unverify_languages']

    def verify_languages(self, request, queryset):
        count = queryset.update(is_verified=True)
        self.message_user(request, f"{count} language(s) verified")
    verify_languages.short_description = "Verify languages"

    def unverify_languages(self, request, queryset):
        count = queryset.update(is_verified=False)
        self.message_user(request, f"{count} language(s) unverified")
    unverify_languages.short_description = "Unverify languages"

@admin.register(models.TranslatorRating)
class TranslatorRatingAdmin(admin.ModelAdmin):
    list_display = ('translation', 'translator', 'rated_by', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('translator__username', 'rated_by__username', 'comment')
    readonly_fields = ('created_at',)

@admin.register(models.Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    actions = ['mark_as_read', 'mark_as_unread']
    readonly_fields = ('created_at',)

    def mark_as_read(self, request, queryset):
        count = queryset.update(is_read=True)
        self.message_user(request, f"{count} notification(s) marked as read")
    mark_as_read.short_description = "Mark as read"

    def mark_as_unread(self, request, queryset):
        count = queryset.update(is_read=False)
        self.message_user(request, f"{count} notification(s) marked as unread")
    mark_as_unread.short_description = "Mark as unread"

# Re-register User with our custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)