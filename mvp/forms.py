# forms.py
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from translations.models import TranslationRequest
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from django.contrib.auth.models import User
from translations.models import UserProfile
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from django.contrib.auth.forms import  SetPasswordForm
from django.core.validators import RegexValidator
from django.core.validators import MinLengthValidator
from django.contrib.auth import forms as auth_forms
from translations.models import UserProfile, Language, TranslatorLanguage
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberPrefixWidget, RegionalPhoneNumberWidget
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget


User = get_user_model()

class LanguageSelectWidget(forms.CheckboxSelectMultiple):
    template_name = 'widgets/language_select.html'
    option_template_name = 'widgets/language_option.html'


class RegistrationForm(forms.ModelForm):
    ROLE_CHOICES = [
        ('CLIENT', 'Client'),
        ('TRANSLATOR', 'Translator'),
    ]

    first_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name',
            'autocomplete': 'given-name'
        })
    )

    last_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name',
            'autocomplete': 'family-name'
        })
    )

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username',
            'autocomplete': 'username'
        }),
        validators=[MinLengthValidator(3, 'Username must be at least 3 characters long')]
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a password',
            'autocomplete': 'new-password'
        }),
        validators=[MinLengthValidator(8, 'Password must be at least 8 characters long')]
    )

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        widget=forms.RadioSelect(attrs={
            'class': 'role-selector',
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre tous les champs obligatoires
        for field in self.fields:
            self.fields[field].required = True

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            # Vérification de la complexité du mot de passe
            if not any(char.isdigit() for char in password):
                raise forms.ValidationError('Password must contain at least one number.')
            if not any(char.isupper() for char in password):
                raise forms.ValidationError('Password must contain at least one uppercase letter.')
            if not any(char.islower() for char in password):
                raise forms.ValidationError('Password must contain at least one lowercase letter.')
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            user.profile.role = self.cleaned_data['role']
            user.profile.save()
        return user


class OTPVerificationForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        required=True,
        label='OTP Code',
        widget=forms.TextInput(attrs={
            'class': 'otp-input',
            'placeholder': '••••••',
            'maxlength': '6',
            'minlength': '6',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
            'autofocus': True
        })
    )

    def clean_otp_code(self):
        otp_code = self.cleaned_data.get('otp_code')
        if not otp_code.isdigit():
            raise forms.ValidationError('OTP code must contain only numbers.')
        if len(otp_code) != 6:
            raise forms.ValidationError('OTP code must be 6 digits long.')
        return otp_code
    
class LoginForm(auth_forms.AuthenticationForm):
    username = forms.CharField(
        max_length=254,
        label='Email / Username',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email or username',
            'autocomplete': 'username',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        })
    )

    error_messages = {
        'invalid_login': 'Please enter a correct email/username and password.',
        'inactive': 'This account is inactive.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'id': 'loginUsername',
            'aria-describedby': 'usernameHelp'
        })
        self.fields['password'].widget.attrs.update({
            'id': 'loginPassword',
            'aria-describedby': 'passwordHelp'
        })


class BaseProfileForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'placeholder': 'Select your date of birth'
        }),
        required=True
    )

    country = CountryField().formfield(
        widget=CountrySelectWidget(attrs={
            'class': 'form-control country-select',
            'id': 'country-select'
        })
    )
    
    phone_primary = PhoneNumberField(
        region='US',
        required=True,
        error_messages={
            'invalid': 'Enter a valid phone number with country code'
        },
    )
    
    phone_secondary = PhoneNumberField(
        region='US',
        required=False,
    )

    class Meta:
        model = UserProfile
        fields = [
            'date_of_birth', 'country',
            'phone_primary', 'phone_secondary',
            'address_line1', 'address_line2', 
            'city', 'state_province',
            'postal_code'
        ]
        widgets = {
            'address_line1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street address'
            }),
            'address_line2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apartment, suite, unit, etc. (optional)'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'state_province': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State/Province'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ZIP / Postal code'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['address_line1'].required = True
        self.fields['city'].required = True
        self.fields['state_province'].required = True
        self.fields['postal_code'].required = True
        self.fields['country'].required = True

        # Customiser les widgets des champs de téléphone
        self.fields['phone_primary'].widget.attrs.update({
            'class': 'form-control phone-input',
            'placeholder': 'Enter phone number',
            'style': 'width: 100%'
        })
        self.fields['phone_secondary'].widget.attrs.update({
            'class': 'form-control phone-input',
            'placeholder': 'Enter alternative phone number (optional)',
            'style': 'width: 100%'
        })

    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get('country')
        phone_primary = cleaned_data.get('phone_primary')
        phone_secondary = cleaned_data.get('phone_secondary')

        if phone_primary:
            try:
                if not phone_primary.is_valid():
                    self.add_error('phone_primary', 'Please enter a valid phone number for the selected country')
            except AttributeError:
                self.add_error('phone_primary', 'Invalid phone number format')

        if phone_secondary:
            try:
                if not phone_secondary.is_valid():
                    self.add_error('phone_secondary', 'Please enter a valid phone number for the selected country')
            except AttributeError:
                self.add_error('phone_secondary', 'Invalid phone number format')

        return cleaned_data

    class Media:
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.13/css/select2.min.css',
            )
        }
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.13/js/select2.min.js',
        )

class ClientProfileForm(BaseProfileForm):
    account_type = forms.ChoiceField(
        choices=UserProfile._meta.get_field('account_type').choices,
        widget=forms.RadioSelect(attrs={'class': 'account-type-radio'}),
        initial='INDIVIDUAL'
    )
    
    company_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control company-name',
            'placeholder': 'Enter company name'
        })
    )

    class Meta(BaseProfileForm.Meta):
        fields = BaseProfileForm.Meta.fields + ['account_type', 'company_name']

    def clean(self):
        cleaned_data = super().clean()
        account_type = cleaned_data.get('account_type')
        company_name = cleaned_data.get('company_name')
        
        if account_type != 'INDIVIDUAL' and not company_name:
            self.add_error('company_name', 'Company name is required for non-individual accounts.')
        
        return cleaned_data

class TranslatorProfileForm(BaseProfileForm):
    languages = forms.ModelMultipleChoiceField(
        queryset=Language.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'language-checkbox'}),
        required=True
    )
    
    # Champs bancaires optionnels
    bank_fields = ['bank_name', 'bank_account_name', 'bank_account_number', 'bank_routing_number']
    
    class Meta(BaseProfileForm.Meta):
        fields = BaseProfileForm.Meta.fields + ['languages'] + [
            'bank_name', 'bank_account_name', 'bank_account_number', 
            'bank_routing_number', 'bank_account_type'
        ]
        widgets = {
            **BaseProfileForm.Meta.widgets,
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_routing_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_type': forms.Select(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre les champs bancaires optionnels
        for field in self.bank_fields:
            self.fields[field].required = False



        
        
class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )

class PasswordResetForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 6-digit OTP code',
            'maxlength': '6',
            'minlength': '6',
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]*'
        })
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password'
        }),
        validators=[validate_password]
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        })
    )

    def clean_otp_code(self):
        otp = self.cleaned_data.get('otp_code')
        if not otp.isdigit():
            raise forms.ValidationError('OTP code must contain only numbers.')
        if len(otp) != 6:
            raise forms.ValidationError('OTP code must be exactly 6 digits.')
        return otp

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError('Passwords do not match.')
        return cleaned_data
    
    

    
class FlexibleLoginForm(AuthenticationForm):
    """
    Login form that accepts both username and email
    """
    username_or_email = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        }),
        label='Username or Email'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        }),
        label='Password'
    )

    def __init__(self, request=None, *args, **kwargs):
        """
        Override the default constructor to replace username with flexible field
        """
        super().__init__(request, *args, **kwargs)
        # Remove the default username field
        del self.fields['username']

    def clean(self):
        """
        Custom authentication method supporting both username and email
        """
        username_or_email = self.cleaned_data.get('username_or_email')
        password = self.cleaned_data.get('password')

        if username_or_email and password:
            # Try to authenticate
            user = None
            
            # Try authenticating with username
            try:
                user = authenticate(
                    self.request, 
                    username=username_or_email, 
                    password=password
                )
            except:
                pass

            # If username auth fails, try email
            if user is None:
                try:
                    # Find user by email first
                    user_obj = User.objects.filter(email=username_or_email).first()
                    if user_obj:
                        user = authenticate(
                            self.request, 
                            username=user_obj.username, 
                            password=password
                        )
                except:
                    pass

            # If both fail, raise validation error
            if user is None:
                raise forms.ValidationError(
                    'Invalid login credentials. Please check your username/email and password.',
                    code='invalid_login'
                )
            
            # Set the authenticated user
            self.user_cache = user

        return self.cleaned_data
    
    

class QuoteRequestForm(forms.ModelForm):  # Changé de QuoteClientRequestForm à QuoteRequestForm
    class Meta:
        model = TranslationRequest
        fields = [
            'translation_type',
            'title', 
            'description',
            'source_language',
            'target_language',
            'deadline',
            'duration_minutes',
            'address',
            'original_document'
        ]
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make base fields required
        self.fields['title'].required = True
        self.fields['description'].required = True
        self.fields['source_language'].required = True
        self.fields['target_language'].required = True
        self.fields['deadline'].required = True
        self.fields['translation_type'].required = True

        # Make optional fields not required by default
        self.fields['duration_minutes'].required = False
        self.fields['address'].required = False
        self.fields['original_document'].required = False

        # Customize file validators
        self.fields['original_document'].validators.append(
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'txt', 'rtf']
            )
        )

    def get_required_fields(self):
        """Returns required fields based on translation type"""
        translation_type = self.data.get('translation_type') if self.data else None
        
        base_fields = [
            'title',
            'description',
            'source_language',
            'target_language',
            'deadline'
        ]
        
        if translation_type == 'DOCUMENT':
            return base_fields + ['original_document']
        elif translation_type in ['REMOTE_PHONE', 'REMOTE_MEETING']:
            return base_fields + ['duration_minutes']
        elif translation_type == 'LIVE_ON_SITE':
            return base_fields + ['duration_minutes', 'address']
        
        return base_fields

    def clean(self):
        cleaned_data = super().clean()
        translation_type = cleaned_data.get('translation_type')
        original_document = cleaned_data.get('original_document')
        duration_minutes = cleaned_data.get('duration_minutes')
        address = cleaned_data.get('address')

        if translation_type == 'DOCUMENT':
            if not original_document:
                self.add_error('original_document', 
                             'A document is required for this type of translation')
        elif translation_type in ['REMOTE_PHONE', 'REMOTE_MEETING']:
            if not duration_minutes:
                self.add_error('duration_minutes', 
                             'Duration is required for this type of service')
        elif translation_type == 'LIVE_ON_SITE':
            if not address:
                self.add_error('address', 
                             'Address is required for this type of service')
            if not duration_minutes:
                self.add_error('duration_minutes', 
                             'Duration is required for this type of service')

        return cleaned_data

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        translation_type = self.cleaned_data.get('translation_type')
        
        if translation_type in ['REMOTE_PHONE', 'REMOTE_MEETING', 'LIVE_ON_SITE']:
            return deadline
        return deadline