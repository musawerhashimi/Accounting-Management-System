from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from core.models import TenantBaseModel, Currency
from core.threads import get_current_tenant
from vendors.models import Vendor
from accounts.models import User
from inventory.models import Location


class CashDrawer(TenantBaseModel):
    """Cash drawers for different locations"""
    name = models.CharField(max_length=100)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='cash_drawers')
    description = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_cash_drawers')

    class Meta:
        db_table = 'cash_drawers'
        unique_together = ['tenant', 'name', 'location']
        indexes = [
            models.Index(fields=['tenant', 'location']),
            models.Index(fields=['tenant', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {self.location.name}"

    @property
    def total_balance(self):
        """Calculate total balance across all currencies"""
        base_currency_id = Currency.get_base_currency().id

        
        return sum(
            Currency.convert_to_base_currency(
                money.amount, money.currency_id
        ) for money in self.cash_drawer_money.all()
        )

    def get_balance_by_currency(self, currency):
        """Get balance for specific currency"""
        try:
            money = self.cash_drawer_money.get(currency=currency)
            return money.amount
        except CashDrawerMoney.DoesNotExist:
            return Decimal('0.00')


class CashDrawerMoney(models.Model):
    """Money in each cash drawer by currency"""
    cash_drawer = models.ForeignKey(CashDrawer, on_delete=models.CASCADE, related_name='cash_drawer_money')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    last_counted_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'cash_drawer_money'
        unique_together = ['cash_drawer', 'currency']
        indexes = [
            models.Index(fields=['cash_drawer', 'currency']),
        ]

    def __str__(self):
        return f"{self.cash_drawer.name} - {self.currency.code}: {self.amount}"


class Payment(TenantBaseModel):
    """Payment records for sales, purchases, expenses"""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
        ('check', 'Check'),
        ('other', 'Other'),
    ]
    
    REFERENCE_TYPES = [
        ('sale', 'Sale'),
        ('purchase', 'Purchase'),
        ('expense', 'Expense'),
        ('salary', 'Salary'),
        ('dividend', 'Dividend'),
        ('loan', 'Loan'),
        ('other', 'Other'),
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('employee', 'Employee'),
        ('member', 'Member'),
        ('customer_statement', 'Customer Statement'),
    ]
    
    payment_number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_date = models.DateTimeField(default=timezone.now)
    reference_type = models.CharField(max_length=20, choices=REFERENCE_TYPES)
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    cash_drawer = models.ForeignKey(CashDrawer, on_delete=models.SET_NULL, null=True, blank=True)
    card_transaction_id = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_payments')

    class Meta:
        db_table = 'payments'
        indexes = [
            models.Index(fields=['tenant', 'payment_date']),
            models.Index(fields=['tenant', 'reference_type', 'reference_id']),
            models.Index(fields=['tenant', 'payment_method']),
            models.Index(fields=['tenant', 'cash_drawer']),
            models.Index(fields=['payment_number']),
        ]

    def __str__(self):
        return f"{self.payment_number} - {self.amount} {self.currency.code}"

    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        super().save(*args, **kwargs)

    def generate_payment_number(self):
        """Generate unique payment number"""
        tenant = get_current_tenant()
        if not tenant:
            raise ValueError("No tenant context available")
        
        from django.utils import timezone
        date_str = timezone.now().strftime('%Y%m%d')
        
        # Get last payment number for today
        last_payment = Payment.objects.filter(
            tenant=tenant,
            payment_number__startswith=f'PAY-{date_str}'
        ).order_by('-payment_number').first()
        
        if last_payment:
            try:
                last_seq = int(last_payment.payment_number.split('-')[-1])
                new_seq = last_seq + 1
            except (ValueError, IndexError):
                new_seq = 1
        else:
            new_seq = 1
        
        return f'PAY-{date_str}-{new_seq:04d}'


class Transaction(TenantBaseModel):
    """General ledger transactions"""
    TRANSACTION_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('transfer', 'Transfer'),
        ('adjustment', 'Adjustment'),
    ]
    
    REFERENCE_TYPE_CHOICES = [
        ('sale', 'Sale'),
        ('purchase', 'Purchase'),
        ('expense', 'Expense'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
        ('customer_statement', 'Customer Statement'),
        ('other', 'Other'),
    ]
    
    PARTY_TYPES = [
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('employee', 'Employee'),
        ('member', 'Member'),
        ('other', 'Other'),
    ]
    
    transaction_date = models.DateTimeField(default=timezone.now)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    description = models.CharField(max_length=255, null=True, blank=True)
    party_type = models.CharField(max_length=20, choices=PARTY_TYPES, null=True, blank=True)
    party_id = models.PositiveIntegerField(null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    reference_type = models.CharField(max_length=50, choices=REFERENCE_TYPE_CHOICES, default="other")
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    cash_drawer = models.ForeignKey(CashDrawer, on_delete=models.SET_NULL, null=True, blank=True)
    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_direct = models.BooleanField(default=False)

    class Meta:
        db_table = 'transactions'
        indexes = [
            models.Index(fields=['tenant', 'transaction_date']),
            models.Index(fields=['tenant', 'transaction_type']),
            models.Index(fields=['tenant', 'party_type', 'party_id']),
            models.Index(fields=['tenant', 'reference_type', 'reference_id']),
            models.Index(fields=['tenant', 'cash_drawer']),
        ]

    def __str__(self):
        return f"{self.description} - {self.amount} {self.currency.code}"


class ExpenseCategory(TenantBaseModel):
    """Categories for organizing expenses"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'expense_categories'
        unique_together = ['tenant', 'name', 'parent_category']
        indexes = [
            models.Index(fields=['tenant', 'parent_category']),
        ]

    def __str__(self):
        if self.parent_category:
            return f"{self.parent_category.name} > {self.name}"
        return self.name

    @property
    def full_path(self):
        """Get full category path"""
        if self.parent_category:
            return f"{self.parent_category.full_path} > {self.name}"
        return self.name


class Expense(TenantBaseModel):
    """Business expense records"""
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('other', 'Other'),
    ]
    
    expense_number = models.CharField(max_length=50)
    expense_category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name='expenses')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    expense_date = models.DateTimeField(default=timezone.now)
    cash_drawer = models.ForeignKey(CashDrawer, on_delete=models.CASCADE, related_name="paid_expenses")
    description = models.TextField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="cash")
    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_expenses')

    class Meta:
        db_table = 'expenses'
        unique_together = ['tenant', 'expense_number']
        indexes = [
            models.Index(fields=['tenant', 'expense_date']),
            models.Index(fields=['tenant', 'expense_category']),
        ]

    def __str__(self):
        return f"{self.expense_number} - {self.description[:50]}"

    def save(self, *args, **kwargs):
        if not self.expense_number:
            self.expense_number = self.generate_expense_number()
        super().save(*args, **kwargs)

    def generate_expense_number(self):
        """Generate unique expense number"""
        tenant = get_current_tenant()
        if not tenant:
            raise ValueError("No tenant context available")
        
        from django.utils import timezone
        date_str = timezone.now().strftime('%Y%m%d')
        # Get last expense number for today
        last_expense = Expense.all_objects.filter(
            tenant=tenant,
            expense_number__startswith=f'EXP-{date_str}'
        ).order_by('-expense_number').first()
        if last_expense:
            try:
                last_seq = int(last_expense.expense_number.split('-')[-1])
                new_seq = last_seq + 1
            except (ValueError, IndexError):
                new_seq = 1
        else:
            new_seq = 1

        return f'EXP-{date_str}-{new_seq:04d}'


class MonthlyPayment(TenantBaseModel):
    """Recurring monthly payments like rent, utilities, etc."""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('auto_debit', 'Auto Debit'),
        ('check', 'Check'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    payment_day = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)], default=1)
    reference_type = models.CharField(max_length=20, choices=[
        ('expense_category', 'Expense'),
        ('employee', 'Employee'),
        ('other', 'Other'),
    ], default='expense')
    reference_id = models.PositiveIntegerField(null=True, blank=True)  # e.g. employee ID if applicable
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'monthly_payments'
        unique_together = ['tenant', 'name']
        indexes = [
            models.Index(fields=['tenant', 'start_date']),
            models.Index(fields=['tenant', 'payment_day']),
            models.Index(fields=['tenant', 'reference_type']),
        ]

    def __str__(self):
        return f"{self.name} - {self.amount} {self.currency.code}"

    def is_due_for_month(self, year, month):
        """Check if payment is due for given month"""
        from datetime import date
        
        if not self.is_active:
            return False
            
        payment_date = date(year, month, min(self.payment_day, 28))  # Avoid issues with Feb 29/30/31
        
        if payment_date < self.start_date:
            return False
            
        if self.end_date and payment_date > self.end_date:
            return False
            
        return True

    def create_expense_for_month(self, year, month, user=None):
        """Create expense record for this monthly payment"""
        from datetime import date
        
        if not self.is_due_for_month(year, month):
            return None
            
        payment_date = date(year, month, min(self.payment_day, 28))
        
        # Check if expense already exists for this month
        existing_expense = Expense.objects.filter(
            tenant=self.tenant,
            description__contains=f"{self.name} - {year}-{month:02d}",
            expense_date=payment_date
        ).first()
        
        if existing_expense:
            return existing_expense
            
        expense = Expense.objects.create(
            tenant=self.tenant,
            expense_category=self.expense_category,
            vendor=self.vendor,
            amount=self.amount,
            currency=self.currency,
            expense_date=payment_date,
            description=f"{self.name} - {year}-{month:02d}",
            payment_method=self.payment_method,
            status='pending',
            created_by_user=user
        )
        
        return expense