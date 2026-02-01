import django_filters
from .models import Transaction


class TransactionFilter(django_filters.FilterSet):
    """Advanced filtering for transactions"""
    transaction_date_range = django_filters.DateFromToRangeFilter(field_name='transaction_date')
    amount_range = django_filters.RangeFilter(field_name='amount')
    transaction_type = django_filters.ChoiceFilter(choices=Transaction.TRANSACTION_TYPES)
    party_type = django_filters.ChoiceFilter(choices=Transaction.PARTY_TYPES)
    currency = django_filters.ModelChoiceFilter(queryset=None)
    cash_drawer = django_filters.ModelChoiceFilter(queryset=None)
    created_date_range = django_filters.DateFromToRangeFilter(field_name='created_at')
    
    # Reference filtering
    reference_type = django_filters.CharFilter(field_name='reference_type')
    has_reference = django_filters.BooleanFilter(method='filter_has_reference')
    
    # User filtering
    created_by = django_filters.ModelChoiceFilter(
        field_name='created_by_user',
        queryset=None
    )
    
    class Meta:
        model = Transaction
        fields = {
            'amount': ['exact', 'gte', 'lte'],
            'transaction_date': ['exact', 'gte', 'lte'],
            'transaction_type': ['exact'],
            'party_type': ['exact'],
            'currency': ['exact'],
            'cash_drawer': ['exact'],
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically set querysets
        from core.models import Currency
        from .models import CashDrawer
        from accounts.models import User
        
        self.filters['currency'].queryset = Currency.objects.filter(is_active=True)
        self.filters['cash_drawer'].queryset = CashDrawer.objects.filter(is_active=True)
        self.filters['created_by'].queryset = User.objects.filter(is_active=True)
    
    def filter_has_reference(self, queryset, name, value):
        if value:
            return queryset.exclude(reference_type__isnull=True, reference_id__isnull=True)
        else:
            return queryset.filter(reference_type__isnull=True, reference_id__isnull=True)
