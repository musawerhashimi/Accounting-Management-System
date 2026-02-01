from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.contenttypes.fields import GenericRelation
from decimal import Decimal
from core.models import TenantBaseModel, Currency, Address
from core.threads import get_current_tenant
from accounts.models import User
from inventory.models import ProductBatch, ProductVariant, Location
from vendors.utils import upload_image_path
from .managers import VendorManager, PurchaseManager
from django.utils import timezone

class Vendor(TenantBaseModel):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]
    
    addresses = GenericRelation(
        to=Address,
        content_type_field='addressable_type',
        object_id_field='addressable_id'
    )
    name = models.CharField(max_length=255)
    photo = models.ImageField(
        upload_to=upload_image_path,  # <--- Use the function here
        blank=True,
        null=True,
        help_text="Customer image"
    )
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    tax_id = models.CharField(max_length=50, blank=True)
    balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_by_user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_vendors'
    )
    
    objects = VendorManager()
    
    class Meta:
        db_table = 'vendors'
        ordering = ['name']
        unique_together = ['tenant', 'name']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'name']),
            models.Index(fields=['tenant', 'email']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def total_purchases(self):
        return self.purchases.aggregate(
            total=models.Sum('total_amount')
        )['total'] or Decimal('0.00')
    
    @property
    def pending_purchases(self):
        return self.purchases.filter(status='pending').count()


class Purchase(TenantBaseModel):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('partially_received', 'Partially Received'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
        ('closed', 'Closed'),
    ]
    
    purchase_number = models.CharField(max_length=100, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='purchases')
    location = models.ForeignKey(
        Location, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchases'
    )
    purchase_date = models.DateTimeField(default=timezone.now)
    delivery_date = models.DateTimeField(null=True, blank=True)
    subtotal = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)
    created_by_user = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='created_purchases'
    )
    
    objects = PurchaseManager()
    
    class Meta:
        db_table = 'purchases'
        ordering = ['-purchase_date']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'purchase_date']),
            models.Index(fields=['tenant', 'vendor']),
            models.Index(fields=['purchase_number']),
        ]
    
    def __str__(self):
        return f"{self.purchase_number} - {self.vendor.name}"
    
    def save(self, *args, **kwargs):
        if not self.purchase_number:
            self.purchase_number = self.generate_purchase_number()
        super().save(*args, **kwargs)
    
    def generate_purchase_number(self):
        tenant = get_current_tenant()
        if not tenant:
            raise ValueError("Tenant is required to generate purchase number")
        
        last_purchase = Purchase.objects.filter(
            tenant=tenant
        ).order_by('-id').first()
        
        if last_purchase and last_purchase.purchase_number.startswith('PO'):
            try:
                last_number = int(last_purchase.purchase_number[2:])
                return f'PO{last_number + 1:06d}'
            except (ValueError, IndexError):
                pass
        
        return 'PO000001'
    
    @property
    def total_items(self):
        """Total number of different items in purchase"""
        return self.items.count()
    
    @property
    def total_quantity(self):
        """Total quantity of all items"""
        return self.items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
    
    @property
    def received_quantity(self):
        return self.items.aggregate(
            total=models.Sum('received_quantity')
        )['total'] or 0
    
    @property
    def received_percentage(self):
        """Percentage of items received"""
        total_qty = self.total_quantity
        if total_qty == 0:
            return 0
        
        received_qty = self.items.aggregate(
            total=models.Sum('received_quantity')
        )['total'] or Decimal('0')
        
        return float((received_qty / total_qty) * 100)
    
    @property
    def is_fully_received(self):
        """Check if all items are fully received"""
        return self.total_quantity == self.received_quantity
    
    @property
    def is_partially_received(self):
        return 0 < self.received_quantity < self.total_quantity
    
    @property
    def outstanding_amount(self):
        """Calculate outstanding payment amount"""
        paid_amount = self.payments.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        return self.total_amount - paid_amount
    
    def can_be_cancelled(self):
        """Check if purchase can be cancelled"""
        return self.status in ['draft', 'pending', 'ordered'] and self.received_percentage == 0
    
    def can_receive_items(self):
        """Check if items can be received"""
        return self.status in ['ordered', 'approved', 'partially_received']
    
    def update_status(self):
        """Update purchase status based on received quantities"""
        if self.is_fully_received:
            self.status = 'received'
        elif self.is_partially_received:
            self.status = 'partially_received'
        # elif self.status == 'received' or self.status == 'partially_received':
        else:
            self.status = 'pending'
        self.save()
    
    def calculate_totals(self):
        """Recalculate purchase totals based on items"""
        items_total = self.items.aggregate(
            total=models.Sum('line_total')
        )['total'] or Decimal('0.00')
        
        self.subtotal = items_total
        self.total_amount = self.subtotal + self.tax_amount
        self.save()


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.CASCADE, 
        related_name='purchase_items'
    )
    batch = models.ForeignKey(
        ProductBatch, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='purchase_items'
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    unit_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    line_total = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    received_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        default=Decimal('0.000'),
        validators=[MinValueValidator(Decimal('0.000'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'purchase_items'
        indexes = [
            models.Index(fields=['purchase', 'variant']),
        ]
    
    def __str__(self):
        return f"{self.purchase.purchase_number} - {self.variant.product.name}"
    
    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
        # Update purchase totals
        self.purchase.calculate_totals()
        self.purchase.update_status()
    
    @property
    def remaining_quantity(self):
        """Quantity still pending receipt"""
        return self.quantity - self.received_quantity
    
    @property
    def pending_quantity(self):
        """Quantity still pending receipt"""
        return self.remaining_quantity
    
    @property
    def is_fully_received(self):
        return self.received_quantity >= self.quantity
    
    @property
    def receipt_percentage(self):
        """Percentage of item received"""
        if self.quantity == 0:
            return 0
        return float((self.received_quantity / self.quantity) * 100)
    
    def receive_quantity(self, quantity):
        """Receive a specific quantity and update inventory"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if self.received_quantity + quantity > self.quantity:
            raise ValueError("Cannot receive more than ordered quantity")
        
        self.received_quantity += quantity
        self.save()
        
        # Update inventory
        from inventory.models import StockMovement
        
        StockMovement.objects.create(
            tenant=self.purchase.tenant,
            variant=self.variant,
            batch=self.batch,
            location=self.purchase.location,
            movement_type='purchase',
            quantity=quantity,
            reference_type='purchase',
            reference_id=self.purchase.id,
            notes=f"Received from purchase {self.purchase.purchase_number}",
            created_by_user=self.purchase.created_by_user
        )