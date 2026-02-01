from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from accounts.utils import upload_user_photo
from core.models import Tenant, Currency, Permission
from core.base_models import TenantBaseModel, BaseModel
from core.managers import UserManager
from django.contrib.auth.models import UserManager as BaseUserManager

ROLE_CHOICES = [
    ('admin', 'Administrator'),
    ('manager', 'Manager'),
    ('employee', 'Employee'),
    ('cashier', 'Cashier'),
    ('inventory_manager', 'Inventory Manager'),
    ('sales_rep', 'Sales Representative'),
    ('accountant', 'Accountant'),
    ('viewer', 'Viewer'),
]


class Employee(TenantBaseModel):
    EMPLOYEE_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('terminated', 'Terminated'),
        ('on_leave', 'On Leave'),
    ]

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    hire_date = models.DateField(default=timezone.now)
    status = models.CharField(
        max_length=20, 
        choices=EMPLOYEE_STATUS_CHOICES, 
        default='active'
    )
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    created_by_user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_employees'
    )


    class Meta:
        db_table = 'employees'
        indexes = [
            models.Index(fields=['tenant', 'name']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'hire_date']),
        ]

    def __str__(self):
        return self.name

    @property
    def current_position(self):
        return self.careers.filter(
            status='active',
            end_date__isnull=True
        ).first()

    @property
    def current_salary(self):
        current_career = self.current_position
        return current_career.salary if current_career else 0


class User(AbstractUser, BaseModel):
    """Extended user model with tenant support"""
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name='users',
        null=True, blank=True
    )
    photo = models.ImageField(
        upload_to=upload_user_photo, 
        null=True, blank=True,
        help_text="User profile photo"
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    employee = models.OneToOneField(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='user_account'
    )

    role_name = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES, 
    )
    # Preferences
    preferred_currency = models.ForeignKey(
        Currency, 
        on_delete=models.SET_NULL, 
        null=True, blank=True
    )
    location = models.ForeignKey(to='inventory.Location', on_delete=models.PROTECT, related_name='users')
    language_preference = models.CharField(
        max_length=10,
        default='en',
        choices=[
            ('en', 'English'),
            ('da', 'Dari'),
            ('pa', 'Pashto'),
            ('es', 'Spanish'),
            ('fr', 'French'),
            ('de', 'German'),
            ('ar', 'Arabic'),
        ]
    )
    timezone = models.CharField(
        max_length=50, 
        default='UTC',
        help_text="User's timezone preference"
    )
    theme = models.CharField(
        max_length=20,
        default='light',
        choices=[
            ('light', 'Light'),
            ('dark', 'Dark'),
            ('system', 'System Default')
        ]
    )
    
    # Custom manager for tenant awareness
    objects = UserManager()
    all_objects = BaseUserManager()
    

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f"{self.username} ({self.get_full_name()})"

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def soft_delete(self):
        """Soft delete the user"""
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save()

    def restore(self):
        """Restore soft deleted user"""
        self.deleted_at = None
        self.is_active = True
        self.save()


class UserPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="users_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    allow = models.BooleanField(default=True)
    class Meta:
        db_table = 'user_permissions'
        unique_together = ['user', 'permission']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['permission']),
        ]

    
class RolePermission(models.Model):
    """Role-based permissions"""
    
    role_name = models.CharField(max_length=50, choices=ROLE_CHOICES)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        db_table = 'role_permissions'
        unique_together = ['role_name', 'permission']
        indexes = [
            models.Index(fields=['role_name']),
            models.Index(fields=['permission']),
        ]

    def __str__(self):
        return f"{self.get_role_name_display()} - {self.permission.module}"


class UserProductPreference(TenantBaseModel):
    """User preferences for products (favorites, bookmarks, etc.)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_preferences')
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.CASCADE, related_name='user_preferences')
    is_favorite = models.BooleanField(default=False)
    is_bookmarked = models.BooleanField(default=False)
    is_loved = models.BooleanField(default=False)

    class Meta:
        db_table = 'user_product_preferences'
        unique_together = ['user', 'variant', 'tenant']
        indexes = [
            models.Index(fields=['tenant', 'user', 'is_favorite']),
            models.Index(fields=['tenant', 'user', 'is_bookmarked']),
            models.Index(fields=['tenant', 'user', 'is_loved']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.variant.variant_name}"