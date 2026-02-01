# inventory/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import F
from .models import (
    Location, Inventory, StockMovement, InventoryAdjustment,
    InventoryCount, InventoryCountItem
)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'location_type', 'is_active', 'manager_display', 'created_at']
    list_filter = ['location_type', 'is_active', 'created_at']
    search_fields = ['name', 'address']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'address', 'location_type', 'is_active', 'manager_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def manager_display(self, obj):
        if obj.manager_id:
            return obj.manager_id.name
        return '-'
    manager_display.short_description = 'Manager'


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = [
        'product_display', 'location', 'quantity_on_hand', 'reserved_quantity', 
        'available_quantity', 'stock_status', 'stock_value_display', 'last_counted_date'
    ]
    list_filter = ['location', 'variant__product__category', 'last_counted_date']
    search_fields = ['location__name']
    readonly_fields = ['created_at', 'updated_at', 'stock_value_display', 'available_quantity']
    
    fieldsets = (
        (None, {
            'fields': ('product', 'location', 'quantity_on_hand', 'reserved_quantity', 'reorder_level')
        }),
        ('Calculated Fields', {
            'fields': ('available_quantity', 'stock_value_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('last_counted_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def product_display(self, obj):
        return f"{obj.product.name} ({obj.product.sku})"
    product_display.short_description = 'Product'
    
    def stock_status(self, obj):
        if obj.quantity_on_hand == 0:
            return format_html('<span style="color: red;">Out of Stock</span>')
        elif obj.is_below_reorder_level:
            return format_html('<span style="color: orange;">Low Stock</span>')
        else:
            return format_html('<span style="color: green;">In Stock</span>')
    stock_status.short_description = 'Status'
    
    def stock_value_display(self, obj):
        return f"${obj.stock_value:,.2f}"
    stock_value_display.short_description = 'Stock Value'


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'product_display', 'location', 'movement_type', 
        'quantity', 'reference_display', 'created_by_user'
    ]
    list_filter = ['movement_type', 'reference_type', 'location', 'created_at']
    search_fields = ['product__name', 'product__sku', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('product', 'location', 'movement_type', 'quantity')
        }),
        ('Reference', {
            'fields': ('reference_type', 'reference_id', 'notes')
        }),
        ('Audit', {
            'fields': ('created_by_user', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def product_display(self, obj):
        return f"{obj.product.name} ({obj.product.sku})"
    product_display.short_description = 'Product'
    
    def reference_display(self, obj):
        if obj.reference_type and obj.reference_id:
            return f"{obj.reference_type.title()} #{obj.reference_id}"
        return '-'
    reference_display.short_description = 'Reference'
    
    def has_add_permission(self, request):
        return False  # Stock movements should be created through business processes
    
    def has_change_permission(self, request, obj=None):
        return False  # Stock movements should be immutable


@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    list_display = [
        'adjustment_number', 'product_display', 'location', 'adjustment_quantity',
        'reason', 'cost_impact_display', 'adjustment_date', 'created_by_user'
    ]
    list_filter = [ 'reason', 'location', 'adjustment_date']
    search_fields = ['adjustment_number', 'product__name', 'product__sku', 'notes']
    readonly_fields = ['adjustment_number', 'cost_impact', 'created_at', 'updated_at']
    date_hierarchy = 'adjustment_date'
    
    fieldsets = (
        (None, {
            'fields': ('product', 'location', 'adjustment_quantity', 'reason', 'adjustment_date')
        }),
        ('Financial', {
            'fields': ('cost_impact', 'currency')
        }),
        ('Approval', {
            'fields': ('approved_by_user', 'notes')
        }),
        ('Audit', {
            'fields': ('adjustment_number', 'created_by_user', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def product_display(self, obj):
        return f"{obj.product.name} ({obj.product.sku})"
    product_display.short_description = 'Product'
    
    def cost_impact_display(self, obj):
        return f"${obj.cost_impact:,.2f}"
    cost_impact_display.short_description = 'Cost Impact'
    
    actions = ['approve_adjustments', 'reject_adjustments']
    
    def approve_adjustments(self, request, queryset):
        approved_count = 0
        for adjustment in queryset.filter(status='pending'):
            try:
                adjustment.approve(request.user)
                approved_count += 1
            except ValueError:
                pass
        
        self.message_user(request, f"{approved_count} adjustments approved successfully.")
    approve_adjustments.short_description = "Approve selected adjustments"
    
    def reject_adjustments(self, request, queryset):
        rejected_count = 0
        for adjustment in queryset.filter(status='pending'):
            try:
                adjustment.reject(request.user)
                rejected_count += 1
            except ValueError:
                pass
        
        self.message_user(request, f"{rejected_count} adjustments rejected.")
    reject_adjustments.short_description = "Reject selected adjustments"


class InventoryCountItemInline(admin.TabularInline):
    model = InventoryCountItem
    extra = 0
    readonly_fields = ['system_quantity', 'variance', 'created_at']
    fields = ['product', 'system_quantity', 'counted_quantity', 'variance', 'condition', 'notes', 'counted_by_user']


@admin.register(InventoryCount)
class InventoryCountAdmin(admin.ModelAdmin):
    list_display = [
        'count_number', 'location', 'count_date', 'status', 
        'total_items_counted', 'variances_found', 'created_by_user'
    ]
    list_filter = ['status', 'location', 'count_date']
    search_fields = ['count_number', 'location__name', 'notes']
    readonly_fields = ['count_number', 'total_items_counted', 'variances_found', 'created_at', 'updated_at']
    date_hierarchy = 'count_date'
    inlines = [InventoryCountItemInline]
    
    fieldsets = (
        (None, {
            'fields': ('location', 'count_date', 'status', 'notes')
        }),
        ('Results', {
            'fields': ('total_items_counted', 'variances_found'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('count_number', 'created_by_user', 'completed_by_user', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['start_counts', 'complete_counts']
    
    def start_counts(self, request, queryset):
        started_count = 0
        for count in queryset.filter(status='planned'):
            try:
                count.start_count()
                started_count += 1
            except ValueError:
                pass
        
        self.message_user(request, f"{started_count} inventory counts started.")
    start_counts.short_description = "Start selected inventory counts"
    
    def complete_counts(self, request, queryset):
        completed_count = 0
        for count in queryset.filter(status='in_progress'):
            try:
                count.complete_count(request.user)
                completed_count += 1
            except ValueError:
                pass
        
        self.message_user(request, f"{completed_count} inventory counts completed.")
    complete_counts.short_description = "Complete selected inventory counts"


@admin.register(InventoryCountItem)
class InventoryCountItemAdmin(admin.ModelAdmin):
    list_display = [
        'count_display', 'product_display', 'system_quantity', 
        'counted_quantity', 'variance', 'counted_by_user'
    ]
    list_filter = ['count__status', 'count__location', 'variance']
    search_fields = ['product__name', 'product__sku', 'count__count_number']
    readonly_fields = ['variance', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('count', 'product', 'system_quantity', 'counted_quantity')
        }),
        ('Results', {
            'fields': ('variance', 'notes', 'counted_by_user')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def count_display(self, obj):
        return obj.count.count_number
    count_display.short_description = 'Count'
    
    def product_display(self, obj):
        return f"{obj.product.name} ({obj.product.sku})"
    product_display.short_description = 'Product'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('count', 'product', 'counted_by_user')


# Custom admin views
class InventoryDashboard:
    """Custom dashboard for inventory overview"""
    def get_context_data(self):
        return {
            'total_locations': Location.objects.filter(is_active=True).count(),
            'total_products_in_stock': Inventory.objects.filter(quantity_on_hand__gt=0).count(),
            'low_stock_items': Inventory.objects.filter(quantity_on_hand__lte=F('reorder_level')).count(),
            'out_of_stock_items': Inventory.objects.filter(quantity_on_hand=0).count(),
            'pending_adjustments': InventoryAdjustment.objects.filter(status='pending').count(),
            'active_counts': InventoryCount.objects.filter(status='in_progress').count(),
        }