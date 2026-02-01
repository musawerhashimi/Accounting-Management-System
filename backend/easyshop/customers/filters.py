import django_filters
from django.db.models import Q
from .models import Customer


class CustomerFilter(django_filters.FilterSet):
    """Advanced filtering for customers"""
    
    # Text filters
    name = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    phone = django_filters.CharFilter(lookup_expr='icontains')
    customer_number = django_filters.CharFilter(lookup_expr='icontains')
    
    # Choice filters
    customer_type = django_filters.ChoiceFilter(choices=Customer.CUSTOMER_TYPE_CHOICES)
    status = django_filters.ChoiceFilter(choices=Customer.STATUS_CHOICES)
    gender = django_filters.ChoiceFilter(choices=Customer.GENDER_CHOICES)
    
    # Boolean filters
    tax_exempt = django_filters.BooleanFilter()
    has_email = django_filters.BooleanFilter(method='filter_has_email')
    has_phone = django_filters.BooleanFilter(method='filter_has_phone')
    
    balance_min = django_filters.NumberFilter(field_name='balance', lookup_expr='gte')
    balance_max = django_filters.NumberFilter(field_name='balance', lookup_expr='lte')
    discount_percentage_min = django_filters.NumberFilter(field_name='discount_percentage', lookup_expr='gte')
    discount_percentage_max = django_filters.NumberFilter(field_name='discount_percentage', lookup_expr='lte')
    
    # Date filters
    date_joined_after = django_filters.DateFilter(field_name='date_joined', lookup_expr='gte')
    date_joined_before = django_filters.DateFilter(field_name='date_joined', lookup_expr='lte')
    birth_date_month = django_filters.NumberFilter(field_name='birth_date__month')
    anniversary_month = django_filters.NumberFilter(field_name='anniversary_date__month')
    
    # Related field filters
    sales_rep = django_filters.NumberFilter(field_name='sales_rep__id')
    preferred_currency = django_filters.NumberFilter(field_name='preferred_currency__id')
    
    # Location filters
    city = django_filters.CharFilter(
        field_name='addresses__city',
        lookup_expr='icontains',
        distinct=True
    )
    state = django_filters.CharFilter(
        field_name='addresses__state',
        lookup_expr='icontains',
        distinct=True
    )
    country = django_filters.CharFilter(
        field_name='addresses__country',
        lookup_expr='icontains',
        distinct=True
    )
    
    # Custom filters
    search = django_filters.CharFilter(method='filter_search')
    inactive_days = django_filters.NumberFilter(method='filter_inactive_days')
    
    class Meta:
        model = Customer
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set queryset for groups filter based on request user's tenant
        
    def filter_has_email(self, queryset, name, value):
        """Filter customers who have/don't have email"""
        if value:
            return queryset.exclude(email__isnull=True).exclude(email='')
        else:
            return queryset.filter(Q(email__isnull=True) | Q(email=''))

    def filter_has_phone(self, queryset, name, value):
        """Filter customers who have/don't have phone"""
        if value:
            return queryset.exclude(phone__isnull=True).exclude(phone='')
        else:
            return queryset.filter(Q(phone__isnull=True) | Q(phone=''))

    def filter_by_groups(self, queryset, name, value):
        """Filter customers by group membership"""
        if value:
            group_ids = [group.id for group in value]
            return queryset.filter(
                group_memberships__group_id__in=group_ids,
                group_memberships__is_active=True
            ).distinct()
        return queryset

    def filter_search(self, queryset, name, value):
        """Global search across multiple fields"""
        if value:
            return queryset.filter(
                Q(name__icontains=value) |
                Q(customer_number__icontains=value) |
                Q(email__icontains=value) |
                Q(phone__icontains=value)
            )
        return queryset

    def filter_inactive_days(self, queryset, name, value):
        """Filter customers who haven't purchased in X days"""
        if value:
            from django.utils import timezone
            from datetime import timedelta
            cutoff_date = timezone.now().date() - timedelta(days=value)
            
            return queryset.filter(
                Q(sales__sale_date__lt=cutoff_date) |
                Q(sales__isnull=True)
            ).distinct()
        return queryset
