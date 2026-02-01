from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Vendor, Purchase, PurchaseItem


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    """Admin interface for Vendor model"""
    list_display = [
        'name', 'email', 'phone', 
        'balance', 'status', 'total_purchases_display',
        'created_at'
    ]
    list_filter = ['status', 'created_at', 'tenant']
    search_fields = ['name', 'email', 'phone', 'tax_id']
    readonly_fields = ['balance', 'created_at', 'updated_at', 'total_purchases_display']
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'name', 'contact_person', 'status')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email')
        }),
        ('Financial Information', {
            'fields': ('tax_id', 'balance')
        }),
        ('System Information', {
            'fields': ('created_by_user', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def total_purchases_display(self, obj):
        """Display total purchases with link"""
        count = obj.purchases.count()
        if count > 0:
            url = reverse('admin:vendors_purchase_changelist') + f'?vendor__id__exact={obj.id}'
            return format_html('<a href="{}">{} purchases</a>', url, count)
        return '0 purchases'
    
    total_purchases_display.short_description = 'Purchases'
    
    def get_queryset(self, request):
        """Filter by tenant for non-superusers"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(tenant=request.user.tenant)


class PurchaseItemInline(admin.TabularInline):
    """Inline for purchase items"""
    model = PurchaseItem
    extra = 0
    readonly_fields = ['line_total', 'remaining_quantity', 'is_fully_received']
    fields = [
        'variant', 'batch', 'quantity', 'unit_cost', 'line_total',
        'received_quantity', 'remaining_quantity', 'is_fully_received'
    ]
    
    def remaining_quantity(self, obj):
        if obj.pk:
            return obj.remaining_quantity
        return '-'
    
    def is_fully_received(self, obj):
        if obj.pk:
            return '✓' if obj.is_fully_received else '✗'
        return '-'
    
    remaining_quantity.short_description = 'Remaining'
    is_fully_received.short_description = 'Received'


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    """Admin interface for Purchase model"""
    list_display = [
        'purchase_number', 'vendor', 'location', 'purchase_date',
        'total_amount', 'currency', 'status', 'progress_display'
    ]
    list_filter = ['status', 'purchase_date', 'vendor', 'location', 'tenant']
    search_fields = ['purchase_number', 'vendor__name', 'notes']
    readonly_fields = [
        'purchase_number', 'subtotal', 'total_amount', 'created_at', 
        'updated_at', 'progress_display'
    ]
    inlines = [PurchaseItemInline]
    date_hierarchy = 'purchase_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'purchase_number', 'vendor', 'location', 'status')
        }),
        ('Dates', {
            'fields': ('purchase_date', 'delivery_date')
        }),
        ('Financial Information', {
            'fields': ('subtotal', 'tax_amount', 'total_amount', 'currency')
        }),
        ('Additional Information', {
            'fields': ('notes', 'progress_display')
        }),
        ('System Information', {
            'fields': ('created_by_user', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def progress_display(self, obj):
        """Display receiving progress"""
        if obj.pk:
            total_qty = obj.total_quantity
            received_qty = obj.received_quantity
            
            if total_qty == 0:
                return 'No items'
            
            percentage = (received_qty / total_qty) * 100
            color = 'green' if percentage == 100 else 'orange' if percentage > 0 else 'gray'
            
            return format_html(
                '<span style="color: {};">{}% ({}/{})</span>',
                color, percentage, received_qty, total_qty
            )
        return '-'
    
    progress_display.short_description = 'Progress'
    
    def get_queryset(self, request):
        """Filter by tenant for non-superusers"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(tenant=request.user.tenant)
    
    def save_model(self, request, obj, form, change):
        """Set created_by_user for new purchases"""
        if not change:
            obj.created_by_user = request.user
        super().save_model(request, obj, form, change)


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    """Admin interface for Purchase Item model"""
    list_display = [
        'purchase', 'variant_display', 'quantity', 'unit_cost',
        'line_total', 'received_quantity', 'progress_display'
    ]
    list_filter = ['purchase__status', 'purchase__purchase_date', 'variant__product']
    search_fields = [
        'purchase__purchase_number', 'variant__product__name',
        'variant__sku', 'batch__batch_number'
    ]
    readonly_fields = ['line_total', 'remaining_quantity', 'is_fully_received']
    
    fieldsets = (
        ('Purchase Information', {
            'fields': ('purchase',)
        }),
        ('Product Information', {
            'fields': ('variant', 'batch')
        }),
        ('Quantity Information', {
            'fields': ('quantity', 'received_quantity', 'remaining_quantity')
        }),
        ('Pricing Information', {
            'fields': ('unit_cost', 'line_total')
        }),
        ('Status', {
            'fields': ('is_fully_received',)
        })
    )
    
    def variant_display(self, obj):
        """Display variant with product name"""
        return f"{obj.variant.product.name} - {obj.variant.variant_name}"
    
    def progress_display(self, obj):
        """Display receiving progress"""
        if obj.quantity == 0:
            return 'No quantity'
        
        percentage = (obj.received_quantity / obj.quantity) * 100
        color = 'green' if percentage == 100 else 'orange' if percentage > 0 else 'gray'
        
        return format_html(
            '<span style="color: {};">{}%</span>',
            color, percentage
        )
    
    variant_display.short_description = 'Product Variant'
    progress_display.short_description = 'Progress'
    
    def get_queryset(self, request):
        """Filter by tenant for non-superusers"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(purchase__tenant=request.user.tenant)