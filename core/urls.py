# core/urls.py
from django.urls import path
from .views_reports import AdvancedReportsView
from .views import TestExportView

urlpatterns = [
    path('reports/advanced/', AdvancedReportsView.as_view(), name='core-advanced-reports'),
    path('reports/test/', TestExportView.as_view(), name='test-export'),
]
