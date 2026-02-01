from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from core.models import TenantBaseModel, BaseModel, Currency
from catalog.models import ProductVariant
from accounts.models import User, Employee


class Location(TenantBaseModel):
    LOCATION_TYPES = [
        ('warehouse', 'Warehouse'),
        ('store', 'Store'),
        ('office', 'Office'),
        ('online', 'Online'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=150)
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES, default='warehouse')
    is_active = models.BooleanField(default=True)
    manager = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='managed_locations'
    )
    created_by_user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_locations'
    )

    class Meta:
        db_table = 'locations'
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['tenant', 'location_type']),
        ]
        unique_together = ['tenant', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"


class ProductBatch(TenantBaseModel):
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='batches'
    )
    batch_number = models.CharField(max_length=50, null=True, blank=True)
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField()
    supplier_batch_ref = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    from django.utils import timezone
    class Meta:
        db_table = 'product_batches'
        indexes = [
            models.Index(fields=['tenant', 'variant', 'is_active']),
            models.Index(fields=['tenant', 'batch_number']),
            models.Index(fields=['tenant', 'expiry_date']),
        ]
        unique_together = ['tenant', 'variant', 'batch_number']

    def __str__(self):
        return f"{self.variant.variant_name} - Batch {self.batch_number}"
    

    @property
    def is_expired(self):
        if self.expiry_date:
            from django.utils import timezone
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def days_until_expiry(self):
        if self.expiry_date:
            from django.utils import timezone
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None


class Inventory(TenantBaseModel):
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='inventory_records'
    )
    batch = models.ForeignKey(
        ProductBatch,
        on_delete=models.CASCADE,
        related_name='inventory_records',
        null=True,
        blank=True
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='inventory_records'
    )
    quantity_on_hand = models.DecimalField(
        max_digits=15, 
        decimal_places=4, 
        default=Decimal('0.0000'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    reserved_quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=4, 
        default=Decimal('0.0000'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    reorder_level = models.DecimalField(
        max_digits=15, 
        decimal_places=4, 
        default=Decimal('10.0000'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    last_counted_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'inventory'
        indexes = [
            models.Index(fields=['tenant', 'variant', 'location']),
            models.Index(fields=['tenant', 'location']),
            models.Index(fields=['quantity_on_hand']),
            models.Index(fields=['reserved_quantity']),
        ]
        unique_together = ['tenant', 'variant', 'batch', 'location']

    def __str__(self):
        batch_info = f" (Batch: {self.batch.batch_number})" if self.batch else ""
        return f"{self.variant.variant_name}{batch_info} @ {self.location.name}: {self.quantity_on_hand}"

    @property
    def available_quantity(self):
        return self.quantity_on_hand - self.reserved_quantity

    @property
    def needs_reorder(self):
        return self.available_quantity <= self.reorder_level

    def reserve_quantity(self, quantity):
        """Reserve quantity for pending orders"""
        if self.available_quantity >= quantity:
            self.reserved_quantity += quantity
            self.save(update_fields=['reserved_quantity', 'updated_at'])
            return True
        return False

    def release_reservation(self, quantity):
        """Release reserved quantity"""
        if self.reserved_quantity >= quantity:
            self.reserved_quantity -= quantity
            self.save(update_fields=['reserved_quantity', 'updated_at'])
            return True
        return False


class StockMovement(TenantBaseModel):
    MOVEMENT_TYPES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('transfer', 'Transfer'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
        ('loss', 'Loss'),
        ('damage', 'Damage'),
        ('sale', 'Sale'),
        ('purchase', 'Purchase'),
    ]

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='stock_movements'
    )
    batch = models.ForeignKey(
        ProductBatch,
        on_delete=models.CASCADE,
        related_name='stock_movements',
        null=True,
        blank=True
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='stock_movements'
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=4,
        help_text="Positive for IN movements, negative for OUT movements"
    )
    reference_type = models.CharField(max_length=50, blank=True)  # 'sale', 'purchase', 'adjustment', etc.
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_stock_movements'
    )

    class Meta:
        db_table = 'stock_movements'
        indexes = [
            models.Index(fields=['tenant', 'variant', 'location']),
            models.Index(fields=['tenant', 'movement_type']),
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]

    def __str__(self):
        return f"{self.get_movement_type_display()}: {self.quantity} {self.variant.variant_name}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Update inventory automatically
            self.update_inventory()

    def update_inventory(self):
        """Update inventory record based on this movement"""
        try:
            inventory, created = Inventory.objects.get_or_create(
                tenant=self.tenant,
                variant=self.variant,
                batch=self.batch,
                location=self.location,
                defaults={'quantity_on_hand': Decimal('0')}
            )
            
            inventory.quantity_on_hand += self.quantity
            inventory.save(update_fields=['quantity_on_hand', 'updated_at'])
            
        except Exception as e:
            # Log error but don't fail the movement creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to update inventory for movement {self.id}: {e}")


class InventoryAdjustment(TenantBaseModel):
    ADJUSTMENT_REASONS = [
        ('count_variance', 'Physical Count Variance'),
        ('damage', 'Damage'),
        ('loss', 'Loss/Theft'),
        ('expiry', 'Expiry'),
        ('return_to_vendor', 'Return to Vendor'),
        ('promotion', 'Promotional Give-away'),
        ('sample', 'Sample'),
        ('correction', 'Data Correction'),
        ('other', 'Other'),
    ]

    adjustment_number = models.CharField(max_length=50, unique=True)
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='adjustments'
    )
    batch = models.ForeignKey(
        ProductBatch,
        on_delete=models.CASCADE,
        related_name='adjustments',
        null=True,
        blank=True
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='adjustments'
    )
    adjustment_quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=4,
        help_text="Positive for increases, negative for decreases"
    )
    reason = models.CharField(max_length=30, choices=ADJUSTMENT_REASONS)
    cost_impact = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Financial impact of the adjustment"
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name='inventory_adjustments'
    )
    notes = models.TextField(blank=True)
    approved_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_adjustments'
    )
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_adjustments'
    )
    adjustment_date = models.DateTimeField()

    class Meta:
        db_table = 'inventory_adjustments'
        indexes = [
            models.Index(fields=['tenant', 'adjustment_number']),
            models.Index(fields=['tenant', 'variant', 'location']),
            models.Index(fields=['tenant', 'adjustment_date']),
            models.Index(fields=['tenant', 'reason']),
        ]

    def __str__(self):
        return f"Adjustment {self.adjustment_number}: {self.adjustment_quantity} {self.variant.variant_name}"

    def save(self, *args, **kwargs):
        if not self.adjustment_number:
            self.adjustment_number = self.generate_adjustment_number()
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and self.approved_by_user:
            # Create stock movement
            self.create_stock_movement()

    def generate_adjustment_number(self):
        """Generate unique adjustment number"""
        from django.utils import timezone
        date_str = timezone.now().strftime('%Y%m%d')
        tenant_prefix = self.tenant.name[:3].upper() if self.tenant else 'SYS'
        
        # Get the last adjustment for today
        last_adjustment = InventoryAdjustment.objects.filter(
            tenant=self.tenant,
            adjustment_number__startswith=f"ADJ-{tenant_prefix}-{date_str}"
        ).order_by('-adjustment_number').first()
        
        if last_adjustment:
            try:
                last_num = int(last_adjustment.adjustment_number.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
            
        return f"ADJ-{tenant_prefix}-{date_str}-{next_num:04d}"

    def create_stock_movement(self):
        """Create corresponding stock movement"""
        StockMovement.objects.create(
            tenant=self.tenant,
            variant=self.variant,
            batch=self.batch,
            location=self.location,
            movement_type='adjustment',
            quantity=self.adjustment_quantity,
            reference_type='adjustment',
            reference_id=self.id,
            notes=f"Adjustment: {self.get_reason_display()}",
            created_by_user=self.created_by_user
        )


class InventoryCount(TenantBaseModel):
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    count_number = models.CharField(max_length=50, unique=True)
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='inventory_counts'
    )
    count_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    total_items_counted = models.PositiveIntegerField(default=0)
    variances_found = models.PositiveIntegerField(default=0)
    created_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_counts'
    )
    completed_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_counts'
    )

    class Meta:
        db_table = 'inventory_counts'
        indexes = [
            models.Index(fields=['tenant', 'location', 'status']),
            models.Index(fields=['tenant', 'count_date']),
            models.Index(fields=['tenant', 'count_number']),
        ]

    def __str__(self):
        return f"Count {self.count_number} - {self.location.name}"

    def save(self, *args, **kwargs):
        if not self.count_number:
            self.count_number = self.generate_count_number()
        super().save(*args, **kwargs)

    def generate_count_number(self):
        """Generate unique count number"""
        from django.utils import timezone
        date_str = timezone.now().strftime('%Y%m%d')
        tenant_prefix = self.tenant.name[:3].upper() if self.tenant else 'SYS'
        
        # Get the last count for today
        last_count = InventoryCount.objects.filter(
            tenant=self.tenant,
            count_number__startswith=f"CNT-{tenant_prefix}-{date_str}"
        ).order_by('-count_number').first()
        
        if last_count:
            try:
                last_num = int(last_count.count_number.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
            
        return f"CNT-{tenant_prefix}-{date_str}-{next_num:04d}"

    def complete_count(self, user):
        """Complete the inventory count and create adjustments for variances"""
        if self.status != 'in_progress':
            raise ValueError("Count must be in progress to complete")
        
        variances = self.count_items.filter(variance__ne=0)
        
        for item in variances:
            if item.variance != 0:
                # Create adjustment for variance
                InventoryAdjustment.objects.create(
                    tenant=self.tenant,
                    variant=item.variant,
                    batch=item.batch,
                    location=self.location,
                    adjustment_quantity=item.variance,
                    reason='count_variance',
                    cost_impact=item.variance * (item.variant.final_cost_price or 0),
                    currency=self.tenant.currencies.filter(is_base_currency=True).first(),
                    notes=f"Physical count variance - Count #{self.count_number}",
                    approved_by_user=user,
                    created_by_user=user,
                    adjustment_date=self.count_date
                )
        
        self.status = 'completed'
        self.completed_by_user = user
        self.variances_found = variances.count()
        self.save(update_fields=['status', 'completed_by_user', 'variances_found', 'updated_at'])


class InventoryCountItem(BaseModel):
    count = models.ForeignKey(
        InventoryCount,
        on_delete=models.CASCADE,
        related_name='count_items'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='count_items'
    )
    batch = models.ForeignKey(
        ProductBatch,
        on_delete=models.CASCADE,
        related_name='count_items',
        null=True,
        blank=True
    )
    system_quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=4,
        help_text="Quantity per system records"
    )
    counted_quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=4,
        help_text="Actual counted quantity"
    )
    variance = models.DecimalField(
        max_digits=15, 
        decimal_places=4,
        help_text="Difference between counted and system quantity"
    )
    notes = models.TextField(blank=True)
    counted_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='counted_items'
    )

    class Meta:
        db_table = 'inventory_count_items'
        indexes = [
            models.Index(fields=['count', 'variant']),
            models.Index(fields=['variance']),
        ]
        unique_together = ['count', 'variant', 'batch']

    def __str__(self):
        return f"{self.variant.variant_name}: {self.counted_quantity} (vs {self.system_quantity})"

    def save(self, *args, **kwargs):
        # Calculate variance
        self.variance = self.counted_quantity - self.system_quantity
        super().save(*args, **kwargs)
        
        # Update count totals
        self.count.total_items_counted = self.count.count_items.count()
        self.count.save(update_fields=['total_items_counted', 'updated_at'])