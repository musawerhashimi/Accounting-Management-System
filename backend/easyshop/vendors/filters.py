import django_filters
from django.db.models import Q
from django.utils import timezone
from .models import  Purchase


class PurchaseFilter(django_filters.FilterSet):
    """Filter class for Purchase model"""
    
    # Text filters
    purchase_number = django_filters.CharFilter(lookup_expr='icontains')
    vendor_invoice_number = django_filters.CharFilter(lookup_expr='icontains')
    reference_number = django_filters.CharFilter(lookup_expr='icontains')
    
    # Vendor filters
    vendor = django_filters.NumberFilter(field_name='vendor_id')
    vendor_name = django_filters.CharFilter(field_name='vendor__name', lookup_expr='icontains')
    vendor_code = django_filters.CharFilter(field_name='vendor__vendor_code', lookup_expr='icontains')
    
    # Choice filters
    status = django_filters.ChoiceFilter(choices=Purchase.STATUS_CHOICES)
    payment_status = django_filters.ChoiceFilter(choices=Purchase.STATUS_CHOICES)
    
    # Date filters
    purchase_date_after = django_filters.DateFilter(field_name='purchase_date', lookup_expr='gte')
    purchase_date_before = django_filters.DateFilter(field_name='purchase_date', lookup_expr='lte')
    order_date_after = django_filters.DateFilter(field_name='order_date', lookup_expr='gte')
    order_date_before = django_filters.DateFilter(field_name='order_date', lookup_expr='lte')
    expected_delivery_after = django_filters.DateFilter(field_name='expected_delivery_date', lookup_expr='gte')
    expected_delivery_before = django_filters.DateFilter(field_name='expected_delivery_date', lookup_expr='lte')
    actual_delivery_after = django_filters.DateFilter(field_name='actual_delivery_date', lookup_expr='gte')
    actual_delivery_before = django_filters.DateFilter(field_name='actual_delivery_date', lookup_expr='lte')
    
    # Amount filters
    total_amount_min = django_filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    total_amount_max = django_filters.NumberFilter(field_name='total_amount', lookup_expr='lte')
    subtotal_min = django_filters.NumberFilter(field_name='subtotal', lookup_expr='gte')
    subtotal_max = django_filters.NumberFilter(field_name='subtotal', lookup_expr='lte')
    
    # Currency filter
    currency = django_filters.NumberFilter(field_name='currency_id')
    
    # Boolean filters
    overdue = django_filters.BooleanFilter(method='filter_overdue')
    has_received_items = django_filters.BooleanFilter(method='filter_has_received_items')
    fully_received = django_filters.BooleanFilter(method='filter_fully_received')
    
    # User filters
    created_by = django_filters.NumberFilter(field_name='created_by_user')
    approved_by = django_filters.NumberFilter(field_name='approved_by_user')
    
    # Date range shortcuts
    this_week = django_filters.BooleanFilter(method='filter_this_week')
    this_month = django_filters.BooleanFilter(method='filter_this_month')
    this_year = django_filters.BooleanFilter(method='filter_this_year')
    last_30_days = django_filters.BooleanFilter(method='filter_last_30_days')
    
    # Product filters
    contains_product = django_filters.NumberFilter(method='filter_contains_product')
    
    class Meta:
        model = Purchase
        fields = [
            'purchase_number', 'vendor_invoice_number', 'reference_number',
            'vendor', 'vendor_name', 'vendor_code', 'status', 'payment_status',
            'purchase_date_after', 'purchase_date_before', 'order_date_after', 'order_date_before',
            'expected_delivery_after', 'expected_delivery_before', 'actual_delivery_after', 'actual_delivery_before',
            'total_amount_min', 'total_amount_max', 'subtotal_min', 'subtotal_max',
            'currency', 'overdue', 'has_received_items', 'fully_received',
            'created_by', 'approved_by', 'this_week', 'this_month', 'this_year',
            'last_30_days', 'contains_product'
        ]
    
    def filter_overdue(self, queryset, name, value):
        if value:
            current_date = timezone.now().date()
            return queryset.filter(
                expected_delivery_date__lt=current_date,
                status__in=['approved', 'ordered', 'partial_received']
            )
        return queryset
    
    def filter_has_received_items(self, queryset, name, value):
        if value:
            return queryset.filter(items__received_quantity__gt=0).distinct()
        elif value is False:
            return queryset.filter(items__received_quantity=0).distinct()
        return queryset
    
    def filter_fully_received(self, queryset, name, value):
        if value:
            return queryset.filter(status='received')
        elif value is False:
            return queryset.exclude(status='received')
        return queryset
    
    def filter_this_week(self, queryset, name, value):
        if value:
            from django.utils.dates import WEEKDAYS
            today = timezone.now().date()
            start_week = today - timezone.timedelta(days=today.weekday())
            end_week = start_week + timezone.timedelta(days=6)
            return queryset.filter(
                purchase_date__range=[start_week, end_week]
            )
        return queryset
    
    def filter_this_month(self, queryset, name, value):
        if value:
            today = timezone.now().date()
            return queryset.filter(
                purchase_date__year=today.year,
                purchase_date__month=today.month
            )
        return queryset
    
    def filter_this_year(self, queryset, name, value):
        if value:
            today = timezone.now().date()
            return queryset.filter(purchase_date__year=today.year)
        return queryset
    
    def filter_last_30_days(self, queryset, name, value):
        if value:
            thirty_days_ago = timezone.now().date() - timezone.timedelta(days=30)
            return queryset.filter(purchase_date__gte=thirty_days_ago)
        return queryset
    
    def filter_contains_product(self, queryset, name, value):
        if value:
            return queryset.filter(items__product_id=value).distinct()
        return queryset

