from django.db import models


class SourceRequestWindow(models.Model):
    host = models.CharField(max_length=253, primary_key=True)
    available_at = models.DateTimeField()
