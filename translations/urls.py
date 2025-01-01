from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    # Auth URLs
    path('register/', views.register, name='register'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('profile/client/setup/', views.client_profile_setup, name='client_profile_setup'),
    path('profile/translator/setup/', views.translator_profile_setup, name='translator_profile_setup'),
    
    # Client URLs
    path('client/quote/create/', views.create_quote, name='client_create_quote'),
    path('client/quotes/', views.quote_list, name='client_quote_list'),
    path('client/quote/<int:pk>/', views.quote_detail, name='client_quote_detail'),
    path('client/quote/<int:pk>/payment-success/', views.payment_success, name='client_payment_success'),
    path('client/translations/', views.translation_list, name='client_translation_list'),
    path('client/translation/<int:pk>/', views.translation_detail, name='client_translation_detail'),
    path('client/profile/', views.client_profile, name='client_profile'),
    
    # Notifications
    path('client/notifications/', views.notification_list, name='client_notifications'),
    path('client/notification-settings/', 
         views.notification_settings, name='client_notification_settings'),
        # Translator URLs
    path('translator/dashboard/', 
         views.translator_dashboard, 
         name='translator_dashboard'),
    
    path('translator/translation/<int:pk>/', 
         views.translation_detail, 
         name='translator_translation_detail'),
    
    path('translator/translation/<int:pk>/upload/', 
         views.upload_translation, 
         name='translator_upload'),
    
    path('translator/translation/<int:pk>/download/', 
         views.download_original, 
         name='translator_download_original'),
    
    path('translator/payments/', 
         views.payment_history, 
         name='translator_payments'),
    
    path('translator/history/', 
         views.translation_history, 
         name='translator_history'),
    
        path('admin/dashboard/', 
         views.admin_dashboard, 
         name='admin_dashboard'),
    
    path('admin/translation/create/', 
         views.create_translation, 
         name='admin_create_translation'),
    
    path('admin/quotes/', 
         views.manage_quotes, 
         name='admin_manage_quotes'),
    
    path('admin/quote/<int:pk>/process/', 
         views.process_quote, 
         name='admin_process_quote'),
    
    path('admin/translations/', 
         views.translation_list, 
         name='admin_translation_list'),
    
    path('admin/translation/<int:pk>/assign/', 
         views.assign_translator, 
         name='admin_assign_translator'),
    
    path('admin/payments/', 
         views.payment_management, 
         name='admin_payments'),
    
    path('admin/reports/', 
         views.reports, 
         name='admin_reports'),

]