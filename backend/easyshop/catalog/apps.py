from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalog'
    verbose_name = 'Product Catalog'
    
    def ready(self):
        # Import signals if you have any
        # import catalog.signals
        pass