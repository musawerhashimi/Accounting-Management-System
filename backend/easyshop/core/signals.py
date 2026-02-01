from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Address




default_settings = [
    {
        'setting_key': 'company_name',
        'setting_value': 'My Business',
        'setting_type': 'string',
        'category': 'general',
        'description': 'Company name displayed in the system'
    },
    {
        'setting_key': 'base_currency_id',
        'setting_value': '1',
        'setting_type': 'integer',
        'category': 'finance',
        'description': 'Base currency for financial calculations'
    },
    {
        'setting_key': 'low_stock_threshold',
        'setting_value': '10',
        'setting_type': 'integer',
        'category': 'inventory',
        'description': 'Default low stock threshold for products'
    },
    {
        'setting_key': 'tax_rate',
        'setting_value': '0.00',
        'setting_type': 'decimal',
        'category': 'finance',
        'description': 'Default tax rate percentage'
    },
    {
        'setting_key': 'enable_multi_location',
        'setting_value': 'false',
        'setting_type': 'boolean',
        'category': 'inventory',
        'description': 'Enable multi-location inventory management'
    }
]


@receiver(pre_save, sender=Address)
def ensure_single_default_address(sender, instance, **kwargs):
    """Ensure only one default address per entity per type"""
    if instance.is_default:
        # Find other default addresses for the same entity and type
        Address.objects.filter(
            addressable_type=instance.addressable_type,
            addressable_id=instance.addressable_id,
            address_type=instance.address_type,
            is_default=True
        ).exclude(pk=instance.pk).update(is_default=False)

