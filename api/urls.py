from django.urls import path
from . import views

urlpatterns = [
    path('', views.api_root, name='api-root'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('usage/', views.usage_list, name='usage-list'),
    path('usage/summary/', views.usage_summary, name='usage-summary'),
    path('profile/', views.profile_view, name='profile'),
]
