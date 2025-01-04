# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/verify/', views.PasswordResetVerifyView.as_view(), name='password_reset_verify'),
    path('profile-setup/', views.profile_setup_view, name='profile_setup'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('quote/create/', views.CreateClientQuoteRequestView.as_view(), name='create_quote'),
    path('password-reset/', views.password_reset_request_view, name='password_reset_request'),
    path('password-reset-confirm/', views.password_reset_confirm_view, name='password_reset_confirm'),
        # URL pour la liste des devis
    path('quotes/', views.QuoteListView.as_view(), name='quote_list'),

    # URL pour les détails d'un devis
    path('quotes/<int:id>/', views.QuoteDetailView.as_view(), name='quote_detail'),

    # URL pour le paiement d'un devis
    #path('quotes/<int:id>/pay/', views.PaymentView, name='payment'),

    # URL pour indiquer qu'un devis a été payé
    #path('quotes/<int:id>/paid/', views.QuotePaidView, name='quote_paid'),

    # URL pour générer et télécharger la facture
    path('quotes/<int:id>/invoice/', views.generate_and_send_invoice, name='generate_invoice'),
    # Ajoutez d'autres URLs ici
]
