from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from django.utils import timezone
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('CLIENT', 'Client'),
        ('TRANSLATOR', 'Translator')
    ]

    # Relation avec User
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Informations de base
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Contact
    phone_primary = PhoneNumberField(blank=True, help_text="Primary contact number")
    phone_secondary = PhoneNumberField(blank=True, help_text="Secondary contact number")
    
    # Adresse détaillée
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = CountryField(blank=True)
    
    # Informations supplémentaires
    company_name = models.CharField(max_length=200, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    
    # Vérification et statut
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_address_verified = models.BooleanField(default=False)
    account_status = models.CharField(max_length=20, default='PENDING', 
        choices=[
            ('PENDING', 'Pending'),
            ('ACTIVE', 'Active'),
            ('SUSPENDED', 'Suspended'),
            ('BLOCKED', 'Blocked')
        ])
    
    # Champs spécifiques pour les traducteurs
    languages = models.ManyToManyField('Language', through='TranslatorLanguage')
    
    # Informations bancaires (pour les traducteurs)
    bank_name = models.CharField(max_length=200, blank=True)
    bank_account_name = models.CharField(max_length=200, blank=True)
    bank_account_number = models.CharField(max_length=200, blank=True)
    bank_routing_number = models.CharField(max_length=200, blank=True)

    # Type de compte
    account_type = models.CharField(max_length=20, default='INDIVIDUAL', 
        choices=[
            ('INDIVIDUAL', 'Individual'),
            ('COMPANY', 'Company'),
            ('ORGANIZATION', 'Organization'),
            ('AGENCY', 'Translation Agency')
        ])
    
    # Type de compte bancaire
    bank_account_type = models.CharField(max_length=20, blank=True,
        choices=[
            ('CHECKING', 'Checking Account'),
            ('SAVINGS', 'Savings Account'),


        ])
    
    # Évaluation (pour les traducteurs)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    number_of_ratings = models.IntegerField(default=0)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Préférences
    preferred_language = models.ForeignKey(
        'Language',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_by_users'
    )
    timezone = models.CharField(max_length=50, default='UTC')

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['role']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.role}"

    def get_full_address(self):
        """Retourne l'adresse complète formatée"""
        parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state_province,
            self.postal_code,
            self.country.name
        ]
        return ', '.join(filter(None, parts))

# Signal pour créer/mettre à jour le profil automatiquement
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        instance.profile.save()
        
class Language(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"
    
    
class TranslatorLanguage(models.Model):
    PROFICIENCY_CHOICES = [
        ('BASIC', 'Basic'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
        ('NATIVE', 'Native'),
        ('CERTIFIED', 'Certified')
    ]

    translator = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    proficiency = models.CharField(max_length=20, choices=PROFICIENCY_CHOICES)
    certification_document = models.FileField(upload_to='certifications/', blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        unique_together = ['translator', 'language']

class TranslationRequest(models.Model):
    STATUS_CHOICES = [
        ('QUOTE', 'Quote Pending'),
        ('QUOTED', 'Quote Sent'),
        ('PAID', 'Quote Paid'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled')
    ]

    TYPE_CHOICES = [
        ('DOCUMENT', 'Document'),
        ('LIVE_ON_SITE', 'Live On Site'),
        ('REMOTE_PHONE', 'Remote Phone'),
        ('REMOTE_MEETING', 'Remote Meeting')
    ]

    # Informations de base
    title = models.CharField(max_length=200)
    description = models.TextField()
    source_language = models.ForeignKey(
        'Language', related_name='source_translations', on_delete=models.PROTECT
    )
    target_language = models.ForeignKey(
        'Language', related_name='target_translations', on_delete=models.PROTECT
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deadline = models.DateTimeField()
    start_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)

    # Documents
    original_document = models.FileField(upload_to='original_documents/', blank=True, null=True)
    translated_document = models.FileField(upload_to='translated_documents/', blank=True, null=True)
    
    # Prix et paiement
    client_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    translator_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    stripe_payment_id = models.CharField(max_length=100, blank=True)

    # Type et localisation
    translation_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    address = models.TextField(blank=True, null=True)  # Utilisé pour "LIVE_ON_SITE"

    # Détails pour les interprétations
    duration_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Durée estimée en minutes")
    meeting_link = models.URLField(blank=True, null=True, help_text="Lien pour les réunions distantes")
    phone_number = models.CharField(max_length=20, blank=True, null=True, help_text="Numéro pour les appels téléphoniques")
    additional_context = models.JSONField(blank=True, null=True, help_text="Métadonnées spécifiques au contexte")

    # Relations
    client = models.ForeignKey(
        User, related_name='client_requests', on_delete=models.PROTECT, blank=True, null=True
    )
    translator = models.ForeignKey(
        User, related_name='translator_requests', null=True, blank=True, on_delete=models.SET_NULL
    )
    assigned_by = models.ForeignKey(
        User, related_name='assigned_translations', null=True, blank=True, on_delete=models.SET_NULL
    )
    
    # Statut
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='QUOTE')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} ({self.source_language} to {self.target_language})"

    def is_live_interpretation(self):
        return self.translation_type in ['LIVE_ON_SITE', 'REMOTE_PHONE', 'REMOTE_MEETING']



class TranslatorRating(models.Model):
    translation = models.ForeignKey(TranslationRequest, on_delete=models.CASCADE)
    translator = models.ForeignKey(User, on_delete=models.CASCADE)
    rated_by = models.ForeignKey(User, related_name='given_ratings', on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['translation', 'translator', 'rated_by']

# Tables pour la vérification et la sécurité
class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

class PasswordReset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

class OTPVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    reminder_frequency = models.IntegerField(default=24)  # en heures

class TranslationHistory(models.Model):
    translation = models.ForeignKey(TranslationRequest, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-changed_at']
        
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('QUOTE', 'Quote Received'),
        ('PROGRESS', 'Translation Progress'),
        ('COMPLETED', 'Translation Completed'),
        ('PAYMENT', 'Payment Required'),
        ('SYSTEM', 'System Notification')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_display()} - {self.title}"