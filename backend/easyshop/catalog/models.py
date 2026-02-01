from django.db import models
from django.core.validators import MinValueValidator
from core.models import Tenant, TenantBaseModel, BaseModel, Unit, Currency
from core.managers import TenantManager
from accounts.models import User
from .utils import product_image_path


class Department(TenantBaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_departments')
    
    
    class Meta:
        db_table = 'departments'
        unique_together = ['tenant', 'name']
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['tenant', 'name']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name})"

    @property
    def total_products(self):
        return sum(category.total_products for category in self.categories.all())
    
    @property
    def total_quantity(self):
        return sum(category.total_quantity for category in self.categories.all())
        
    
class Category(TenantBaseModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_categories')
    
    
    class Meta:
        db_table = 'categories'
        unique_together = ['tenant', 'department', 'name']
        indexes = [
            models.Index(fields=['tenant', 'department', 'is_active']),
            models.Index(fields=['tenant', 'name']),
        ]
        ordering = ['department__name', 'name']
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return f"{self.department.name} - {self.name}"

    @property
    def total_products(self):
        return ProductVariant.objects.filter(product__category=self).count()
    
    @property
    def total_quantity(self):
        from inventory.models import Inventory
        return Inventory.objects.filter(
            variant__product__category=self
        ).aggregate(
            total=models.Sum('quantity_on_hand')
        )['total'] or 0
        

class Product(TenantBaseModel):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    base_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='products')
    description = models.TextField(blank=True, null=True)
    reorder_level = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    has_variants = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_products')

    class Meta:
        db_table = 'products'
        unique_together = ['tenant', 'name']
        indexes = [
            models.Index(fields=['tenant', 'category']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.category.name})"


class ProductVariant(TenantBaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=100, blank=True, null=True)
    variant_name = models.CharField(max_length=255, null=True, blank=True)
    image = models.ImageField(
        upload_to=product_image_path,  # <--- Use the function here
        blank=True, 
        null=True,
        help_text="Product image"
    )
    barcode = models.CharField(max_length=100)  # New barcode field
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_product_variants')
    
    class Meta:
        db_table = 'product_variants'
        unique_together = [
            ('product', 'variant_name'),
            ('product', 'sku'),
            ('tenant', 'barcode')
        ]
        indexes = [
            models.Index(fields=['product', 'is_active']),
            models.Index(fields=['product', 'is_default']),
            models.Index(fields=['tenant', 'barcode']),
        ]
        ordering = ['-is_default', 'variant_name']
    
    def clean(self):
        if self.is_default:
            from django.core.exceptions import ValidationError
            fields = [
                'variant_name',
                'cost_price',
                'selling_price',
                'cost_currency',
                'selling_currency',
                # 'image'
            ]
            for field in fields:
                if not getattr(self, field, None):
                    raise ValidationError(f"default variant should have {field}")

        return super().clean()

    def save(self, *args, **kwargs):
        # Ensure only one default variant per product
        if self.is_default:
            ProductVariant.objects.filter(product=self.product, is_default=True).exclude(pk=self.pk).update(is_default=False)
        
        if not self.sku:
            self.sku = f"{self.variant_name}-{self.product.pk}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.is_default:
            return self.variant_name
        if self.variant_name:
            
            return f"{self.product.name} - {self.variant_name}"
        return f"{self.product.name} - {self.sku}"
    
    @property
    def default_variant(self):
        if self.is_default:
            return self
        try:
            return self.objects.get(product=self.product, is_default=True)
        except:
            return None 
    
    @property
    def current_price(self):
        return self.variant_prices.filter(is_current=True).first()
        

class ProductPrice(TenantBaseModel):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='variant_prices')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices')
    cost_price = models.DecimalField(max_digits=15, decimal_places=4)
    cost_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='cost_prices')
    selling_price = models.DecimalField(max_digits=15, decimal_places=4)
    selling_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='selling_prices')
    effective_date = models.DateTimeField(auto_now=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_current = models.BooleanField(default=True)
    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_prices')
    
    
    class Meta:
        db_table = 'product_prices'
        indexes = [
            models.Index(fields=['tenant', 'product', 'is_current']),
            models.Index(fields=['tenant', 'variant', 'is_current']),
            models.Index(fields=['effective_date']),
            models.Index(fields=['end_date']),
        ]
        ordering = ['-effective_date']
    
    def __str__(self):
        return f"{self.variant} - {self.selling_price} ({self.effective_date.date()})"
    
    def save(self, *args, **kwargs):
        # Ensure only one current price per product/variant
        if self.is_current:
            current_prices = ProductPrice.objects.filter(
                product=self.product,
                variant=self.variant,
                is_current=True
            ).exclude(pk=self.pk)
            last_current = current_prices.last()
            if last_current:
                fields = ['cost_price', 'cost_currency', 'selling_price', 'selling_currency']
                for field in fields:
                    if not hasattr(self, field) or not getattr(self, field):
                        setattr(self, field, getattr(last_current, field))
                        
            from django.utils.timezone import now
            current_prices.update(is_current=False)
            current_prices.filter(end_date__isnull=True).update(end_date=now())
        super().save(*args, **kwargs)