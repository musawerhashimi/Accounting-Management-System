import django_filters
from django.db import models
from .models import Sales, Returns


class SalesFilter(django_filters.FilterSet):
    """Filter for Sales model"""
    
    # Date range filters
    sale_date_from = django_filters.DateFilter(
        field_name='sale_date',
        lookup_expr='date__gte',
        label='Sale Date From'
    )
    sale_date_to = django_filters.DateFilter(
        field_name='sale_date',
        lookup_expr='date__lte',
        label='Sale Date To'
    )
    
    # Amount range filters
    total_amount_min = django_filters.NumberFilter(
        field_name='total_amount',
        lookup_expr='gte',
        label='Minimum Total Amount'
    )
    total_amount_max = django_filters.NumberFilter(
        field_name='total_amount',
        lookup_expr='lte',
        label='Maximum Total Amount'
    )
    
    # Status filters
    status = django_filters.ChoiceFilter(
        choices=Sales.STATUS_CHOICES,
        label='Status'
    )
    payment_status = django_filters.ChoiceFilter(
        choices=Sales.PAYMENT_STATUS_CHOICES,
        label='Payment Status'
    )
    
    # Relationship filters
    customer = django_filters.NumberFilter(
        field_name='customer_id',
        label='Customer ID'
    )
    customer_name = django_filters.CharFilter(
        field_name='customer__name',
        lookup_expr='icontains',
        label='Customer Name'
    )
    location = django_filters.NumberFilter(
        field_name='location_id',
        label='Location ID'
    )
    location_name = django_filters.CharFilter(
        field_name='location__name',
        lookup_expr='icontains',
        label='Location Name'
    )
    
    # Currency filter
    currency = django_filters.NumberFilter(
        field_name='currency_id',
        label='Currency ID'
    )
    currency_code = django_filters.CharFilter(
        field_name='currency__code',
        lookup_expr='iexact',
        label='Currency Code'
    )
    
    # Created by filter
    created_by = django_filters.NumberFilter(
        field_name='created_by_user_id',
        label='Created By User ID'
    )
    
    # Has customer filter (for walk-in vs registered customers)
    has_customer = django_filters.BooleanFilter(
        field_name='customer',
        lookup_expr='isnull',
        exclude=True,
        label='Has Customer'
    )
    
    # Paid status filters
    is_fully_paid = django_filters.BooleanFilter(
        method='filter_fully_paid',
        label='Is Fully Paid'
    )
    has_balance = django_filters.BooleanFilter(
        method='filter_has_balance',
        label='Has Outstanding Balance'
    )
    
    # Advanced filters
    items_count_min = django_filters.NumberFilter(
        method='filter_items_count_min',
        label='Minimum Items Count'
    )
    items_count_max = django_filters.NumberFilter(
        method='filter_items_count_max',
        label='Maximum Items Count'
    )
    
    class Meta:
        model = Sales
        fields = [
            'sale_number', 'status', 'payment_status', 'customer', 
            'location', 'currency'
        ]
    
    def filter_fully_paid(self, queryset, name, value):
        """Filter sales that are fully paid"""
        if value is True:
            return queryset.filter(payment_status='paid')
        elif value is False:
            return queryset.exclude(payment_status='paid')
        return queryset
    
    def filter_has_balance(self, queryset, name, value):
        """Filter sales with outstanding balance"""
        if value is True:
            return queryset.filter(payment_status__in=['pending', 'partial'])
        elif value is False:
            return queryset.exclude(payment_status__in=['pending', 'partial'])
        return queryset
    
    def filter_items_count_min(self, queryset, name, value):
        """Filter by minimum number of items"""
        return queryset.annotate(
            items_count=models.Count('items')
        ).filter(items_count__gte=value)
    
    def filter_items_count_max(self, queryset, name, value):
        """Filter by maximum number of items"""
        return queryset.annotate(
            items_count=models.Count('items')
        ).filter(items_count__lte=value)


class ReturnsFilter(django_filters.FilterSet):
    """Filter for Returns model"""
    
    # Date range filters
    return_date_from = django_filters.DateFilter(
        field_name='return_date',
        lookup_expr='date__gte',
        label='Return Date From'
    )
    return_date_to = django_filters.DateFilter(
        field_name='return_date',
        lookup_expr='date__lte',
        label='Return Date To'
    )
    
    # Amount range filters
    refund_amount_min = django_filters.NumberFilter(
        field_name='total_refund_amount',
        lookup_expr='gte',
        label='Minimum Refund Amount'
    )
    refund_amount_max = django_filters.NumberFilter(
        field_name='total_refund_amount',
        lookup_expr='lte',
        label='Maximum Refund Amount'
    )
    
    # Status and reason filters
    status = django_filters.ChoiceFilter(
        choices=Returns.STATUS_CHOICES,
        label='Status'
    )
    reason = django_filters.ChoiceFilter(
        choices=Returns.REASON_CHOICES,
        label='Reason'
    )
    
    # Relationship filters
    customer = django_filters.NumberFilter(
        field_name='customer_id',
        label='Customer ID'
    )
    customer_name = django_filters.CharFilter(
        field_name='customer__name',
        lookup_expr='icontains',
        label='Customer Name'
    )
    
    # Original sale filters
    original_sale = django_filters.NumberFilter(
        field_name='original_sale_id',
        label='Original Sale ID'
    )
    original_sale_number = django_filters.CharFilter(
        field_name='original_sale__sale_number',
        lookup_expr='icontains',
        label='Original Sale Number'
    )
    
    # Currency filter
    currency = django_filters.NumberFilter(
        field_name='currency_id',
        label='Currency ID'
    )
    currency_code = django_filters.CharFilter(
        field_name='currency__code',
        lookup_expr='iexact',
        label='Currency Code'
    )
    
    # Processed by filter
    processed_by = django_filters.NumberFilter(
        field_name='processed_by_user_id',
        label='Processed By User ID'
    )
    
    # Status-based filters
    pending_approval = django_filters.BooleanFilter(
        method='filter_pending_approval',
        label='Pending Approval'
    )
    is_processed = django_filters.BooleanFilter(
        method='filter_processed',
        label='Is Processed'
    )
    
    # Items count filters
    items_count_min = django_filters.NumberFilter(
        method='filter_items_count_min',
        label='Minimum Items Count'
    )
    items_count_max = django_filters.NumberFilter(
        method='filter_items_count_max',
        label='Maximum Items Count'
    )
    
    class Meta:
        model = Returns
        fields = [
            'return_number', 'status', 'reason', 'customer', 
            'original_sale', 'currency'
        ]
    
    def filter_pending_approval(self, queryset, name, value):
        """Filter returns pending approval"""
        if value is True:
            return queryset.filter(status='pending')
        elif value is False:
            return queryset.exclude(status='pending')
        return queryset
    
    def filter_processed(self, queryset, name, value):
        """Filter processed returns"""
        if value is True:
            return queryset.filter(status='processed')
        elif value is False:
            return queryset.exclude(status='processed')
        return queryset
    
    def filter_items_count_min(self, queryset, name, value):
        """Filter by minimum number of items"""
        return queryset.annotate(
            items_count=models.Count('items')
        ).filter(items_count__gte=value)
    
    def filter_items_count_max(self, queryset, name, value):
        """Filter by maximum number of items"""
        return queryset.annotate(
            items_count=models.Count('items')
        ).filter(items_count__lte=value)