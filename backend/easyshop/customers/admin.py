from django.contrib import admin
from django.utils.html import format_html
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Admin interface for Customer model"""
    
    list_display = [
        'customer_number', 'name', 'email', 'phone', 'customer_type',
        'status',
        'get_purchase_count',
        'date_joined'
    ]
    
    list_filter = [
        'customer_type', 'status', 'tax_exempt', 'date_joined',
        # 'get_last_purchase_date',
        'gender'
    ]
    
    search_fields = [
        'customer_number', 'name', 'email', 'phone'
    ]
    
    readonly_fields = [
        'customer_number', 'date_joined',
        'created_at',
        'updated_at', 'credit_available_display', 'average_purchase_display'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'customer_number', 'name', 'gender', 'email', 'phone'
            )
        }),
        ('Customer Details', {
            'fields': (
                'customer_type', 'status', 'date_joined', 'notes', 'photo_url'
            )
        }),
        ('Financial Information', {
            'fields': (
                'balance', 'credit_limit', 'credit_available_display',
                'discount_percentage', 'tax_exempt'
            )
        }),
        ('Purchase Statistics', {
            'fields': (
                'total_purchases', 'purchase_count', 'average_purchase_display',
                'last_purchase_date'
            )
        }),
        ('System Information', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-created_at']
    date_hierarchy = 'date_joined'
    
    actions = [
        'activate_customers', 'deactivate_customers', 'suspend_customers',
        'mark_as_vip', 'reset_discount'
    ]
    
    def balance_display(self, obj):
        """Display balance with color coding"""
        if obj.balance < 0:
            color = 'red'
            icon = '⚠️'
        elif obj.balance > 0:
            color = 'green'
            icon = '✅'
        else:
            color = 'black'
            icon = '⚪'
        
        return format_html(
            '<span style="color: {};">{} ${:,.2f}</span>',
            color, icon, obj.balance
        )
    balance_display.short_description = 'Balance'
    balance_display.admin_order_field = 'balance'
    
    def credit_available_display(self, obj):
        """Display available credit"""
        available = obj.credit_available
        if obj.credit_limit > 0:
            percentage = (available / obj.credit_limit) * 100
            if percentage < 20:
                color = 'red'
            elif percentage < 50:
                color = 'orange'
            else:
                color = 'green'
            
            return format_html(
                '<span style="color: {};">${:,.2f} ({:.1f}%)</span>',
                color, available, percentage
            )
        return f"${available:,.2f}"
    credit_available_display.short_description = 'Credit Available'
    
    def average_purchase_display(self, obj):
        """Display average purchase amount"""
        avg = obj.average_purchase_amount
        return f"${avg:,.2f}" if avg > 0 else "No purchases"
    average_purchase_display.short_description = 'Avg Purchase'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related()
    
    # Admin Actions
    def activate_customers(self, request, queryset):
        """Activate selected customers"""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} customers activated.')
    activate_customers.short_description = 'Activate selected customers'
    
    def deactivate_customers(self, request, queryset):
        """Deactivate selected customers"""
        updated = queryset.update(status='inactive')
        self.message_user(request, f'{updated} customers deactivated.')
    deactivate_customers.short_description = 'Deactivate selected customers'
    
    def suspend_customers(self, request, queryset):
        """Suspend selected customers"""
        updated = queryset.update(status='suspended')
        self.message_user(request, f'{updated} customers suspended.')
    suspend_customers.short_description = 'Suspend selected customers'
    
    def mark_as_vip(self, request, queryset):
        """Mark selected customers as VIP"""
        updated = queryset.update(customer_type='vip')
        self.message_user(request, f'{updated} customers marked as VIP.')
    mark_as_vip.short_description = 'Mark as VIP customers'
    
    def reset_discount(self, request, queryset):
        """Reset discount percentage to 0"""
        updated = queryset.update(discount_percentage=0)
        self.message_user(request, f'Discount reset for {updated} customers.')
    reset_discount.short_description = 'Reset discount percentage'