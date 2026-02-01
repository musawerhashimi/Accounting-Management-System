from rest_framework import serializers
from django.db import transaction, models
from django.utils import timezone
from accounts.models import Employee
from .models import EmployeePosition, EmployeeCareer, Member


class EmployeePositionSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    active_employees_count = serializers.SerializerMethodField()

    class Meta:
        model = EmployeePosition
        fields = [
            'id', 'position_name', 'department', 'department_name',
            'base_salary', 'currency', 'currency_code', 'currency_symbol',
            'description', 'is_active', 'active_employees_count',
            'created_at', 'updated_at'
        ]

    def get_active_employees_count(self, obj):
        return obj.careers.filter(status='active', end_date__isnull=True).count()


class EmployeePositionListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    active_employees_count = serializers.SerializerMethodField()

    class Meta:
        model = EmployeePosition
        fields = [
            'id', 'position_name', 'department_name', 'base_salary',
            'currency_code', 'is_active', 'active_employees_count'
        ]

    def get_active_employees_count(self, obj):
        return obj.careers.filter(status='active', end_date__isnull=True).count()


class EmployeeCareerSerializer(serializers.ModelSerializer):
    position_name = serializers.CharField(source='position.position_name', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    created_by_user_name = serializers.CharField(source='created_by_user.get_full_name', read_only=True)
    duration_days = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeCareer
        fields = [
            'id', 'employee', 'position', 'position_name',
            'start_date', 'end_date', 'salary', 'currency',
            'currency_code', 'currency_symbol', 'status', 'notes',
            'created_by_user', 'created_by_user_name', 'duration_days',
            'created_at', 'updated_at'
        ]

    def get_duration_days(self, obj):
        end_date = obj.end_date or timezone.now().date()
        return (end_date - obj.start_date).days

    def validate(self, data):
        if data.get('end_date') and data.get('start_date'):
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError("Start date cannot be after end date")
        return data


class EmployeeSerializer(serializers.ModelSerializer):
    current_position = serializers.SerializerMethodField()
    current_salary = serializers.SerializerMethodField()
    current_currency = serializers.SerializerMethodField()
    careers_count = serializers.SerializerMethodField()
    created_by_user_name = serializers.CharField(source='created_by_user.get_full_name', read_only=True)
    service_years = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'phone', 'email',
            'hire_date', 'status', 'balance', 'current_position',
            'current_salary', 'current_currency', 'careers_count',
            'service_years', 'created_by_user', 'created_by_user_name',
            'created_at', 'updated_at'
        ]

    def get_current_position(self, obj):
        career = obj.current_position
        return career.position.position_name if career else None

    def get_current_salary(self, obj):
        return obj.current_salary

    def get_current_currency(self, obj):
        career = obj.current_position
        return career.currency.code if career else None

    def get_careers_count(self, obj):
        return obj.careers.count()

    def get_service_years(self, obj):
        today = timezone.now().date()
        years = (today - obj.hire_date).days / 365.25
        return round(years, 1)


class EmployeeListSerializer(serializers.ModelSerializer):
    current_position = serializers.SerializerMethodField()
    current_salary = serializers.SerializerMethodField()
    service_years = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'phone', 'email',
            'hire_date', 'status', 'current_position', 'current_salary',
            'service_years'
        ]

    def get_current_position(self, obj):
        career = obj.current_position
        return career.position.position_name if career else None

    def get_current_salary(self, obj):
        return obj.current_salary

    def get_service_years(self, obj):
        today = timezone.now().date()
        years = (today - obj.hire_date).days / 365.25
        return round(years, 1)


class EmployeeCreateUpdateSerializer(serializers.ModelSerializer):
    # position_id = serializers.IntegerField(write_only=True, required=False)
    # salary = serializers.DecimalField(max_digits=15, decimal_places=2, write_only=True, required=False)
    # currency_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Employee
        fields = [
            'name', 'phone', 'email', # 'hire_date',
            # 'status', 'balance', 'position_id', 'salary', 'currency_id'
        ]

    @transaction.atomic
    def create(self, validated_data):
        # position_id = validated_data.pop('position_id', None)
        # salary = validated_data.pop('salary', None)
        # currency_id = validated_data.pop('currency_id', None)

        employee = Employee.objects.create(**validated_data)

        # Create initial career if position data provided
        # if position_id and salary and currency_id:
        #     EmployeeCareer.objects.create(
        #         employee=employee,
        #         position_id=position_id,
        #         start_date=employee.hire_date,
        #         salary=salary,
        #         currency_id=currency_id,
        #         status='active',
        #         created_by_user=self.context['request'].user
        #     )

        return employee


class MemberSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    membership_duration_days = serializers.SerializerMethodField()
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            'id', 'name', 'ownership_percentage', 'investment_amount',
            'currency', 'currency_code', 'currency_symbol',
            'start_date', 'end_date', 'balance',
            'status', 'membership_duration_days',
            'is_current', 'created_at', 'updated_at'
        ]

    def get_membership_duration_days(self, obj):
        end_date = obj.end_date or timezone.now().date()
        return (end_date - obj.start_date).days

    def get_is_current(self, obj):
        today = timezone.now().date()
        return obj.start_date <= today and (obj.end_date is None or obj.end_date >= today)

    def validate(self, data):
        if data.get('end_date') and data.get('start_date'):
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError("Start date cannot be after end date")
        return data

    def validate_ownership_percentage(self, value):
        # Check total ownership doesn't exceed 100%
        tenant = self.context['request'].tenant
        total_ownership = Member.objects.filter(
            tenant=tenant,
            status='active'
        ).exclude(
            id=self.instance.id if self.instance else None
        ).aggregate(
            total=models.Sum('ownership_percentage')
        )['total'] or 0

        if total_ownership + value > 100:
            raise serializers.ValidationError("Total ownership cannot exceed 100%")
        return value


class MemberListSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            'id', 'name', 'ownership_percentage', 'investment_amount',
            'currency_code', 'status', 'is_current'
        ]

    def get_is_current(self, obj):
        today = timezone.now().date()
        return obj.start_date <= today and (obj.end_date is None or obj.end_date >= today)


# Stats Serializers
class EmployeeStatsSerializer(serializers.Serializer):
    total_employees = serializers.IntegerField()
    active_employees = serializers.IntegerField()
    inactive_employees = serializers.IntegerField()
    total_positions = serializers.IntegerField()
    avg_salary = serializers.DecimalField(max_digits=15, decimal_places=2)
    avg_service_years = serializers.FloatField()