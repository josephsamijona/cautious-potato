# urls/client.py

from django.urls import path
from ..views.client import (
    client_dashboard,
    create_quote_request,
    quote_list_view,
    translation_list_view,
    translation_detail_view,
    handle_payment_view
)

app_name = 'client'

urlpatterns = [
    path('dashboard/', client_dashboard, name='dashboard'),
    path('quotes/create/', create_quote_request, name='create_quote'),
    path('quotes/', quote_list_view, name='quote_list'),
    path('translations/', translation_list_view, name='translation_list'),
    path('translations/<int:translation_id>/', translation_detail_view, name='translation_detail'),
    path('translations/<int:translation_id>/payment/', handle_payment_view, name='handle_payment'),
]