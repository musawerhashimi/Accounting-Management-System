import os
import django
from django.apps import apps
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
# Setup Django environment
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "easyshop.settings")
# django.setup()

project_apps = [
    'core',
    'accounts',
    'catalog',
    'inventory',
    'vendors',
    'finance',
    'customers',
    'sales',
    'hr',
]

def get_field_type(field):
    if isinstance(field, models.ForeignKey):
        return f"ForeignKey → {field.related_model.__name__}"
    elif isinstance(field, models.ManyToManyField):
        return f"ManyToMany → {field.related_model.__name__}"
    elif isinstance(field, models.OneToOneField):
        return f"OneToOne → {field.related_model.__name__}"
    elif isinstance(field, GenericForeignKey):
      return f"GenericForeignKey"
    else:
        return field.get_internal_type()


def inspect_models():
    models_counter = 0
    for model in apps.get_models():
        module = model.__module__
        if module.split(".")[0] not in project_apps:
            continue
        models_counter += 1
        print(f"\n📦 {models_counter}. Model: {module}.{model.__name__}")
        print("-" * 60)
        for field in model._meta.fields:
            field_name = field.name
            if field_name in ['created_at', 'updated_at', 'deleted_at']:
                continue
            field_type = get_field_type(field)
            print(f"🔹 {field_name}: {field_type}")

if __name__ == "__main__":
    inspect_models()
