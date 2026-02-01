# sales/admin.py

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum, Count
from django.contrib.admin import SimpleListFilter
from .models import Sales, SaleItem, Returns, ReturnItem


class PaymentStatusFilter(SimpleListFilter):
    """Custom filter for payment status"""
    title = 'Payment Status'
    parameter_name = 'payment_status'

    def lookups(self, request, model_admin):
        return Sales.PAYMENT_STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(payment_status=self.value())
        return queryset


class SaleDateFilter(SimpleListFilter):
    """Custom filter for sale date ranges"""
    title = 'Sale Date'
    parameter_name = 'sale_date_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('this_week', 'This Week'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
            ('this_year', 'This Year'),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'today':
            return queryset.filter(sale_date__date=now.date())
        elif self.value() == 'yesterday':
            yesterday = now.date() - timezone.timedelta(days=1)
            return queryset.filter(sale_date__date=yesterday)
        elif self.value() == 'this_week':
            start_week = now.date() - timezone.timedelta(days=now.weekday())
            return queryset.filter(sale_date__date__gte=start_week)
        elif self.value() == 'this_month':
            return queryset.filter(sale_date__year=now.year, sale_date__month=now.month)
        elif self.value() == 'last_month':
            if now.month == 1:
                return queryset.filter(sale_date__year=now.year-1, sale_date__month=12)
            else:
                return queryset.filter(sale_date__year=now.year, sale_date__month=now.month-1)
        elif self.value() == 'this_year':
            return queryset.filter(sale_date__year=now.year)
        return queryset


class SaleItemInline(admin.TabularInline):
    """Inline admin for sale items"""
    model = SaleItem
    extra = 0
    readonly_fields = ('line_total',)
    fields = ('product', 'quantity', 'unit_price', 'discount_amount', 'line_total')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


@admin.register(Sales)
class SaleAdmin(admin.ModelAdmin):
    """Admin configuration for Sale model"""
    list_display = [
        'sale_number', 'customer_link', 'sale_date', 'total_amount_display', 
        'payment_status_display', 'total_items_display', 'created_by_user'
    ]
    list_filter = [
        PaymentStatusFilter, SaleDateFilter, 'currency', 'created_by_user'
    ]
    search_fields = [
        'sale_number', 'customer__name', 'customer__customer_number', 
        'customer__email', 'notes'
    ]
    readonly_fields = [
        'sale_number', 'subtotal', 'total_amount', 'total_items_display',
        'total_paid_display', 'balance_due_display', 'created_at', 'updated_at'
    ]
    fieldsets = (
        ('Sale Information', {
            'fields': ('sale_number', 'customer', 'sale_date', 'currency')
        }),
        ('Financial Details', {
            'fields': (
                'subtotal', 'discount_amount', 'tax_amount', 'total_amount',
                'total_paid_display', 'balance_due_display', 'payment_status'
            )
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by_user'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    inlines = [SaleItemInline]
    date_hierarchy = 'sale_date'
    ordering = ['-sale_date']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'customer', 'currency', 'created_by_user'
        ).prefetch_related('sale_items')
    
    def customer_link(self, obj):
        """Link to customer detail page"""
        if obj.customer:
            url = reverse('admin:customers_customer_change', args=[obj.customer.id])
            return format_html('<a href="{}">{}</a>', url, obj.customer.name)
        return '-'
    customer_link.short_description = 'Customer'
    customer_link.admin_order_field = 'customer__name'
    
    def total_amount_display(self, obj):
        """Display total amount with currency"""
        return f"{obj.currency.symbol}{obj.total_amount:,.2f}"
    total_amount_display.short_description = 'Total Amount'
    total_amount_display.admin_order_field = 'total_amount'
    
    def payment_status_display(self, obj):
        """Display payment status with color coding"""
        colors = {
            'paid': 'green',
            'partial': 'orange',
            'pending': 'red',
            'overdue': 'darkred',
            'refunded': 'blue'
        }
        color = colors.get(obj.payment_status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_payment_status_display()
        )
    payment_status_display.short_description = 'Payment Status'
    payment_status_display.admin_order_field = 'payment_status'
    
    def total_items_display(self, obj):
        """Display total number of items"""
        return obj.total_items
    total_items_display.short_description = 'Items'
    
    def total_paid_display(self, obj):
        """Display total amount paid"""
        return f"{obj.currency.symbol}{obj.total_paid:,.2f}"
    total_paid_display.short_description = 'Total Paid'
    
    def balance_due_display(self, obj):
        """Display balance due with color coding"""
        balance = obj.balance_due
        color = 'green' if balance <= 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{:,.2f}</span>',
            color, obj.currency.symbol, balance
        )
    balance_due_display.short_description = 'Balance Due'
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly after creation"""
        readonly = list(self.readonly_fields)
        if obj:  # Editing existing object
            readonly.extend(['customer', 'currency', 'created_by_user'])
        return readonly
    
    def save_model(self, request, obj, form, change):
        """Set created_by_user when creating new sale"""
        if not change:  # Creating new object
            obj.created_by_user = request.user
        super().save_model(request, obj, form, change)
    
    def has_delete_permission(self, request, obj=None):
        """Restrict delete permissions for processed sales"""
        if obj and obj.payment_status == 'paid':
            return False
        return super().has_delete_permission(request, obj)


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    """Admin configuration for SaleItem model"""
    list_display = [
        'sale_link', 'product_link', 'quantity', 'unit_price', 
        'discount_amount', 'line_total_display'
    ]
    list_filter = ['sale__sale_date', 'inventory__variant__product__category']
    search_fields = [
        'sale__sale_number', 'inventory__variant__variant_name', 'inventory__variant__sku', # 'product__barcode'
    ]
    readonly_fields = ['line_total']
    raw_id_fields = ['sale', 'inventory']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sale', 'product')
    
    def sale_link(self, obj):
        """Link to sale detail page"""
        url = reverse('admin:sales_sale_change', args=[obj.sale.id])
        return format_html('<a href="{}">{}</a>', url, obj.sale.sale_number)
    sale_link.short_description = 'Sale'
    sale_link.admin_order_field = 'sale__sale_number'
    
    def product_link(self, obj):
        """Link to product detail page"""
        url = reverse('admin:catalog_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)
    product_link.short_description = 'Product'
    product_link.admin_order_field = 'product__name'
    
    def line_total_display(self, obj):
        """Display line total with currency"""
        return f"{obj.sale.currency.symbol}{obj.line_total:,.2f}"
    line_total_display.short_description = 'Line Total'
    line_total_display.admin_order_field = 'line_total'


class ReturnItemInline(admin.TabularInline):
    """Inline admin for return items"""
    model = ReturnItem
    extra = 0
    readonly_fields = ('product_name', 'original_quantity', 'original_price')
    fields = (
        'sale_item', 'product_name', 'original_quantity', 'original_price',
        'quantity_returned', 'condition', 'refund_amount', 'restocked'
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sale_item__product')
    
    def product_name(self, obj):
        """Display product name"""
        return obj.sale_item.product.name if obj.sale_item else '-'
    product_name.short_description = 'Product'
    
    def original_quantity(self, obj):
        """Display original quantity sold"""
        return obj.sale_item.quantity if obj.sale_item else '-'
    original_quantity.short_description = 'Original Qty'
    
    def original_price(self, obj):
        """Display original unit price"""
        return obj.sale_item.unit_price if obj.sale_item else '-'
    original_price.short_description = 'Original Price'


@admin.register(Returns)
class ReturnAdmin(admin.ModelAdmin):
    """Admin configuration for Return model"""
    list_display = [
        'return_number', 'original_sale_link', 'customer_link', 'return_date',
        'reason', 'total_refund_amount_display', 'status_display', 'processed_by_user'
    ]
    list_filter = ['status', 'reason', 'return_date', 'processed_by_user']
    search_fields = [
        'return_number', 'original_sale__sale_number', 'customer__name',
        'customer__customer_number'
    ]
    readonly_fields = [
        'return_number', 'total_refund_amount', 'total_items_display',
        'created_at', 'updated_at'
    ]
    fieldsets = (
        ('Return Information', {
            'fields': ('return_number', 'original_sale', 'customer', 'return_date')
        }),
        ('Return Details', {
            'fields': ('reason', 'status', 'total_refund_amount', 'currency')
        }),
        ('Processing Information', {
            'fields': ('processed_by_user', 'notes'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    inlines = [ReturnItemInline]
    date_hierarchy = 'return_date'
    ordering = ['-return_date']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'customer', 'original_sale', 'currency', 'processed_by_user'
        ).prefetch_related('return_items')
    
    def original_sale_link(self, obj):
        """Link to original sale"""
        if obj.original_sale:
            url = reverse('admin:sales_sale_change', args=[obj.original_sale.id])
            return format_html('<a href="{}">{}</a>', url, obj.original_sale.sale_number)
        return '-'
    original_sale_link.short_description = 'Original Sale'
    original_sale_link.admin_order_field = 'original_sale__sale_number'
    
    def customer_link(self, obj):
        """Link to customer detail page"""
        if obj.customer:
            url = reverse('admin:customers_customer_change', args=[obj.customer.id])
            return format_html('<a href="{}">{}</a>', url, obj.customer.name)
        return '-'
    customer_link.short_description = 'Customer'
    customer_link.admin_order_field = 'customer__name'
    
    def total_refund_amount_display(self, obj):
        """Display refund amount with currency"""
        return f"{obj.currency.symbol}{obj.total_refund_amount:,.2f}"
    total_refund_amount_display.short_description = 'Refund Amount'
    total_refund_amount_display.admin_order_field = 'total_refund_amount'
    
    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'processed': 'blue'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def total_items_display(self, obj):
        """Display total number of items being returned"""
        return obj.total_items
    total_items_display.short_description = 'Items'
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly after creation"""
        readonly = list(self.readonly_fields)
        if obj:  # Editing existing object
            readonly.extend(['original_sale', 'customer', 'currency'])
        return readonly
    
    def has_delete_permission(self, request, obj=None):
        """Restrict delete permissions for processed returns"""
        if obj and obj.status == 'processed':
            return False
        return super().has_delete_permission(request, obj)


@admin.register(ReturnItem)
class ReturnItemAdmin(admin.ModelAdmin):
    """Admin configuration for ReturnItem model"""
    list_display = [
        'return_link', 'product_name', 'quantity_returned', 'condition',
        'refund_amount_display', 'restocked'
    ]
    list_filter = ['condition', 'restocked', 'return_order__status']
    search_fields = [
        'return_order__return_number', 'sale_item__product__name',
        'sale_item__product__sku'
    ]
    readonly_fields = ['product_name', 'original_quantity', 'original_price']
    raw_id_fields = ['return_order', 'sale_item']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'return_order', 'sale_item__product'
        )
    
    def return_link(self, obj):
        """Link to return detail page"""
        url = reverse('admin:sales_return_change', args=[obj.return_order.id])
        return format_html('<a href="{}">{}</a>', url, obj.return_order.return_number)
    return_link.short_description = 'Return'
    return_link.admin_order_field = 'return_order__return_number'
    
    def product_name(self, obj):
        """Display product name"""
        return obj.sale_item.product.name if obj.sale_item else '-'
    product_name.short_description = 'Product'
    
    def original_quantity(self, obj):
        """Display original quantity sold"""
        return obj.sale_item.quantity if obj.sale_item else '-'
    original_quantity.short_description = 'Original Qty'
    
    def original_price(self, obj):
        """Display original unit price"""
        return obj.sale_item.unit_price if obj.sale_item else '-'
    original_price.short_description = 'Original Price'
    
    def refund_amount_display(self, obj):
        """Display refund amount with currency"""
        return f"{obj.return_order.currency.symbol}{obj.refund_amount:,.2f}"
    refund_amount_display.short_description = 'Refund Amount'
    refund_amount_display.admin_order_field = 'refund_amount'


# Admin site customization
admin.site.site_header = "Business Management System"
admin.site.site_title = "Sales Management"
admin.site.index_title = "Sales Administration"