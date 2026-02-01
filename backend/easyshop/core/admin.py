from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Tenant, TenantSettings, TenantSubscription, Currency, CurrencyRate,
    Unit, Address, Permission, ActivityLog
)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'domain', 'business_type', 'status', 'subscription_plan',
        'contact_email', 'trial_status', 'created_at'
    ]
    list_filter = ['business_type', 'status', 'subscription_plan', 'created_at']
    search_fields = ['name', 'domain', 'contact_email']
    readonly_fields = ['created_at', 'updated_at', 'trial_status', 'usage_summary']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'domain', 'business_type', 'status')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone')
        }),
        ('Subscription & Limits', {
            'fields': (
                'subscription_plan', 'trial_ends_at', 'max_users', 
                'max_products', 'max_locations', 'max_storage_mb'
            )
        }),
        ('Status & Analytics', {
            'fields': ('trial_status', 'usage_summary', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def trial_status(self, obj):
        if obj.status == 'trial':
            if obj.is_trial_expired:
                return format_html('<span style="color: red;">Expired</span>')
            else:
                days_left = (obj.trial_ends_at - timezone.now()).days if obj.trial_ends_at else 360
                return format_html(f'<span style="color: orange;">{days_left} days left</span>')
        return format_html('<span style="color: green;">Not in trial</span>')
    trial_status.short_description = 'Trial Status'
    
    def usage_summary(self, obj):
        try:
            users_count = obj.users.filter(is_active=True).count()
            products_count = obj.products.filter(deleted_at__isnull=True).count()
            locations_count = obj.locations.filter(deleted_at__isnull=True).count()
            
            return format_html(
                'Users: {}/{} | Products: {}/{} | Locations: {}/{}',
                users_count, obj.max_users,
                products_count, obj.max_products,
                locations_count, obj.max_locations
            )
        except:
            return 'N/A'
    usage_summary.short_description = 'Usage Summary'

    actions = ['activate_tenants', 'suspend_tenants']
    
    def activate_tenants(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} tenants activated.')
    activate_tenants.short_description = 'Activate selected tenants'
    
    def suspend_tenants(self, request, queryset):
        updated = queryset.update(status='suspended')
        self.message_user(request, f'{updated} tenants suspended.')
    suspend_tenants.short_description = 'Suspend selected tenants'


class TenantSettingsInline(admin.TabularInline):
    model = TenantSettings
    extra = 0
    fields = ['setting_key', 'setting_value', 'setting_type', 'description']


@admin.register(TenantSettings)
class TenantSettingsAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'setting_key', 'setting_type', 'created_at']
    list_filter = ['setting_type', 'tenant', 'created_at']
    search_fields = ['tenant__name', 'setting_key', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tenant')


@admin.register(TenantSubscription)
class TenantSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'tenant', 'plan_name', 'price', 'currency', 'billing_cycle', 
        'status', 'next_billing_date', 'subscription_status'
    ]
    list_filter = ['plan_name', 'billing_cycle', 'status', 'created_at']
    search_fields = ['tenant__name', 'plan_name']
    readonly_fields = ['created_at', 'updated_at', 'subscription_status']
    
    def subscription_status(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">Active</span>')
        else:
            return format_html('<span style="color: red;">Inactive</span>')
    subscription_status.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tenant', 'currency')


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'symbol', 'tenant', 'is_base_currency', 'is_active', 'current_rate']
    list_filter = ['is_base_currency', 'is_active', 'tenant', 'created_at']
    search_fields = ['name', 'code', 'tenant__name']
    readonly_fields = ['created_at', 'updated_at', 'current_rate']
    
    def current_rate(self, obj):
        latest_rate = obj.rates.order_by('-effective_date').first()
        return latest_rate.rate if latest_rate else 'No rate set'
    current_rate.short_description = 'Current Rate'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tenant').prefetch_related('rates')


@admin.register(CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ['currency', 'rate', 'effective_date', 'tenant', 'created_at']
    list_filter = ['currency', 'effective_date', 'tenant', 'created_at']
    search_fields = ['currency__name', 'currency__code', 'tenant__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'effective_date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('currency', 'tenant')


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'abbreviation', 'unit_type', 'tenant', 'is_base_unit', 'base_unit', 'conversion_factor']
    list_filter = ['unit_type', 'is_base_unit', 'tenant', 'created_at']
    search_fields = ['name', 'abbreviation', 'tenant__name']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tenant', 'base_unit')


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = [
        'addressable_info', 'address_type', 'city', 'state', 
        'country', 'is_default', 'tenant'
    ]
    list_filter = ['address_type', 'country', 'state', 'is_default', 'tenant']
    search_fields = ['address_line_1', 'city', 'state', 'country', 'tenant__name']
    readonly_fields = ['created_at', 'updated_at']
    
    def addressable_info(self, obj):
        return f"{obj.addressable_type} #{obj.addressable_id}"
    addressable_info.short_description = 'Related To'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tenant')


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['action', 'module', 'description', 'created_at']
    list_filter = ['module', 'created_at']
    search_fields = ['action', 'description']
    readonly_fields = ['created_at']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'action', 'table_name', 'record_id', 
        'tenant', 'ip_address', 'timestamp'
    ]
    list_filter = ['action', 'table_name', 'tenant', 'timestamp']
    search_fields = ['user__username', 'table_name', 'tenant__name', 'ip_address']
    readonly_fields = [
        'user', 'action', 'table_name', 'record_id', 'old_values', 
        'new_values', 'ip_address', 'user_agent', 'session_id', 
        'timestamp', 'created_at', 'tenant'
    ]
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'tenant')


# Customize admin site
admin.site.site_header = 'Business Management System Admin'
admin.site.site_title = 'BMS Admin'
admin.site.index_title = 'Welcome to Business Management System Administration'