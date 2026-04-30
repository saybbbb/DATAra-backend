from django.urls import path
from . import views

urlpatterns = [
    path('', views.api_root, name='api-root'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
]
