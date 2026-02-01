from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Employee, EmployeePosition, EmployeeCareer, Member


@admin.register(EmployeePosition)
class EmployeePositionAdmin(admin.ModelAdmin):
    list_display = [
        'position_name', 'base_salary', 'currency',
        'active_employees_count', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'currency', 'created_at']
    search_fields = ['position_name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'active_employees_count']
    raw_id_fields = ['currency']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('position_name', 'department', 'description', 'is_active')
        }),
        ('Salary Information', {
            'fields': ('base_salary', 'currency')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at', 'active_employees_count'),
            'classes': ('collapse',)
        }),
    )

    def active_employees_count(self, obj):
        count = obj.careers.filter(status='active', end_date__isnull=True).count()
        if count > 0:
            url = reverse('admin:hr_employee_changelist')
            return format_html(
                '<a href="{}?careers__position__id__exact={}">{} employees</a>',
                url, obj.id, count
            )
        return '0 employees'
    active_employees_count.short_description = 'Active Employees'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'department', 'currency'
        ).prefetch_related('careers')


class EmployeeCareerInline(admin.TabularInline):
    model = EmployeeCareer
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['position', 'currency', 'created_by_user']
    
    fieldsets = (
        (None, {
            'fields': (
                'position', 'start_date', 'end_date', 'salary', 'currency',
                'status', 'notes', 'created_by_user'
            )
        }),
    )


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'current_position_display',
        'current_salary_display', 'status', 'hire_date', 'service_years'
    ]
    list_filter = ['status', 'hire_date', 'created_at']
    search_fields = ['employee_number', 'name', 'phone', 'email']
    readonly_fields = [
        'created_at', 'updated_at', 'current_position_display',
        'current_salary_display', 'service_years', 'careers_count'
    ]
    raw_id_fields = ['created_by_user']
    inlines = [EmployeeCareerInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('employee_number', 'name', 'phone', 'email')
        }),
        ('Employment Information', {
            'fields': ('hire_date', 'status', 'balance')
        }),
        ('Current Position', {
            'fields': ('current_position_display', 'current_salary_display'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('service_years', 'careers_count'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_by_user', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def current_position_display(self, obj):
        career = obj.current_position
        if career:
            return f"{career.position.position_name} ({career.position.department.name})"
        return "No active position"
    current_position_display.short_description = 'Current Position'

    def current_salary_display(self, obj):
        career = obj.current_position
        if career:
            return f"{career.currency.symbol}{career.salary:,.2f}"
        return "N/A"
    current_salary_display.short_description = 'Current Salary'

    def service_years(self, obj):
        from django.utils import timezone
        today = timezone.now().date()
        years = (today - obj.hire_date).days / 365.25
        return f"{years:.1f} years"
    service_years.short_description = 'Service Years'

    def careers_count(self, obj):
        count = obj.careers.count()
        if count > 0:
            url = reverse('admin:hr_employeecareer_changelist')
            return format_html(
                '<a href="{}?employee__id__exact={}">{} careers</a>',
                url, obj.id, count
            )
        return '0 careers'
    careers_count.short_description = 'Career History'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'created_by_user'
        ).prefetch_related(
            'careers__position__department',
            'careers__currency'
        )

    actions = ['terminate_employees', 'activate_employees']

    def terminate_employees(self, request, queryset):
        count = queryset.update(status='terminated')
        self.message_user(request, f'{count} employees terminated.')
    terminate_employees.short_description = 'Terminate selected employees'

    def activate_employees(self, request, queryset):
        count = queryset.update(status='active')
        self.message_user(request, f'{count} employees activated.')
    activate_employees.short_description = 'Activate selected employees'


@admin.register(EmployeeCareer)
class EmployeeCareerAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'position', 'start_date', 'end_date',
        'salary_display', 'status', 'duration_display'
    ]
    list_filter = ['status', 'start_date', 'end_date']
    search_fields = [
        'employee__name', 'employee__employee_number',
        'position__position_name', 'notes'
    ]
    readonly_fields = ['created_at', 'updated_at', 'duration_display']
    raw_id_fields = ['employee', 'position', 'currency', 'created_by_user']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Career Information', {
            'fields': ('employee', 'position', 'start_date', 'end_date', 'status')
        }),
        ('Salary Information', {
            'fields': ('salary', 'currency')
        }),
        ('Additional Information', {
            'fields': ('notes', 'duration_display')
        }),
        ('System Information', {
            'fields': ('created_by_user', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def salary_display(self, obj):
        return f"{obj.currency.symbol}{obj.salary:,.2f}"
    salary_display.short_description = 'Salary'
    salary_display.admin_order_field = 'salary'

    def duration_display(self, obj):
        from django.utils import timezone
        end_date = obj.end_date or timezone.now().date()
        days = (end_date - obj.start_date).days
        
        if days < 30:
            return f"{days} days"
        elif days < 365:
            months = days // 30
            return f"{months} months"
        else:
            years = days / 365.25
            return f"{years:.1f} years"
    duration_display.short_description = 'Duration'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'employee', 'position', 'currency', 'created_by_user'
        )


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'ownership_percentage', 'investment_display',
        'status', 'membership_duration', 'is_current'
    ]
    list_filter = ['status', 'start_date', 'currency']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at', 'membership_duration', 'is_current']
    raw_id_fields = ['currency']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Member Information', {
            'fields': ('name', 'status')
        }),
        ('Ownership & Investment', {
            'fields': (
                'ownership_percentage', 'investment_amount', 'currency',
                'profit_share', 'asset_share'
            )
        }),
        ('Membership Period', {
            'fields': ('start_date', 'end_date', 'membership_duration', 'is_current')
        }),
        ('Financial', {
            'fields': ('balance',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def investment_display(self, obj):
        return f"{obj.currency.symbol}{obj.investment_amount:,.2f}"
    investment_display.short_description = 'Investment'
    investment_display.admin_order_field = 'investment_amount'

    def membership_duration(self, obj):
        from django.utils import timezone
        end_date = obj.end_date or timezone.now().date()
        days = (end_date - obj.start_date).days
        years = days / 365.25
        return f"{years:.1f} years"
    membership_duration.short_description = 'Duration'

    def is_current(self, obj):
        from django.utils import timezone
        today = timezone.now().date()
        is_current = (obj.start_date <= today and 
                     (obj.end_date is None or obj.end_date >= today))
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if is_current else 'red',
            'Yes' if is_current else 'No'
        )
    is_current.short_description = 'Current Member'
    is_current.boolean = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('currency')

    actions = ['withdraw_members', 'activate_members']

    def withdraw_members(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(
            status='withdrawn',
            end_date=timezone.now().date()
        )
        self.message_user(request, f'{count} members withdrawn.')
    withdraw_members.short_description = 'Withdraw selected members'

    def activate_members(self, request, queryset):
        count = queryset.update(status='active', end_date=None)
        self.message_user(request, f'{count} members activated.')
    activate_members.short_description = 'Activate selected members'


# Custom admin site configurations
admin.site.site_header = "HR Management System"
admin.site.site_title = "HR Admin"
admin.site.index_title = "HR Administration"