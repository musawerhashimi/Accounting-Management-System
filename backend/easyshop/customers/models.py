from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from core.models import TenantBaseModel, Currency
from accounts.models import Employee, User

from core.threads import get_current_tenant
from customers.utils import customer_image_path
from finance.models import CashDrawer

from django.utils import timezone



class Customer(TenantBaseModel):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    ]
    
    CUSTOMER_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('business', 'Business'),
        ('wholesale', 'Wholesale'),
        ('retail', 'Retail'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('blacklisted', 'Blacklisted'),
    ]

    customer_number = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE_CHOICES, default='individual')
    
    discount_percentage = models.FloatField(
        default=0.0, 
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    tax_exempt = models.BooleanField(default=False)
    balance = models.DecimalField(max_digits=15, decimal_places=9, default=Decimal('0.00'))
    date_joined = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
    notes = models.TextField(blank=True, null=True)
    photo = models.ImageField(
        upload_to=customer_image_path,  # <--- Use the function here
        blank=True,
        null=True,
        help_text="Customer image"
    )
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_customers'
    )
    preferred_currency = models.ForeignKey(
        Currency,
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        default=Currency.get_base_currency,
        related_name='preferred_by_customers'
    )
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    class Meta:
        db_table = 'customers'
        indexes = [
            models.Index(fields=['tenant', 'customer_number']),
            models.Index(fields=['tenant', 'name']),
        ]
        unique_together = [
            ['tenant', 'customer_number'],
            ['tenant', 'email'],
            ['tenant', 'name']
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.customer_number})"

    def clean(self):
        super().clean()
        if self.email and Customer.objects.filter(
            tenant=get_current_tenant(), 
            email=self.email
        ).exclude(pk=self.pk).exists():
            raise ValidationError({'email': 'Customer with this email already exists.'})

    def save(self, *args, **kwargs):
        if not self.customer_number:
            self.customer_number = self.generate_customer_number()
        self.full_clean()
        super().save(*args, **kwargs)

    def generate_customer_number(self):
        """Generate unique customer number"""
        tenant = get_current_tenant()
        if not tenant:
            raise ValueError("Tenant is required to generate customer number")
        
        # Get the last customer number for this tenant
        last_customer = Customer.objects.filter(tenant=tenant).order_by('-id').first()
        if last_customer and last_customer.customer_number:
            try:
                # Extract numeric part from customer number (assuming format like CUS-001, CUST-001, etc.)
                parts = last_customer.customer_number.split('-')
                if len(parts) >= 2 and parts[-1].isdigit():
                    next_num = int(parts[-1]) + 1
                    return f"CUS-{next_num:06d}"
            except (ValueError, IndexError):
                pass
        
        # Default starting number
        return f"CUS-{1:06d}"


    @property
    def available_credit(self):
        """Calculate available credit limit"""
        return max(Decimal('0.00'), self.credit_limit - abs(self.balance))

    @property
    def is_over_credit_limit(self):
        """Check if customer is over credit limit"""
        return self.balance < 0 and abs(self.balance) > self.credit_limit

    def get_total_purchases(self):
        """Get total purchase amount for this customer"""
        from sales.models import Sale
        total = Sale.objects.filter(
            customer=self, 
            status='completed'
        ).aggregate(
            total=models.Sum('total_amount')
        )['total']
        return total or Decimal('0.00')

    def get_purchase_count(self):
        """Get total number of purchases"""
        from sales.models import Sale
        return Sale.objects.filter(customer=self, status='completed').count()

    def get_last_purchase_date(self):
        """Get date of last purchase"""
        from sales.models import Sale
        last_sale = Sale.objects.filter(
            customer=self, 
            status='completed'
        ).order_by('-sale_date').first()
        return last_sale.sale_date if last_sale else None

    def update_balance(self, amount):
        """Update customer balance"""
        self.balance += amount
        self.save(update_fields=['balance', 'updated_at'])



from sales.models import Sales
class CustomerStatement(TenantBaseModel):
    """Payment records for sales, purchases, expenses"""
    STATEMENT_TYPES = [
        ('cash', 'Cash'),
        ('loan', 'Loan'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="statements")
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    statement_type = models.CharField(max_length=20, choices=STATEMENT_TYPES)
    statement_date = models.DateTimeField(default=timezone.now)
    sale = models.ForeignKey(Sales, null=True, blank=True, on_delete=models.SET_NULL)
    cash_drawer = models.ForeignKey(CashDrawer, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_customer_statement')

    class Meta:
        db_table = 'customer_statements'
        indexes = [
            models.Index(fields=['tenant', 'statement_date']),
            models.Index(fields=['tenant', 'sale']),
        ]
        ordering=['-statement_date']

    def __str__(self):
        return f"{self.amount} {self.currency.code}"

