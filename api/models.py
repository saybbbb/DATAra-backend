from django.db import models
from django.contrib.auth.models import User

class DataUsageRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='usage_records')
    date = models.DateField()
    time_slot = models.CharField(max_length=20)       # e.g., "0:00-1:00"
    data_used_mb = models.FloatField()                 # usage in MB
    app_name = models.CharField(max_length=100, blank=True, null=True)  # e.g., "Facebook"
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'time_slot']

    def __str__(self):
        return f"{self.user.username} - {self.date} {self.time_slot}: {self.data_used_mb}MB"
