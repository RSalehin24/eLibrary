import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.apps import apps
from django.db import models

for model in apps.get_models():
    # Only check models in our apps
    if not model._meta.app_label in ['catalog', 'ingestion', 'processing', 'common', 'accounts']:
        continue
    
    # Find fields to check
    fields_to_check = []
    for f in model._meta.fields:
        if isinstance(f, (models.CharField, models.TextField, models.IntegerField, models.FloatField, models.DecimalField)):
            fields_to_check.append(f.name)
            
    if not fields_to_check:
        continue
        
    # Query model
    try:
        for obj in model.objects.all():
            for field in fields_to_check:
                val = getattr(obj, field)
                if val == 89 or val == "89" or (isinstance(val, str) and "89" in val):
                    print(f"Match found in model {model.__name__} (ID: {obj.pk}): field {field} = {val}")
    except Exception as e:
        # Ignore models that can't be queried
        pass
