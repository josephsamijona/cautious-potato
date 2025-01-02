from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from translations.models import UserProfile, TranslatorLanguage, Language
# forms/auth.py (ajouter ces nouveaux formulaires)

from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import get_user_model

class EmailAuthenticationForm(AuthenticationForm):
    def clean_username(self):
        """
        Override to allow login with email
        """
        username = self.cleaned_data.get('username')
        # Check if the input is an email
        if '@' in username:
            try:
                user = get_user_model().objects.get(email=username)
                return user.username
            except get_user_model().DoesNotExist:
                raise forms.ValidationError("No user found with this email address.")
        return username

class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data['email']
        if not get_user_model().objects.filter(email=email).exists():
            raise forms.ValidationError("No user found with this email address.")
        return email

class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].help_text = "Your password must contain at least 8 characters."
        
        
class UserRegistrationForm(UserCreationForm):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    ROLE_CHOICES = [
        ('CLIENT', 'Client'),
        ('TRANSLATOR', 'Translator')
    ]
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'role')

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists")
        return email

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role']
            )
        return user

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
        fields = [
            'phone_primary', 'phone_secondary',
            'address_line1', 'address_line2', 'city',
            'state_province', 'postal_code', 'country',
            'company_name', 'tax_id', 'profile_picture',
            'date_of_birth'
        ]

class ClientProfileForm(BaseProfileForm):
    pass

class TranslatorProfileForm(BaseProfileForm):
    languages = forms.ModelMultipleChoiceField(
        queryset=Language.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    
    # Optional bank fields
    bank_name = forms.CharField(required=False)
    bank_account_name = forms.CharField(required=False)
    bank_account_number = forms.CharField(required=False)
    bank_routing_number = forms.CharField(required=False)
    bank_swift_code = forms.CharField(required=False)
    bank_iban = forms.CharField(required=False)
    bank_account_type = forms.ChoiceField(
        choices=UserProfile.bank_account_type.field.choices,
        required=False
    )
    
    class Meta(BaseProfileForm.Meta):
        fields = BaseProfileForm.Meta.fields + [
            'bank_name', 'bank_account_name', 'bank_account_number',
            'bank_routing_number', 'bank_swift_code', 'bank_iban',
            'bank_account_type'
        ]

    def clean(self):
        cleaned_data = super().clean()
        # If any bank field is filled, make sure all required bank fields are filled
        bank_fields = ['bank_name', 'bank_account_name', 'bank_account_number', 'bank_routing_number']
        has_bank_info = any(cleaned_data.get(field) for field in bank_fields)
        
        if has_bank_info:
            missing_fields = [field for field in bank_fields if not cleaned_data.get(field)]
            if missing_fields:
                raise forms.ValidationError(
                    "If providing bank information, please fill in all required fields: " + 
                    ", ".join(missing_fields)
                )
        
        return cleaned_data
    