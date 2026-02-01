from django.contrib import admin
from django.utils.html import format_html
from .models import Department, Category, ProductPrice


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'categories_count', 'products_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    
    def categories_count(self, obj):
        return obj.active_categories_count
    categories_count.short_description = 'Active Categories'
    
    def products_count(self, obj):
        return obj.products_count
    products_count.short_description = 'Total Products'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'is_active', 'products_count', 'created_at']
    list_filter = ['is_active', 'department', 'created_at']
    search_fields = ['name', 'description', 'department__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['department__name', 'name']
    
    def products_count(self, obj):
        return obj.products_count
    products_count.short_description = 'Products'


class ProductPriceInline(admin.TabularInline):
    model = ProductPrice
    extra = 0
    readonly_fields = ['created_at', 'profit_margin']
    fields = [
        'cost_price', 'selling_price', 'currency', 
        'effective_date', 'end_date', 'created_by_user', 
        'profit_margin', 'created_at'
    ]
    
    def profit_margin(self, obj):
        return f"{obj.profit_margin:.2f}%"
    profit_margin.short_description = 'Profit Margin'


@admin.register(ProductPrice)
class ProductPriceAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'cost_price', 'selling_price',
        'cost_currency', 'selling_currency',
        'effective_date', 'end_date', 'is_current', 'profit_margin',
        'created_by_user', 'created_at'
    ]
    list_filter = [
        'cost_currency', 'selling_currency', 'effective_date', 'end_date', 
        'created_at', 'created_by_user'
    ]
    search_fields = [
        'product__name', 'product__sku', 'created_by_user__username'
    ]
    readonly_fields = ['created_at', 'profit_margin', 'is_current']
    ordering = ['-effective_date']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product', 'cost_currency', 'selling_currency', 'created_by_user'
        )
    
    def profit_margin(self, obj):
        return f"{obj.profit_margin:.2f}%"
    profit_margin.short_description = 'Profit Margin'
    
    def is_current(self, obj):
        if obj.is_current:
            return format_html(
                '<span style="color: green; font-weight: bold;">✅ Current</span>'
            )
        return format_html(
            '<span style="color: gray;">Historical</span>'
        )
    is_current.short_description = 'Status'
    is_current.admin_order_field = 'end_date'