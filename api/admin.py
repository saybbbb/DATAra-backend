from django.contrib import admin
from .models import DataUsageRecord, UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'provider']

@admin.register(DataUsageRecord)
class DataUsageRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'time_slot', 'data_used_mb', 'app_name']
    list_filter = ['date', 'app_name']
