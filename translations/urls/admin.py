# urls/admin.py

from django.urls import path
from ..views.admin import (
    admin_dashboard,
    manage_users_view,
    manage_translations_view,
    process_quote_view,
    assign_translator_view,
    payment_management_view,
    reports_view
)

app_name = 'admin'

urlpatterns = [
    path('dashboard/', admin_dashboard, name='dashboard'),
    path('users/', manage_users_view, name='manage_users'),
    path('translations/', manage_translations_view, name='manage_translations'),
    path('quotes/<int:quote_id>/process/', process_quote_view, name='process_quote'),
    path('translations/<int:translation_id>/assign/', assign_translator_view, name='assign_translator'),
    path('payments/', payment_management_view, name='payment_management'),
    path('reports/', reports_view, name='reports'),
]