from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from core.models import TenantBaseModel
from customers.models import Customer
from inventory.models import Inventory, Location, ProductBatch
from catalog.models import Product, ProductVariant
from core.models import Currency
from accounts.models import User
from django.utils import timezone

class Sales(TenantBaseModel):
    """Sales/Orders model"""
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]
    
    sale_number = models.CharField(max_length=50)
    receipt_id = models.CharField(max_length=200)
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.PROTECT, 
        related_name='sales',
        null=True, 
        blank=True,
    )
    
    sale_date = models.DateTimeField(default=timezone.now)
    subtotal = models.DecimalField(
        max_digits=15, 
        decimal_places=4,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=4, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=4, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00')
    )
    currency = models.ForeignKey(
        Currency, 
        on_delete=models.PROTECT, 
        related_name='sales'
    )
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='pending',
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='completed',
    )
    notes = models.TextField(blank=True)
    created_by_user = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='created_sales'
    )
    
    class Meta:
        db_table = 'sales'
        ordering = ['-sale_date', '-created_at']
        unique_together = [
            ['tenant', 'receipt_id'],
            ['tenant', 'sale_number']            
        ]
        indexes = [
            models.Index(fields=['tenant', 'sale_date']),
            models.Index(fields=['tenant', 'customer']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'receipt_id']),
            models.Index(fields=['tenant', 'payment_status']),
            models.Index(fields=['tenant', 'sale_number']),
        ]
    
    def __str__(self):
        return f"Sale {self.sale_number}"
    
    @property
    def paid_amount(self):
        """Calculate total paid amount from payments"""
        from finance.models import Payment
        
        payments = Payment.objects.filter(
            tenant=self.tenant,
            reference_type='sale',
            reference_id=self.id
        )
        paid = 0
        
        for payment in payments:
            p = self.currency.convert_from(payment.amount, payment.currency_id)
            # p_base = payment.amount / payment.currency.exchange_rate
            # p = p_base * self.currency.exchange_rate
            paid += p
        return paid

    @property
    def balance_due(self):
        """Calculate remaining balance"""
        return self.total_amount - self.paid_amount
    
    def can_be_returned(self):
        """Check if sale can be returned"""
        return self.status in ['completed'] and self.payment_status != 'cancelled'
    
    def update_payment_status(self):
        """Update payment status based on payments"""
        paid = self.paid_amount
        if paid <= 0:
            self.payment_status = 'pending'
        elif paid >= self.total_amount:
            self.payment_status = 'paid'
        else:
            self.payment_status = 'partial'
        self.save(update_fields=['payment_status'])


class SaleItem(models.Model):
    """Individual items in a sale"""
    
    sale = models.ForeignKey(
        Sales, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    inventory = models.ForeignKey(
        Inventory, 
        on_delete=models.PROTECT, 
        related_name='sale_items'
    )
    
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))]
    )
    unit_price = models.DecimalField(
        max_digits=15, 
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    line_total = models.DecimalField(
        max_digits=15, 
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=4, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sale_items'
        indexes = [
            models.Index(fields=['sale']),
            models.Index(fields=['inventory']),
        ]
    
    def __str__(self):
        return f"{self.variant.variant_name} - {self.quantity} @ {self.unit_price}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate line_total on save"""
        self.line_total = (self.quantity * self.unit_price) - self.discount_amount
        super().save(*args, **kwargs)


class Returns(TenantBaseModel):
    """Product returns model"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
        ('cancelled', 'Cancelled'),
    ]
    
    REASON_CHOICES = [
        ('defective', 'Defective Product'),
        ('wrong_item', 'Wrong Item'),
        ('damaged', 'Damaged in Transit'),
        ('not_satisfied', 'Customer Not Satisfied'),
        ('duplicate', 'Duplicate Order'),
        ('other', 'Other'),
    ]
    
    return_number = models.CharField(max_length=50, unique=True, db_index=True)
    original_sale = models.ForeignKey(
        Sales, 
        on_delete=models.PROTECT, 
        related_name='returns'
    )
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.PROTECT, 
        related_name='returns',
        null=True, 
        blank=True
    )
    return_date = models.DateTimeField(db_index=True)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    total_refund_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.ForeignKey(
        Currency, 
        on_delete=models.PROTECT, 
        related_name='returns'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        db_index=True
    )
    processed_by_user = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='processed_returns',
        null=True, 
        blank=True
    )
    
    class Meta:
        db_table = 'returns'
        ordering = ['-return_date', '-created_at']
        indexes = [
            models.Index(fields=['tenant', 'return_date']),
            models.Index(fields=['tenant', 'customer']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['return_number']),
        ]
    
    def __str__(self):
        return f"Return {self.return_number}"
    
    @property
    def total_items(self):
        """Get total number of items being returned"""
        return self.items.aggregate(
            total=models.Sum('quantity_returned')
        )['total'] or 0


class ReturnItem(models.Model):
    """Individual items in a return"""
    
    CONDITION_CHOICES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged'),
    ]
    
    return_order = models.ForeignKey(
        Returns, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    sale_item = models.ForeignKey(
        SaleItem, 
        on_delete=models.PROTECT, 
        related_name='return_items'
    )
    variant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.PROTECT, 
        related_name='return_items'
    )
    batch = models.ForeignKey(
        ProductBatch, 
        on_delete=models.PROTECT, 
        related_name='return_items',
        null=True, 
        blank=True
    )
    quantity_returned = models.DecimalField(
        max_digits=10, 
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))]
    )
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    refund_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    restocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'return_items'
        indexes = [
            models.Index(fields=['return_order']),
            models.Index(fields=['variant']),
        ]
    
    def __str__(self):
        return f"Return: {self.variant.variant_name} - {self.quantity_returned}"