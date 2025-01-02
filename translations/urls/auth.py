# urls/auth.py (mettre à jour avec les nouvelles URLs)

from django.urls import path
from django.contrib.auth import views as auth_views
from ..views.auth import (
    register_view, verify_otp_view, resend_otp_view,
    client_profile_setup, translator_profile_setup,
    login_view, logout_view, CustomPasswordResetView,
    CustomPasswordResetConfirmView
)

app_name = 'auth'

urlpatterns = [
    # Existing URLs
    path('register/', register_view, name='register'),
    path('verify-otp/', verify_otp_view, name='verify_otp'),
    path('resend-otp/', resend_otp_view, name='resend_otp'),
    path('profile/setup/client/', client_profile_setup, name='client_profile_setup'),
    path('profile/setup/translator/', translator_profile_setup, name='translator_profile_setup'),
    
    # New authentication URLs
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Password reset URLs
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', 
        auth_views.PasswordResetDoneView.as_view(
            template_name='auth/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path('password-reset/confirm/<uidb64>/<token>/',
        CustomPasswordResetConfirmView.as_view(),
        name='password_reset_confirm'
    ),
    path('password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='auth/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
    path('profile/update/', profile_update_view, name='profile_update'),
]