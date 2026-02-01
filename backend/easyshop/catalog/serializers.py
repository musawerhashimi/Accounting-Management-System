from rest_framework import serializers
from django.db import transaction
from django.core.validators import MinValueValidator

from core.models import Currency, Unit
from inventory.models import Inventory
from sales.models import ReturnItem, SaleItem
from vendors.models import PurchaseItem
from .models import (
    Department, Category, ProductVariant, ProductPrice
)


class CategorySerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    created_by_user_name = serializers.CharField(source='created_by_user.get_full_name', read_only=True)
    # products_count = serializers.IntegerField(read_only=True)
    total_products = serializers.ReadOnlyField()
    total_quantity = serializers.ReadOnlyField()
    
    
    class Meta:
        model = Category
        fields = [
            'id', 'department', 'department_name', 'name', 'description', 'is_active',
            'created_by_user', 'created_by_user_name',
            'created_at', 'updated_at', 'total_products', 'total_quantity'
        ]
        read_only_fields = ['id', 'created_by_user', 'created_at', 'updated_at']


class DepartmentSerializer(serializers.ModelSerializer):
    created_by_user_name = serializers.CharField(source='created_by_user.get_full_name', read_only=True)
    # categories_count = serializers.IntegerField(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    total_products = serializers.ReadOnlyField()
    total_quantity = serializers.ReadOnlyField()
    
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'description', 'is_active', 'categories',
            'created_by_user', 'created_by_user_name',
            'total_products', 'total_quantity',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by_user', 'created_at', 'updated_at']


class ProductVariantSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(source='product.category.id', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    department_id = serializers.IntegerField(source='product.category.department.id', read_only=True)
    department_name = serializers.CharField(source='product.category.department.name', read_only=True)

    name = serializers.CharField(source="variant_name")

    # variant_attributes = ProductVariantAttributeSerializer(many=True, read_only=True)
    
    cost_price = serializers.DecimalField(max_digits=10, decimal_places=2, source="current_price.cost_price", read_only=True)
    cost_currency = serializers.IntegerField(source="current_price.cost_currency_id", read_only=True)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, source="current_price.selling_price", read_only=True)
    selling_currency = serializers.IntegerField(source="current_price.selling_currency_id", read_only=True)

    
    # current_stock = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'sku', 'name',
            # 'variant_name',
            'barcode',
            'category_id', 'category_name',
            'department_id', 'department_name',
            'cost_price', 'selling_price',
            'cost_currency', 'selling_currency',
            'image', 'is_default', 'is_active',
            # 'variant_attributes',
            # 'variant_prices', 'current_stock',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'barcode']


class ProductVariantDetailSerializer(serializers.ModelSerializer):
    # map “name” → product.name
    name = serializers.CharField(source='product.name')
    # other product fields
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='product.category'
    )
    department = serializers.IntegerField(source='product.category.department_id', read_only=True)
    base_unit = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.all(),
        source='product.base_unit'
    )
    reorder_level = serializers.IntegerField(
        source='product.reorder_level',
        validators=[MinValueValidator(0)]
    )
    description = serializers.CharField(
        source='product.description',
        allow_blank=True,
        required=False
    )

    # new selling price info
    selling_price = serializers.DecimalField(
        source="current_price.selling_price",
        max_digits=15,
        decimal_places=3,
    )
    selling_currency = serializers.PrimaryKeyRelatedField(
        source="current_price.selling_currency",
        queryset=Currency.objects.all()
    )
    image_url = serializers.SerializerMethodField(read_only=True)
    available = serializers.SerializerMethodField(read_only=True)
    purchased = serializers.SerializerMethodField(read_only=True)
    sold      = serializers.SerializerMethodField(read_only=True)
    returned  = serializers.SerializerMethodField(read_only=True)

    
    
    class Meta:
        model = ProductVariant
        fields = [
            'name', 'barcode', 'category', 'department', 'base_unit', 'reorder_level', 'description',
            'selling_price', 'selling_currency',
            
            'image_url', 'available', 'purchased', 'sold', 'returned',
        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        # 1) Update parent Product
        price = validated_data.pop('current_price')
        prod_data = validated_data.pop('product', {})
        for attr, val in prod_data.items():
            setattr(instance.product, attr, val)
        instance.product.save()
        # 2) Sync variant_name to new product.name (if you want)
        instance.variant_name = instance.product.name

        instance.save()

        # 4) Create new selling‐price record (ends old one automatically)

        new_price = ProductPrice.objects.create(
            tenant=instance.tenant,
            product=instance.product,
            variant=instance,
            selling_price=price['selling_price'],
            selling_currency=price['selling_currency'],
            is_current=True,
            created_by_user=self.context['request'].user,
        )

        return instance


    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_available(self, obj):
        tenant = self.context['request'].tenant
        qs = Inventory.objects.filter(
            tenant=tenant,
            variant=obj
        ).values_list('quantity_on_hand', flat=True)
        return sum(qs) if qs else 0

    def get_purchased(self, obj):
        tenant = self.context['request'].tenant
        qs = PurchaseItem.objects.filter(
            variant=obj,
            purchase__status__in=['received', 'partially_received'],
            purchase__tenant=tenant
        ).values_list('received_quantity', flat=True)
        return sum(qs) if qs else 0

    def get_sold(self, obj):
        tenant = self.context['request'].tenant
        qs = SaleItem.objects.filter(
            inventory__variant=obj,
            sale__tenant=tenant
        ).values_list('quantity', flat=True)
        return sum(qs) if qs else 0

    def get_returned(self, obj):
        tenant = self.context['request'].tenant
        qs = ReturnItem.objects.filter(
            sale_item__inventory__variant=obj,
            return_order__tenant=tenant  # assuming your Return parent is named return_record
        ).values_list('quantity_returned', flat=True)
        return sum(qs) if qs else 0


class ProductVariantSearchSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="variant_name")
    category_id = serializers.IntegerField(source='product.category_id', read_only=True)
    department_id = serializers.IntegerField(source='product.category.department_id', read_only=True)
    cost_price = serializers.DecimalField(max_digits=10, decimal_places=2, source="current_price.cost_price", read_only=True)
    cost_currency = serializers.IntegerField(source="current_price.cost_currency_id", read_only=True)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, source="current_price.selling_price", read_only=True)
    selling_currency = serializers.IntegerField(source="current_price.selling_currency_id", read_only=True)
    unit_id = serializers.IntegerField(source="product.base_unit_id")
    reorder_level = serializers.IntegerField(source="product.reorder_level")
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'name', 'barcode',
            'category_id', 'department_id',
            'cost_price', 'selling_price',
            'cost_currency', 'selling_currency',
            'unit_id', 'reorder_level'
        ]