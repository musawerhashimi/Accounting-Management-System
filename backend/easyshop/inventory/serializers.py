from rest_framework import serializers
from django.db import transaction, models
from django.db.models.query import QuerySet
from django.utils import timezone
from decimal import Decimal
from accounts.models import UserProductPreference
from .models import (
    Location, ProductBatch, Inventory, StockMovement,
    InventoryAdjustment, InventoryCount, InventoryCountItem
)


class DummyQuerySet(QuerySet):
    def __init__(self, model = None, query = None, using = None, hints = None):
        pass


class LocationSerializer(serializers.ModelSerializer):
    # address_display = serializers.CharField(source='address.__str__()', read_only=True)
    manager_name = serializers.CharField(source='manager.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by_user.get_full_name', read_only=True)
    total_products = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()
    class Meta:
        model = Location
        fields = [
            'id', 'name', 'location_type', 'address',
            'manager', 'manager_name', 'created_by_user', 
            'created_by_name', 'total_products', 'total_quantity',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by_user', 'created_at', 'updated_at']

    def get_total_products(self, obj):
        return obj.inventory_records.values('variant').distinct().count()

    def get_total_quantity(self, obj):
        total = obj.inventory_records.aggregate(
            total=models.Sum('quantity_on_hand')
        )['total']
        return total or Decimal('0')


class ProductBatchSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(source='variant.variant_name', read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    total_quantity = serializers.SerializerMethodField()

    class Meta:
        model = ProductBatch
        fields = [
            'id', 'variant', 'variant_name', 'product_name', 'batch_number',
            'manufacture_date', 'expiry_date', 'supplier_batch_ref', 'notes',
            'is_active', 'is_expired', 'days_until_expiry', 'total_quantity',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_total_quantity(self, obj):
        total = obj.inventory_records.aggregate(
            total=models.Sum('quantity_on_hand')
        )['total']
        return total or Decimal('0')

    def validate(self, data):
        if data.get('expiry_date') and data.get('manufacture_date'):
            if data['expiry_date'] <= data['manufacture_date']:
                raise serializers.ValidationError(
                    "Expiry date must be after manufacture date"
                )
        return data


class InventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='variant.variant_name', read_only=True)
    image = serializers.ImageField(source="variant.image")
    barcode = serializers.CharField(source="variant.barcode")
    category_id = serializers.IntegerField(source="variant.product.category_id")
    department_id = serializers.IntegerField(source="variant.product.category.department_id")
    location_name = serializers.CharField(source='location.name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    available_quantity = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    unit_id = serializers.IntegerField(source='variant.product.base_unit_id', read_only=True)
    cost_price = serializers.DecimalField(source='variant.current_price.cost_price', max_digits=15, decimal_places=2, read_only=True)
    selling_price = serializers.DecimalField(source='variant.current_price.selling_price', max_digits=15, decimal_places=2, read_only=True)
    cost_currency_id = serializers.IntegerField(source='variant.current_price.cost_currency_id', read_only=True)
    selling_currency_id = serializers.IntegerField(source='variant.current_price.selling_currency_id', read_only=True)

    is_favorite = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    is_loved = serializers.SerializerMethodField()

    class Meta:
        model = Inventory
        fields = [
            'id', 'variant', 'product_name', 'batch', 'batch_number',
            'image', 'barcode', 'category_id', 'department_id',
            'location', 'location_name', 'quantity_on_hand', 'reserved_quantity',
            'available_quantity', 'unit_id', 'cost_price',
            'cost_currency_id', 'selling_price', 'selling_currency_id',
            'is_favorite', 'is_bookmarked', 'is_loved',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['available_quantity', 'needs_reorder', 'created_at', 'updated_at']

    def get_is_favorite(self, instance):
        user = self.context['request'].user
        preferences, _ = UserProductPreference.objects.get_or_create(
            tenant=user.tenant,
            variant=instance.variant,
            user=user
        )
        return preferences.is_favorite

    def get_is_bookmarked(self, instance):
        user = self.context['request'].user
            
        preferences, _ = UserProductPreference.objects.get_or_create(
            tenant=user.tenant,
            variant=instance.variant,
            user=user
        )
        return preferences.is_bookmarked

    def get_is_loved(self, instance):
        user = self.context['request'].user
        preferences, _ = UserProductPreference.objects.get_or_create(
            tenant=user.tenant,
            variant=instance.variant,
            user=user
        )
        return preferences.is_loved


class StockMovementSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(source='variant.variant_name', read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    created_by_name = serializers.CharField(source='created_by_user.get_full_name', read_only=True)
    unit_name = serializers.CharField(source='variant.product.base_unit.name', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'id', 'variant', 'variant_name', 'product_name', 'batch', 'batch_number',
            'location', 'location_name', 'movement_type', 'quantity', 'unit_name',
            'reference_type', 'reference_id', 'notes', 'created_by_user',
            'created_by_name', 'created_at'
        ]
        read_only_fields = ['created_by_user', 'created_at']


class InventoryAdjustmentSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(source='variant.variant_name', read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    created_by_name = serializers.CharField(source='created_by_user.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by_user.get_full_name', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    unit_name = serializers.CharField(source='variant.product.base_unit.name', read_only=True)

    class Meta:
        model = InventoryAdjustment
        fields = [
            'id', 'adjustment_number', 'variant', 'variant_name', 'product_name',
            'batch', 'batch_number', 'location', 'location_name', 'adjustment_quantity',
            'unit_name', 'reason', 'cost_impact', 'currency', 'currency_symbol',
            'notes', 'approved_by_user', 'approved_by_name', 'created_by_user',
            'created_by_name', 'adjustment_date', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'adjustment_number', 'created_by_user', 'created_at', 'updated_at'
        ]

    def validate(self, data):
        if not data.get('adjustment_date'):
            data['adjustment_date'] = timezone.now()
        return data


class InventoryCountItemSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(source='variant.variant_name', read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    counted_by_name = serializers.CharField(source='counted_by_user.get_full_name', read_only=True)
    unit_name = serializers.CharField(source='variant.product.base_unit.name', read_only=True)

    class Meta:
        model = InventoryCountItem
        fields = [
            'id', 'variant', 'variant_name', 'product_name', 'batch', 'batch_number',
            'system_quantity', 'counted_quantity', 'variance', 'unit_name',
            'notes', 'counted_by_user', 'counted_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['variance', 'created_at', 'updated_at']


class InventoryCountSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by_user.get_full_name', read_only=True)
    completed_by_name = serializers.CharField(source='completed_by_user.get_full_name', read_only=True)
    count_items = InventoryCountItemSerializer(many=True, read_only=True)

    class Meta:
        model = InventoryCount
        fields = [
            'id', 'count_number', 'location', 'location_name', 'count_date',
            'status', 'total_items_counted', 'variances_found', 'created_by_user',
            'created_by_name', 'completed_by_user', 'completed_by_name',
            'count_items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'count_number', 'total_items_counted', 'variances_found',
            'created_by_user', 'completed_by_user', 'created_at', 'updated_at'
        ]

    def validate(self, data):
        if not data.get('count_date'):
            data['count_date'] = timezone.now()
        return data


class BulkStockMovementSerializer(serializers.Serializer):
    """Serializer for bulk stock movements"""
    movements = StockMovementSerializer(many=True)
    
    def create(self, validated_data):
        movements_data = validated_data['movements']
        movements = []
        
        with transaction.atomic():
            for movement_data in movements_data:
                movement_data['tenant'] = self.context['request'].user.tenant
                movement_data['created_by_user'] = self.context['request'].user
                movement = StockMovement.objects.create(**movement_data)
                movements.append(movement)
        
        return {'movements': movements}


class InventoryTransferSerializer(serializers.Serializer):
    """Serializer for inventory transfers between locations"""
    variant = serializers.PrimaryKeyRelatedField(
        queryset=DummyQuerySet()  # Will be set in __init__
    )
    batch = serializers.PrimaryKeyRelatedField(
        queryset=DummyQuerySet(),  # Will be set in __init__
        required=False,
        allow_null=True
    )
    from_location = serializers.PrimaryKeyRelatedField(
        queryset=DummyQuerySet()  # Will be set in __init__
    )
    to_location = serializers.PrimaryKeyRelatedField(
        queryset=DummyQuerySet()  # Will be set in __init__
    )
    quantity = serializers.DecimalField(
        max_digits=15, 
        decimal_places=4,
        min_value=Decimal('0.0001')
    )
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.context.get('request'):
            tenant = self.context['request'].tenant
            
            self.fields['variant'].queryset = tenant.products.filter(
                variants__isnull=False
            ).distinct()
            self.fields['batch'].queryset = tenant.product_batches.filter(is_active=True)
            self.fields['from_location'].queryset = tenant.locations.filter(is_active=True)
            self.fields['to_location'].queryset = tenant.locations.filter(is_active=True)

    def validate(self, data):
        # Validate that from_location and to_location are different
        if data['from_location'] == data['to_location']:
            raise serializers.ValidationError(
                "Source and destination locations must be different"
            )
        
        # Validate that enough stock is available at source location
        try:
            inventory = Inventory.objects.get(
                tenant=self.context['request'].user.tenant,
                variant=data['variant'],
                batch=data.get('batch'),
                location=data['from_location']
            )
            if inventory.available_quantity < data['quantity']:
                raise serializers.ValidationError(
                    f"Insufficient stock. Available: {inventory.available_quantity}"
                )
        except Inventory.DoesNotExist:
            raise serializers.ValidationError(
                "No inventory found at source location"
            )
        
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        tenant = user.tenant
        
        with transaction.atomic():
            # Create outbound movement
            outbound_movement = StockMovement.objects.create(
                tenant=tenant,
                variant=validated_data['variant'],
                batch=validated_data.get('batch'),
                location=validated_data['from_location'],
                movement_type='transfer',
                quantity=-validated_data['quantity'],  # Negative for outbound
                reference_type='transfer',
                notes=f"Transfer to {validated_data['to_location'].name}. {validated_data.get('notes', '')}",
                created_by_user=user
            )
            
            # Create inbound movement
            inbound_movement = StockMovement.objects.create(
                tenant=tenant,
                variant=validated_data['variant'],
                batch=validated_data.get('batch'),
                location=validated_data['to_location'],
                movement_type='transfer',
                quantity=validated_data['quantity'],  # Positive for inbound
                reference_type='transfer',
                reference_id=outbound_movement.id,
                notes=f"Transfer from {validated_data['from_location'].name}. {validated_data.get('notes', '')}",
                created_by_user=user
            )
            
            # Link the movements
            outbound_movement.reference_id = inbound_movement.id
            outbound_movement.save(update_fields=['reference_id'])
        
        return {
            'outbound_movement': outbound_movement,
            'inbound_movement': inbound_movement,
            'quantity_transferred': validated_data['quantity']
        }


class InventoryReportSerializer(serializers.Serializer):
    """Serializer for inventory reports"""
    location = serializers.PrimaryKeyRelatedField(
        queryset=DummyQuerySet,  # Will be set in __init__
        required=False,
        allow_null=True
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=DummyQuerySet,  # Will be set in __init__
        required=False,
        allow_null=True
    )
    low_stock_only = serializers.BooleanField(default=False)
    expired_only = serializers.BooleanField(default=False)
    expiring_days = serializers.IntegerField(required=False, min_value=1, max_value=365)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.context.get('request'):
            tenant = self.context['request'].user.tenant
            self.fields['location'].queryset = tenant.locations.filter(is_active=True)
            self.fields['category'].queryset = tenant.categories.filter(is_active=True)


class StockLevelReportSerializer(serializers.Serializer):
    """Serializer for stock level analysis"""
    product_name = serializers.CharField(read_only=True)
    variant_name = serializers.CharField(read_only=True)
    sku = serializers.CharField(read_only=True)
    location_name = serializers.CharField(read_only=True)
    current_stock = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    reserved_stock = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    available_stock = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    reorder_level = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    needs_reorder = serializers.BooleanField(read_only=True)
    cost_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    selling_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    unit_name = serializers.CharField(read_only=True)


class ExpiryReportSerializer(serializers.Serializer):
    """Serializer for expiry analysis"""
    product_name = serializers.CharField(read_only=True)
    variant_name = serializers.CharField(read_only=True)
    batch_number = serializers.CharField(read_only=True)
    location_name = serializers.CharField(read_only=True)
    quantity = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    expiry_date = serializers.DateField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    cost_impact = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    unit_name = serializers.CharField(read_only=True)




#----------------------------------------------------


from rest_framework import serializers
from django.db.models import Sum
from decimal import Decimal
from .models import ProductVariant, Inventory, Location
from sales.models import SaleItem


class ProductVariantInventorySerializer(serializers.ModelSerializer):
    item = serializers.CharField(source='variant_name', read_only=True)
    department_name = serializers.CharField(source='product.category.department.name', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    available_quantity = serializers.SerializerMethodField()
    sold_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductVariant
        fields = [
            'id',
            'item',
            'barcode', 
            'department_name',
            'category_name',
            'available_quantity',
            'sold_quantity'
        ]
    
    def get_available_quantity(self, obj):
        """Get total available quantity for this variant at specified location"""
        location_id = self.context.get('location_id')
        
        if location_id:
            # Get inventory for specific location
            inventory_qs = obj.inventory_records.filter(
                location_id=location_id,
                location__is_active=True
            )
        else:
            # Get inventory across all active locations
            inventory_qs = obj.inventory_records.filter(
                location__is_active=True
            )
        
        total_available = inventory_qs.aggregate(
            total=Sum('quantity_on_hand') - Sum('reserved_quantity')
        )['total']
        
        return total_available or Decimal('0.0000')
    
    def get_sold_quantity(self, obj):
        """Get total sold quantity for this variant at specified location"""
        location_id = self.context.get('location_id')
        
        # Base queryset for sold items
        sold_items_qs = SaleItem.objects.filter(
            inventory__variant=obj,
            sale__status='completed'  # Only count completed sales
        )
        
        if location_id:
            # Filter by location
            sold_items_qs = sold_items_qs.filter(
                inventory__location_id=location_id
            )
        
        total_sold = sold_items_qs.aggregate(
            total=Sum('quantity')
        )['total']
        
        return total_sold or Decimal('0.0000')