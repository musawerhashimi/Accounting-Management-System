from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from core.image_path import settings_image_upload_path
from .base_models import BaseModel, TenantBaseModel


class Tenant(BaseModel):
    BUSINESS_TYPE_CHOICES = [
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
        ('manufacturing', 'Manufacturing'),
        ('service', 'Service'),
        ('restaurant', 'Restaurant'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('trial', 'Trial'),
    ]
    
    SUBSCRIPTION_PLANS = [
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    ]

    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True, null=True, blank=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True)
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPE_CHOICES, default='retail')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    subscription_plan = models.CharField(max_length=20, choices=SUBSCRIPTION_PLANS, default='basic')
    max_users = models.PositiveIntegerField(default=5)
    max_products = models.PositiveIntegerField(default=1000)
    max_locations = models.PositiveIntegerField(default=2)
    max_storage_mb = models.PositiveIntegerField(default=1024)  # 1GB default

    class Meta:
        db_table = 'tenants'
        indexes = [
            models.Index(fields=['domain']),
            models.Index(fields=['status']),
            models.Index(fields=['contact_email']),
        ]

    def __str__(self):
        return self.name

    @property
    def is_trial_expired(self):
        return self.trial_ends_at and timezone.now() > self.trial_ends_at

    def is_within_limits(self, resource_type):
        """Check if tenant is within resource limits"""
        if resource_type == 'users':
            return self.users.filter(is_active=True).count() < self.max_users
        elif resource_type == 'products':
            return self.products.filter(deleted_at__isnull=True).count() < self.max_products
        elif resource_type == 'locations':
            return self.locations.filter(deleted_at__isnull=True).count() < self.max_locations
        return True


class TenantSettings(TenantBaseModel):
    SETTING_TYPES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
        ('image', 'Image')
    ]
    
    CATEGORIES = [
        ('general', 'General'),
        ('security', 'Security'),
        ('notifications', 'Notifications'),
        ('integration', 'Integration'),
        ('billing', 'Billing'),
    ]

    setting_key = models.CharField(max_length=100)
    setting_value = models.TextField(blank=True, null=True)
    setting_image = models.ImageField(
        upload_to=settings_image_upload_path,
        blank=True,
        null=True
    )
    
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES, default='string')
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='general')

    class Meta:
        db_table = 'tenant_settings'
        unique_together = ['tenant', 'setting_key']
        indexes = [
            models.Index(fields=['tenant', 'setting_key']),
        ]

    def __str__(self):
        return f"{self.tenant.name} - {self.setting_key}"

    def get_typed_value(self):
        """Return the setting value in its proper type"""
        if self.setting_type == 'integer':
            return int(self.setting_value)
        elif self.setting_type == 'float':
            return float(self.setting_value)
        elif self.setting_type == 'boolean':
            return self.setting_value.lower() in ['true', '1', 'yes', 'on']
        elif self.setting_type == 'json':
            import json
            return json.loads(self.setting_value)
        elif self.setting_type == 'image':
            return self.setting_image.url if self.setting_image else None
        return self.setting_value

    @classmethod
    def set_setting(cls, tenant, key, value, setting_type='string', category='general', description='', image=None):
        """Set or update a tenant setting"""
        setting, created = cls.objects.get_or_create(
            tenant=tenant,
            setting_key=key,
            defaults={
                'setting_value': value,
                'setting_type': setting_type,
                'category': category,
                'description': description,
                'setting_image': image,
            }
        )
        if not created:
            setting.setting_value = value
            setting.setting_type = setting_type
            setting.category = category
            setting.description = description
            if image:
                setting.setting_image = image
            setting.save()
        return setting


class Currency(TenantBaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=3)  # ISO 4217
    symbol = models.CharField(max_length=10, null=True, blank=True)
    decimal_places = models.PositiveSmallIntegerField(default=2, validators=[MaxValueValidator(4)])
    is_base_currency = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'currencies'
        verbose_name_plural = 'currencies'
        unique_together = ['tenant', 'code']
        indexes = [
            models.Index(fields=['tenant', 'is_base_currency']),
            models.Index(fields=['tenant', 'is_active']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if self.is_base_currency:
            # Ensure only one base currency per tenant
            Currency.objects.filter(tenant=self.tenant, is_base_currency=True).update(is_base_currency=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_base_currency(cls):
        base_currency_id = TenantSettings.objects.get(key="base_currency_id").get_typed_value()
        return cls.objects.get(id=base_currency_id)

    @property
    def exchange_rate(self):
        latest_rate = self.rates.order_by('-effective_date').first()
        return latest_rate.rate if latest_rate else None

    def convert_to(self, amount, to_currency_id):
        if self.id == to_currency_id:
            return amount
        try:
            toCurrency = Currency.objects.get(id=to_currency_id)
        except Currency.DoesNotExist:
            return amount
        
        from_rate = self.exchange_rate
        to_rate = toCurrency.exchange_rate
        if from_rate is None or to_rate is None:
            return amount
        # Convert amount to base currency, then to target currency
        base_amount = amount / from_rate
        converted_amount = base_amount * to_rate
        return converted_amount

    def convert_from(self, amount, from_currency_id):
        if self.id == from_currency_id:
            return amount
        try:
            fromCurrency = Currency.objects.get(id=from_currency_id)
        except Currency.DoesNotExist:
            return amount
        
        from_rate = fromCurrency.exchange_rate
        to_rate = self.exchange_rate
        if from_rate is None or to_rate is None:
            return amount
        
        base_amount = amount / from_rate
        converted_amount = base_amount * to_rate
        return converted_amount

    @classmethod
    def convert_to_base_currency(cls, amount, from_currency_id):
        base_currency = cls.get_base_currency()

        if base_currency.id == from_currency_id:
            return amount
        try:
            from_currency = Currency.objects.get(id=from_currency_id)
        except Currency.DoesNotExist:
            return amount
        
        from_rate = from_currency.exchange_rate        
        base_amount = amount / from_rate
        return base_amount
        
    @classmethod
    def get_base_currency(cls):
        base_currency_id = TenantSettings.objects.get(setting_key="base_currency_id").get_typed_value()
        return cls.objects.get(id=base_currency_id)


class CurrencyRate(TenantBaseModel):
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='rates')
    rate = models.DecimalField(max_digits=15, decimal_places=6, validators=[MinValueValidator(0.000001)])
    effective_date = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'currency_rates'
        indexes = [
            models.Index(fields=['tenant', 'currency', 'effective_date']),
        ]

    def __str__(self):
        return f"{self.currency.code} - {self.rate} ({self.effective_date.date()})"


class TenantSubscription(TenantBaseModel):
    BILLING_CYCLES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('incomplete', 'Incomplete'),
        ('trialing', 'Trialing'),
    ]
    
    PAYMENT_METHODS = [
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
        ('invoice', 'Invoice'),
        ('cash', 'Cash'),
    ]

    plan_name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLES, default='monthly')
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='credit_card')
    next_billing_date = models.DateTimeField()

    class Meta:
        db_table = 'tenant_subscriptions'
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['next_billing_date']),
        ]

    def __str__(self):
        return f"{self.tenant.name} - {self.plan_name}"

    @property
    def is_active(self):
        return self.status == 'active' and timezone.now() <= self.current_period_end


class Unit(TenantBaseModel):
    UNIT_TYPES = [
      ('weight', 'Weight'),
      ('volume', 'Volume'),
      ('length', 'Length'),
      ('area', 'Area'),
      ('count', 'Count'),
      ('time', 'Time')
    ]

    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=20)
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPES, default='weight')
    base_unit = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='derived_units')
    conversion_factor = models.DecimalField(max_digits=15, decimal_places=6, default=1.0)
    is_base_unit = models.BooleanField(default=False)

    class Meta:
        db_table = 'units'
        unique_together = ['tenant', 'name']
        indexes = [
            models.Index(fields=['tenant', 'unit_type']),
            models.Index(fields=['tenant', 'is_base_unit']),
        ]

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.is_base_unit and self.base_unit:
            raise ValidationError("Base unit cannot have a parent base unit")
        if not self.is_base_unit and not self.base_unit:
            raise ValidationError("Non-base unit must have a base unit")

        # Check for circular references
        current = self.base_unit
        while current and current.base_unit:
            if current.base_unit == self:
                raise ValidationError("Circular reference detected in unit hierarchy")
            current = current.base_unit


class Address(TenantBaseModel):
    ADDRESS_TYPES = [
        ('billing', 'Billing'),
        ('shipping', 'Shipping'),
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
    ]
    addressable_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    addressable_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('addressable_type', 'addressable_id')
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPES, default='primary')
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(blank=True, max_length=100, null=True)
    postal_code = models.CharField(blank=True, max_length=20, null=True)
    country = models.CharField(blank=True, max_length=100, null=True)
    is_default = models.BooleanField(default=True)
    created_by_user = models.ForeignKey('accounts.User', blank=True, null=True, on_delete=models.SET_NULL, related_name='created_addresses')
    class Meta:
        db_table = 'addresses'
        indexes = [
            models.Index(fields=['tenant', 'addressable_type', 'addressable_id']),
            models.Index(fields=['tenant', 'address_type']),
        ]

    def __str__(self):
        return f"{self.address_line_1}, {self.city}, {self.state}"


class Permission(models.Model):
    MODULES = [
        ('users', 'Users'),
        ('inventory', 'Inventory'),
        ('sales', 'Sales'),
        ('purchases', 'Purchases'),
        ('customers', 'Customers'),
        ('finance', 'Finance'),
        ('reports', 'Reports'),
        ('settings', 'Settings'),
        # newly added
        ("product_details", "Product Details"),
        ("expense", "Expense"),
        ("stock_and_warehouse", "Stock and Warehouse"),
        ("currency", "Currency"),
        ("units", "Units"),
        ("discount", "Discount"),

        # ('vendors', 'Vendors'),
        # ("members", "Members"),
        # ("employees", "Employees"),

    ]

    action = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    module = models.CharField(max_length=50, choices=MODULES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'permissions'
        unique_together = ['module', 'action']
        indexes = [
            models.Index(fields=['module']),
        ]

    @property
    def codename(self):
        return f"{self.module}.{self.action}"
    
    def __str__(self):
        return self.codename


class ActivityLog(TenantBaseModel):
    ACTIONS = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=20, choices=ACTIONS)
    table_name = models.CharField(max_length=100, blank=True)
    record_id = models.PositiveIntegerField(null=True, blank=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=40, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'activity_logs'
        indexes = [
            models.Index(fields=['tenant', 'user', 'timestamp']),
            models.Index(fields=['tenant', 'action', 'timestamp']),
            models.Index(fields=['tenant', 'table_name', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"
    
    