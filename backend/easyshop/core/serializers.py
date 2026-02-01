from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from django.core.validators import MinValueValidator

from core.threads import get_current_tenant
from .models import (
    Tenant, TenantSettings, TenantSubscription, Currency, CurrencyRate, 
    Unit, Address, Permission, ActivityLog
)


class TenantSerializer(serializers.ModelSerializer):
    is_trial_expired = serializers.ReadOnlyField()
    usage_stats = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'domain', 'contact_email', 'contact_phone', 
            'business_type', 'status', 'trial_ends_at', 'subscription_plan',
            'max_users', 'max_products', 'max_locations', 'max_storage_mb',
            'is_trial_expired', 'usage_stats', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_trial_expired']

    def get_usage_stats(self, obj):
        return {
            'users_count': obj.users.filter(is_active=True).count(),
            'products_count': obj.products.filter(deleted_at__isnull=True).count(),
            'locations_count': obj.locations.filter(deleted_at__isnull=True).count(),
        }

    def validate_domain(self, value):
        if value:
            # Check if domain is already taken by another tenant
            existing = Tenant.objects.filter(domain=value).exclude(id=self.instance.id if self.instance else None)
            if existing.exists():
                raise serializers.ValidationError("This domain is already taken.")
        return value


class TenantCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for tenant creation"""
    
    class Meta:
        model = Tenant
        fields = [
            'name', 'contact_email', 'contact_phone', 'business_type', 
            'subscription_plan'
        ]

    def create(self, validated_data):
        # Set trial period
        validated_data['trial_ends_at'] = timezone.now() + timezone.timedelta(days=30)
        validated_data['status'] = 'trial'
        return super().create(validated_data)


class ShopSettingsSerializer(serializers.Serializer):
    shop_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)

    def update(self, instance, validated_data):
        tenant = self.context['tenant']
        for key, value in validated_data.items():
            if value:
                TenantSettings.set_setting(
                    tenant=tenant,
                    key=key,
                    value=value,
                    setting_type='string',
                    category='general',
                    description=f"{key.replace('_', ' ').capitalize()} of the shop"
                )
        return validated_data

    def create(self, validated_data):
        return self.update(None, validated_data)

        
class EmailSettingsSerializer(serializers.Serializer):
    smtp_host = serializers.CharField(required=False, allow_blank=True)
    smtp_port = serializers.CharField(required=False, allow_blank=True)  # Accept as string first
    smtp_username = serializers.CharField(required=False, allow_blank=True)
    smtp_password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    from_email = serializers.EmailField(required=False, allow_blank=True)

    def validate_smtp_port(self, value):
        # Skip empty values
        if value in [None, ""]:
            return None
        try:
            return int(value)
        except ValueError:
            raise serializers.ValidationError("smtp_port must be an integer.")

    def update(self, instance, validated_data):
        tenant = self.context['tenant']
        for key, value in validated_data.items():
            if value not in [None, ""]:
                setting_type = 'integer' if key == 'smtp_port' else 'string'
                TenantSettings.set_setting(
                    tenant=tenant,
                    key=key,
                    value=value,
                    setting_type=setting_type,
                    category='notifications',
                    description=f"{key.replace('_', ' ').capitalize()} for email configuration"
                )
        return validated_data

    def create(self, validated_data):
        return self.update(None, validated_data)


class CurrencySerializer(serializers.ModelSerializer):
    
    exchange_rate = serializers.DecimalField(
        max_digits=15,
        decimal_places=6,
        # write_only=True,
        validators=[MinValueValidator(0.000001)]
    )

    class Meta:
        model = Currency
        fields = [
            'id', 'name', 'code', 'symbol', 'decimal_places', 
            'is_base_currency',
            'exchange_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'exchange_rate', 'is_base_currency']

    def validate(self, data):
        # Validate currency code format
        code = data.get('code', '').upper()
        if len(code) != 3:
            raise serializers.ValidationError("Currency code must be exactly 3 characters")
        data['code'] = code
        return data

    @transaction.atomic
    def create(self, validated_data):
        tenant = get_current_tenant()
        exchange_rate = validated_data.pop('exchange_rate')
        currency = Currency.objects.create(**validated_data)
        CurrencyRate.objects.create(
            tenant=tenant,
            currency=currency,
            rate=exchange_rate
        )
        return currency
    
    @transaction.atomic
    def update(self, instance, validated_data):
        # fields = ["name", "code", "symbol", "decimal_places"]
        instance.name = validated_data.get('name', instance.name)
        instance.code = validated_data.get('code', instance.code)
        instance.symbol = validated_data.get('symbol', instance.symbol)
        instance.decimal_places = validated_data.get('decimal_places', instance.decimal_places)
        instance.save()
        
        exchange_rate = validated_data.get("exchange_rate", None)
        if exchange_rate:
            CurrencyRate.objects.create(
                tenant=self.context.get("request").tenant,
                currency=instance,
                rate=exchange_rate
            )
        return instance
    

class TenantSubscriptionSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    is_active = serializers.ReadOnlyField()
    days_until_renewal = serializers.SerializerMethodField()

    class Meta:
        model = TenantSubscription
        fields = [
            'id', 'plan_name', 'price', 'currency', 'currency_code',
            'billing_cycle', 'current_period_start', 'current_period_end',
            'status', 'payment_method', 'next_billing_date', 'is_active',
            'days_until_renewal', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_active', 'days_until_renewal']

    def get_days_until_renewal(self, obj):
        if obj.next_billing_date:
            delta = obj.next_billing_date.date() - timezone.now().date()
            return delta.days
        return None


class UnitSerializer(serializers.ModelSerializer):
    base_unit_name = serializers.CharField(source='base_unit.name', read_only=True)
    derived_units_count = serializers.SerializerMethodField()

    class Meta:
        model = Unit
        fields = [
            'id', 'name', 'abbreviation', 'unit_type', 'base_unit',
            'base_unit_name', 'conversion_factor', 'is_base_unit',
            'derived_units_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'derived_units_count']

    def get_derived_units_count(self, obj):
        return obj.derived_units.count()

    def validate(self, data):
        is_base_unit = data.get('is_base_unit', True)
        base_unit = data.get('base_unit')
        
        if is_base_unit and base_unit:
            raise serializers.ValidationError("Base unit cannot have a parent base unit")
        if not is_base_unit and not base_unit:
            raise serializers.ValidationError("Non-base unit must have a base unit")
        
        return data


class AddressSerializer(serializers.ModelSerializer):
    full_address = serializers.SerializerMethodField()

    class Meta:
        model = Address
        fields = [
            'id', 'addressable_type', 'addressable_id', 'address_type',
            'address_line_1', 'address_line_2', 'city', 'state',
            'postal_code', 'country', 'is_default', 'full_address',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'full_address']

    def get_full_address(self, obj):
        parts = [obj.address_line_1]
        if obj.address_line_2:
            parts.append(obj.address_line_2)
        parts.extend([obj.city, obj.state, obj.postal_code, obj.country])
        return ', '.join(parts)


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'user', 'user_name', 'user_username', 'action',
            'table_name', 'record_id', 'old_values', 'new_values',
            'ip_address', 'user_agent', 'session_id', 'timestamp', 'created_at'
        ]
        read_only_fields = ['created_at', 'user_name', 'user_username']


class ActivityLogCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating activity logs"""
    
    class Meta:
        model = ActivityLog
        fields = [
            'action', 'table_name', 'record_id', 'old_values', 
            'new_values', 'ip_address', 'user_agent', 'session_id'
        ]