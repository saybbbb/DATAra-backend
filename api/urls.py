from django.urls import path
from . import views
from . import sync_views

urlpatterns = [
    path('', views.api_root, name='api-root'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('usage/', views.usage_list, name='usage-list'),
    path('usage/summary/', views.usage_summary, name='usage-summary'),
    path('profile/', views.profile_view, name='profile'),
    path('ml/metrics/', views.ml_metrics_view, name='ml-metrics'),
    path('sync/status/', sync_views.local_stats_status, name='sync-status'),
    path('sync/local-stats/', sync_views.record_local_stats, name='sync-local-stats'),
    path('sync/upload-global/', sync_views.upload_to_global, name='sync-upload-global'),
    path('sync/download-local/', sync_views.download_local_data, name='sync-download-local'),
    path('sync/generate-mock/', sync_views.generate_mock_stats, name='sync-generate-mock'),
    path('sync/global-averages/', sync_views.global_averages, name='sync-global-averages'),
]
