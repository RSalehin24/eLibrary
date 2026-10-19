from django.db import models


class SourceRequestWindow(models.Model):
    host = models.CharField(max_length=253, primary_key=True)
    available_at = models.DateTimeField()


class SourceHostHealth(models.Model):
    host = models.CharField(max_length=253, primary_key=True)
    failure_count = models.PositiveIntegerField(default=0)
    window_started_at = models.DateTimeField(null=True)
    open_until = models.DateTimeField(null=True)
