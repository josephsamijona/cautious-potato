# urls/translator.py

from django.urls import path
from ..views.translator import (
    translator_dashboard,
    translation_list_view,
    translation_detail_view,
    accept_translation_view,
    reject_translation_view,
    complete_translation_view,
    payment_history_view
)

app_name = 'translator'

urlpatterns = [
    path('dashboard/', translator_dashboard, name='dashboard'),
    path('translations/', translation_list_view, name='translation_list'),
    path('translations/<int:translation_id>/', translation_detail_view, name='translation_detail'),
    path('translations/<int:translation_id>/accept/', accept_translation_view, name='accept_translation'),
    path('translations/<int:translation_id>/reject/', reject_translation_view, name='reject_translation'),
    path('translations/<int:translation_id>/complete/', complete_translation_view, name='complete_translation'),
    path('payments/', payment_history_view, name='payment_history'),
]