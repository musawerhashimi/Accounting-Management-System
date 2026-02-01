import django_filters
from django.db.models import Q
from .models import Employee, EmployeePosition, EmployeeCareer, Member


class EmployeePositionFilter(django_filters.FilterSet):
    department = django_filters.NumberFilter(field_name='department')
    department_name = django_filters.CharFilter(field_name='department__name', lookup_expr='icontains')
    salary_min = django_filters.NumberFilter(field_name='base_salary', lookup_expr='gte')
    salary_max = django_filters.NumberFilter(field_name='base_salary', lookup_expr='lte')
    currency = django_filters.NumberFilter(field_name='currency')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    has_employees = django_filters.BooleanFilter(method='filter_has_employees')

    class Meta:
        model = EmployeePosition
        fields = ['department', 'is_active']

    def filter_has_employees(self, queryset, name, value):
        if value:
            return queryset.filter(
                careers__status='active',
                careers__end_date__isnull=True
            ).distinct()
        else:
            return queryset.exclude(
                careers__status='active',
                careers__end_date__isnull=True
            ).distinct()


class EmployeeFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    employee_number = django_filters.CharFilter(lookup_expr='icontains')
    phone = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    status = django_filters.ChoiceFilter(choices=Employee.EMPLOYEE_STATUS_CHOICES)
    hire_date_from = django_filters.DateFilter(field_name='hire_date', lookup_expr='gte')
    hire_date_to = django_filters.DateFilter(field_name='hire_date', lookup_expr='lte')
    hire_year = django_filters.NumberFilter(field_name='hire_date__year')
    hire_month = django_filters.NumberFilter(field_name='hire_date__month')
    
    # Current position filters
    current_position = django_filters.NumberFilter(method='filter_current_position')
    current_department = django_filters.NumberFilter(method='filter_current_department')
    salary_min = django_filters.NumberFilter(method='filter_salary_min')
    salary_max = django_filters.NumberFilter(method='filter_salary_max')
    
    # Service years filters
    service_years_min = django_filters.NumberFilter(method='filter_service_years_min')
    service_years_max = django_filters.NumberFilter(method='filter_service_years_max')
    
    balance_min = django_filters.NumberFilter(field_name='balance', lookup_expr='gte')
    balance_max = django_filters.NumberFilter(field_name='balance', lookup_expr='lte')
    
    created_by = django_filters.NumberFilter(field_name='created_by_user')

    class Meta:
        model = Employee
        fields = ['status']

    def filter_current_position(self, queryset, name, value):
        return queryset.filter(
            careers__position_id=value,
            careers__status='active',
            careers__end_date__isnull=True
        )

    def filter_current_department(self, queryset, name, value):
        return queryset.filter(
            careers__position__department_id=value,
            careers__status='active',
            careers__end_date__isnull=True
        )

    def filter_salary_min(self, queryset, name, value):
        return queryset.filter(
            careers__salary__gte=value,
            careers__status='active',
            careers__end_date__isnull=True
        )

    def filter_salary_max(self, queryset, name, value):
        return queryset.filter(
            careers__salary__lte=value,
            careers__status='active',
            careers__end_date__isnull=True
        )

    def filter_service_years_min(self, queryset, name, value):
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now().date() - timedelta(days=value * 365.25)
        return queryset.filter(hire_date__lte=cutoff_date)

    def filter_service_years_max(self, queryset, name, value):
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now().date() - timedelta(days=value * 365.25)
        return queryset.filter(hire_date__gte=cutoff_date)


class EmployeeCareerFilter(django_filters.FilterSet):
    employee = django_filters.NumberFilter(field_name='employee')
    employee_name = django_filters.CharFilter(field_name='employee__name', lookup_expr='icontains')
    position = django_filters.NumberFilter(field_name='position')
    position_name = django_filters.CharFilter(field_name='position__position_name', lookup_expr='icontains')
    department = django_filters.NumberFilter(field_name='position__department')
    status = django_filters.ChoiceFilter(choices=EmployeeCareer.CAREER_STATUS_CHOICES)
    
    start_date_from = django_filters.DateFilter(field_name='start_date', lookup_expr='gte')
    start_date_to = django_filters.DateFilter(field_name='start_date', lookup_expr='lte')
    end_date_from = django_filters.DateFilter(field_name='end_date', lookup_expr='gte')
    end_date_to = django_filters.DateFilter(field_name='end_date', lookup_expr='lte')
    
    salary_min = django_filters.NumberFilter(field_name='salary', lookup_expr='gte')
    salary_max = django_filters.NumberFilter(field_name='salary', lookup_expr='lte')
    currency = django_filters.NumberFilter(field_name='currency')
    
    is_active = django_filters.BooleanFilter(method='filter_is_active')
    is_current = django_filters.BooleanFilter(method='filter_is_current')
    
    created_by = django_filters.NumberFilter(field_name='created_by_user')

    class Meta:
        model = EmployeeCareer
        fields = ['status']

    def filter_is_active(self, queryset, name, value):
        if value:
            return queryset.filter(status='active')
        else:
            return queryset.exclude(status='active')

    def filter_is_current(self, queryset, name, value):
        if value:
            return queryset.filter(
                status='active',
                end_date__isnull=True
            )
        else:
            return queryset.exclude(
                status='active',
                end_date__isnull=True
            )


class MemberFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    status = django_filters.ChoiceFilter(choices=Member.MEMBER_STATUS_CHOICES)
    
    ownership_min = django_filters.NumberFilter(field_name='ownership_percentage', lookup_expr='gte')
    ownership_max = django_filters.NumberFilter(field_name='ownership_percentage', lookup_expr='lte')
    
    investment_min = django_filters.NumberFilter(field_name='investment_amount', lookup_expr='gte')
    investment_max = django_filters.NumberFilter(field_name='investment_amount', lookup_expr='lte')
    
    profit_share_min = django_filters.NumberFilter(field_name='profit_share', lookup_expr='gte')
    profit_share_max = django_filters.NumberFilter(field_name='profit_share', lookup_expr='lte')
    
    start_date_from = django_filters.DateFilter(field_name='start_date', lookup_expr='gte')
    start_date_to = django_filters.DateFilter(field_name='start_date', lookup_expr='lte')
    end_date_from = django_filters.DateFilter(field_name='end_date', lookup_expr='gte')
    end_date_to = django_filters.DateFilter(field_name='end_date', lookup_expr='lte')
    
    balance_min = django_filters.NumberFilter(field_name='balance', lookup_expr='gte')
    balance_max = django_filters.NumberFilter(field_name='balance', lookup_expr='lte')
    
    currency = django_filters.NumberFilter(field_name='currency')
    
    is_current = django_filters.BooleanFilter(method='filter_is_current')

    class Meta:
        model = Member
        fields = ['status']

    def filter_is_current(self, queryset, name, value):
        from django.utils import timezone
        today = timezone.now().date()
        
        if value:
            return queryset.filter(
                Q(end_date__isnull=True)|Q(end_date__gte=today),
                start_date__lte=today,
            )
        else:
            return queryset.filter(
                Q(start_date__gt=today) | Q(end_date__lt=today)
            )