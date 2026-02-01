# vendors/apps.py

from django.apps import AppConfig


class VendorsConfig(AppConfig):
    """Vendors app configuration"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vendors'
    verbose_name = 'Vendor Management'
    
    def ready(self):
        """Import signals when the app is ready"""
       