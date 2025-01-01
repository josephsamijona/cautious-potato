from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile,TranslationRequest, NotificationPreference
from django_countries.widgets import CountrySelectWidget

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=[('CLIENT', 'Client'), ('TRANSLATOR', 'Translator')])

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'role')

class OTPVerificationForm(forms.Form):
    otp = forms.CharField(
        label='Verification Code',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'placeholder': 'Enter 6-digit code'})
    )

class BaseProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = (
            'profile_picture',
            'date_of_birth',
            'phone_primary',
            'phone_secondary',
            'address_line1',
            'address_line2',
            'city',
            'state_province',
            'postal_code',
            'country',
            'account_type',
            'company_name',
            'tax_id',
        )
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'country': CountrySelectWidget(),
        }

class ClientProfileForm(BaseProfileForm):
    pass

class TranslatorProfileForm(BaseProfileForm):
    class Meta(BaseProfileForm.Meta):
        fields = BaseProfileForm.Meta.fields + (
            'bank_name',
            'bank_account_type',
            'bank_account_name',
            'bank_account_number',
            'bank_routing_number',
            'bank_swift_code',
            'bank_iban',
        )
        
        
class QuoteRequestForm(forms.ModelForm):
    class Meta:
        model = TranslationRequest
        fields = [
            'title',
            'description',
            'source_language',
            'target_language',
            'deadline',
            'translation_type',
            'address',
            'original_document'
        ]
        widgets = {
            'deadline': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'description': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        translation_type = cleaned_data.get('translation_type')
        address = cleaned_data.get('address')

        if translation_type == 'ONSITE' and not address:
            raise forms.ValidationError(
                'Address is required for on-site translations'
            )
        return cleaned_data
    
    
class ClientProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()

    class Meta:
        model = UserProfile
        fields = [
            'profile_picture',
            'phone_primary',
            'phone_secondary',
            'date_of_birth',
            'address_line1',
            'address_line2',
            'city',
            'state_province',
            'postal_code',
            'country',
            'company_name',
            'tax_id',
            'account_type'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = [
            'email_notifications',
            'sms_notifications',
            'reminder_frequency'
        ]
        widgets = {
            'reminder_frequency': forms.Select(choices=[
                (24, 'Daily'),
                (48, 'Every 2 days'),
                (72, 'Every 3 days'),
                (168, 'Weekly')
            ])
        }