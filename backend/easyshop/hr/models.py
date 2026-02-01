from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import TenantBaseModel, Currency
from accounts.models import Employee, User
from catalog.models import Department


class EmployeePosition(TenantBaseModel):
    position_name = models.CharField(max_length=100)
    base_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name='employee_positions'
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'employee_positions'
        unique_together = [['tenant', 'position_name']]
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
        ]

    def __str__(self):
        return f"{self.position_name} - {self.department.name}"


class EmployeeCareer(TenantBaseModel):
    CAREER_STATUS_CHOICES = [
        ('active', 'Active'),
        ('terminated', 'Terminated'),
        ('promoted', 'Promoted'),
        ('transferred', 'Transferred'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='careers'
    )
    position = models.ForeignKey(
        EmployeePosition,
        on_delete=models.CASCADE,
        related_name='careers'
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name='employee_careers'
    )
    status = models.CharField(
        max_length=20,
        choices=CAREER_STATUS_CHOICES,
        default='active'
    )
    notes = models.TextField(blank=True)
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_careers'
    )


    class Meta:
        db_table = 'employee_careers'
        indexes = [
            models.Index(fields=['tenant', 'employee']),
            models.Index(fields=['position']),
            models.Index(fields=['start_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.position.position_name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validate date range
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after end date")


class Member(TenantBaseModel):
    MEMBER_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('withdrawn', 'Withdrawn'),
    ]

    name = models.CharField(max_length=200)
    ownership_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    investment_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name='members'
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=MEMBER_STATUS_CHOICES,
        default='active'
    )


    class Meta:
        db_table = 'members'
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['name']),
            models.Index(fields=['start_date']),
            models.Index(fields=['ownership_percentage']),
        ]

    def __str__(self):
        return f"{self.name} ({self.ownership_percentage}%)"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validate date range
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after end date")