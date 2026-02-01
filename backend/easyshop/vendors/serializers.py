from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone

from catalog.utils import check_barcode, generate_barcode
from .models import Vendor, Purchase, PurchaseItem
from core.models import Currency
from catalog.models import ProductVariant, Product, ProductPrice
from inventory.models import ProductBatch, Inventory, StockMovement
from django.db import IntegrityError, transaction
from core.threads import get_current_tenant
from finance.models import Transaction, Payment


class VendorListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for vendor listings"""
    total_purchases = serializers.ReadOnlyField()
    pending_purchases = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by_user.get_full_name', read_only=True)
    photo = serializers.SerializerMethodField()
    class Meta:
        model = Vendor
        fields = [
            'id', 'name', 'photo', 'phone', 'email', 
            'balance', 'status', 'total_purchases', 'pending_purchases',
            'created_by_name', 'created_at'
        ]

    def get_photo(self, obj):
        request = self.context.get('request')
        
        if obj.photo:
            return request.build_absolute_uri(obj.photo.url)
        return ""
class VendorDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for vendor CRUD operations"""
    created_by_name = serializers.CharField(source='created_by_user.get_full_name', read_only=True)
    addresses = serializers.SerializerMethodField()
    recent_purchases = serializers.SerializerMethodField()
    
    class Meta:
        model = Vendor
        fields = [
            'id', 'name', 'phone', 'photo',
            'email', 'tax_id', 'balance',
            'status', 'created_by_name', 'addresses',
            'recent_purchases', 'created_at', 'updated_at'
        ]
        read_only_fields = ['balance', 'created_by_name', 'created_at', 'updated_at', 'status']
    
    def get_addresses(self, obj):
        from core.serializers import AddressSerializer
        addresses = obj.addresses.all()
        return AddressSerializer(addresses, many=True).data
    
    def get_recent_purchases(self, obj):
        recent_purchases = obj.purchases.filter(
            status__in=['pending', 'received']
        ).order_by('-purchase_date')[:5]
        return PurchaseListSerializer(recent_purchases, many=True).data

    def validate_email(self, value):
        if value:
            existing = Vendor.objects.filter(
            email__iexact=value
            )
            if existing.exists():
                raise serializers.ValidationError("Vendor with this email already exists.")
        return value

    def validate_name(self, name):
        vendors = Vendor.objects.filter(name=name)
        if vendors.exists():
            raise serializers.ValidationError(f"{name} Already Exists")
        return name    
    
    
class VendorUpdateSerializer(serializers.ModelSerializer):
    """Vendor Update"""
    
    class Meta:
        model = Vendor
        fields = [
            'id', 'name', 'phone',
            'email', 'photo', 'balance', 'tax_id'
        ]
        read_only_fields = ["id", "balance", "photo"]
        
    def validate_email(self, value):
        if value:
            existing = Vendor.objects.filter(
                email__iexact=value
            ).exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError("Vendor with this email already exists.")
        return value


# Create Purchase

class ProductVariantCreateSerializer(serializers.Serializer):
    """Serializer for creating new product variants within purchase"""
    variant_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    image = serializers.ImageField(required=False, allow_null=True)
    is_default = serializers.BooleanField(default=False)
    
    
    # Pricing fields (required for default variant)
    cost_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    cost_currency_id = serializers.IntegerField(required=False)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    selling_currency_id = serializers.IntegerField(required=False)

    def validate_barcode(self, barcode):
        if barcode:
            try:
                if not check_barcode(barcode):
                    raise serializers.ValidationError(f"barcode: {barcode} already exists")
            except:
                pass
        return barcode


class ProductCreateSerializer(serializers.Serializer):
    """Serializer for creating new products within purchase"""
    name = serializers.CharField(max_length=255)
    category_id = serializers.IntegerField()
    base_unit_id = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True)
    reorder_level = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Always require default variant
    variants = ProductVariantCreateSerializer(many=True, min_length=1)
    
    # class Meta:
    #     model = Product
    #     fields = [
    #         'name', 'category_id', 'base_unit_id',
    #         'description', 'reorder_level',
    #         'variants'
    #     ]
    
    def validate_variants(self, value):
        """Ensure at least one default variant exists"""
        default_variants = [v for v in value if v.get('is_default', False)]
        if len(default_variants) != 1:
            raise serializers.ValidationError("Exactly one default variant is required")
        
        # Validate required fields for default variant
        default_variant = default_variants[0]
        required_fields = ['cost_price', 'cost_currency_id', 'selling_price', 'selling_currency_id']
        for field in required_fields:
            if not default_variant.get(field):
                raise serializers.ValidationError(f"Default variant must have {field}")
        
        for variant in value:
            if not (variant.get("variant_name") or variant.get("is_default")):
                raise serializers.ValidationError(f"non-Default variant must have variant_name")
        
            # Validate barcodes
            variant_barcode = variant.get('barcode')
            if not check_barcode(variant_barcode):
                raise serializers.ValidationError(f"barcode: {variant_barcode} already exists")
        return value


class PurchaseItemCreateSerializer(serializers.Serializer):
    """Flexible purchase item serializer supporting both existing and new products"""
    # For existing products
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    
    # For new products
    product_data = ProductCreateSerializer(required=False, allow_null=True)
    
    # Common fields
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3)
    unit_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Batch tracking
    expiry_date = serializers.DateTimeField(required=False, allow_null=True)
    batch_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    supplier_batch_ref = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    def validate(self, data):
        """Ensure either variant_id or product_data is provided"""
        if not data.get('variant_id') and not data.get('product_data'):
            raise serializers.ValidationError("Either variant_id or product_data must be provided")
        
        if data.get('variant_id') and data.get('product_data'):
            raise serializers.ValidationError("Cannot provide both variant_id and product_data")
        
        return data


class PurchasePaymentSerializer(serializers.Serializer):
    method = serializers.ChoiceField([
        ("cash", "Cash"),
        ("free", "Free"),
        ("loan", "Loan"),
    ])
    currency = serializers.IntegerField(required=False)
    cash_drawer = serializers.IntegerField(required=False)
    
    def validate(self, attrs):
        method = attrs['method']
        currency = attrs.get("currency", None)
        cash_drawer = attrs.get("cash_drawer", None)
        if method=="cash" and not (currency and cash_drawer):
            raise serializers.ValidationError("Currency and Cash Drawer is required for cash Payment")            
        return attrs
    
    
class PurchaseCreateSerializer(serializers.ModelSerializer):
    """Main purchase serializer with comprehensive item handling"""
    items = PurchaseItemCreateSerializer(many=True, write_only=True)
    payment = PurchasePaymentSerializer(write_only=True)
    class Meta:
        model = Purchase
        fields = [
            'total_items', 'vendor', 'location', 'purchase_date',
            'delivery_date', 'tax_amount', 'currency', 'payment',
            'notes', 'items'
        ]

    def create(self, validated_data):
        """Create purchase with items and handle product/variant creation"""
        items_data = validated_data.pop('items')
        tenant = get_current_tenant()
        user = self.context['request'].user
        payment = validated_data.pop("payment")
        
        with transaction.atomic():
            
            validated_data['tenant'] = tenant
            # validated_data['created_by_user'] = user
            validated_data['status'] = 'pending'
            
            purchase = Purchase.objects.create(**validated_data)
            
            # Process each item
            subtotal = Decimal('0')
            for item_data in items_data:
                line_total = self._process_purchase_item(purchase, item_data, user)
                subtotal += line_total
            
            # Update purchase totals
            purchase.subtotal = subtotal
            purchase.total_amount = subtotal + (purchase.tax_amount or Decimal('0'))
            purchase.save()
            
            self._process_payment(payment, purchase)
            
            return purchase
    
    def _process_purchase_item(self, purchase, item_data, user):
        """Process individual purchase item - create product/variant if needed"""
        from .models import PurchaseItem
        tenant = get_current_tenant()
        
        if item_data.get('variant_id'):
            # Existing product variant
            variant_id = item_data['variant_id']
            variant = ProductVariant.objects.get(id=variant_id, tenant=tenant)
        else:
            # Create new product and variants
            variant = self._create_product_and_variants(item_data['product_data'], user, tenant)
            variant_id = variant.id
        
        # Handle batch creation if expiry date provided
        batch_id = None
        if item_data.get('expiry_date'):
            batch = ProductBatch.objects.create(
                tenant=tenant,
                variant_id=variant_id,
                batch_number=item_data.get('batch_number') or self._generate_batch_number(variant_id),
                expiry_date=item_data['expiry_date'],
                supplier_batch_ref=item_data.get('supplier_batch_ref', ''),
                is_active=True
            )
            batch_id = batch.id
        
        # Create purchase item
        quantity = item_data['quantity']
        unit_cost = item_data['unit_cost']
        line_total = quantity * unit_cost
        
        PurchaseItem.objects.create(
            purchase=purchase,
            variant_id=variant_id,
            batch_id=batch_id,
            quantity=quantity,
            unit_cost=unit_cost,
            line_total=line_total,
            received_quantity=Decimal('0')
        )
        
        return line_total
    
    def _create_product_and_variants(self, product_data, user, tenant):
        """Create new product with variants and pricing"""
        # Create product
        try:
            product = Product.objects.create(
                tenant=tenant,
                name=product_data['name'],
                category_id=product_data['category_id'],
                base_unit_id=product_data['base_unit_id'],
                description=product_data.get('description', ''),
                reorder_level=product_data.get('reorder_level', 0),
                has_variants=len(product_data['variants']) > 1,
                is_active=True,
                created_by_user=user
            )
        except IntegrityError as e:
            raise serializers.ValidationError(f"Product Name must be unique: name: {product_data['name']} is duplicated")
            
        default_variant = None
        
        # Create variants
        for variant_data in product_data['variants']:

            variant_name = variant_data.get('variant_name')

            barcode = variant_data.pop('barcode', '')
            
            if not barcode:
                barcode = generate_barcode()
            
            if variant_data['is_default']:
                variant_name = product.name  # Default variant uses product name
            
            try:
                variant = ProductVariant.objects.create(
                    tenant=tenant,
                    product=product,
                    barcode=barcode,
                    sku=self._generate_sku(product.name, variant_name),
                    variant_name=variant_name,
                    image=variant_data.get('image'),
                    is_default=variant_data['is_default'],
                    is_active=True
                )            
                
            except IntegrityError as e:
                raise serializers.ValidationError({"error": "Barcode must be Unique"})
            
            # Create pricing for variant (required for default, optional for others)
            if variant_data.get('cost_price') and variant_data.get('selling_price'):
                ProductPrice.objects.create(
                    tenant=tenant,
                    variant=variant,
                    product=product,
                    cost_price=variant_data['cost_price'],
                    cost_currency_id=variant_data['cost_currency_id'],
                    selling_price=variant_data['selling_price'],
                    selling_currency_id=variant_data['selling_currency_id'],
                    effective_date=timezone.now(),
                    is_current=True,
                    created_by_user=user
                )
            
            if variant_data['is_default']:
                default_variant = variant
        
        return default_variant
    
    def _generate_sku(self, product_name, variant_name):
        """Generate SKU from product and variant names"""
        base = f"{product_name[:3].upper()}-{variant_name[:3].upper() if variant_name else 'DEF'}"
        return f"{base}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    
    def _generate_batch_number(self, variant_id):
        """Generate batch number for variant"""
        count = ProductBatch.objects.filter(variant_id=variant_id).count()
        return f"BATCH-{variant_id}-{count + 1:04d}"

    def _process_payment(self, payment, purchase: Purchase):
        payment_method = payment.get("method")
        if payment_method == "cash":
            payment_currency_id = payment.get("currency")
            try:
                payment_currency = Currency.objects.get(id=payment_currency_id)
            except:
                raise serializers.ValidationError("Invalid Currency")
            
            payment_amount = purchase.currency.convert_to(purchase.total_amount, payment_currency_id)
            payment_cash_drawer_id = payment.get("cash_drawer")
            # Create payment
            payment = Payment.objects.create(
                tenant=purchase.tenant,
                amount=payment_amount,
                currency_id=payment_currency_id,
                payment_method="cash",
                reference_type='purchase',
                reference_id=purchase.id,
                cash_drawer_id=payment_cash_drawer_id,
                notes=f"{payment_amount} {payment_currency.code} Payment For purchase: {purchase.purchase_number}",
                created_by_user=purchase.created_by_user
            )
            
            # Create transaction
            Transaction.objects.create(
                tenant=purchase.tenant,
                amount=payment_amount,
                currency_id=payment_currency_id,
                description=f"Payment for Purchase {purchase.purchase_number}",
                party_type='vendor',
                party_id=purchase.vendor_id,
                transaction_type='expense',
                reference_type='purchase',
                reference_id=purchase.id,
                cash_drawer_id=payment_cash_drawer_id,
                created_by_user=purchase.created_by_user
            )
            
            # Update cash drawer if specified
            from finance.models import CashDrawerMoney
            drawer_money, created = CashDrawerMoney.objects.get_or_create(
                cash_drawer_id=payment_cash_drawer_id,
                currency_id=payment_currency_id,
                defaults={'amount': Decimal('0')}
            )
            drawer_money.amount -= payment_amount
            drawer_money.save()
            
            return payment

        elif payment_method == "loan":
            vendor = purchase.vendor
            base_purchase_amount = Currency.convert_to_base_currency(purchase.total_amount, purchase.currency_id)
            vendor.balance += base_purchase_amount
            vendor.save()
    
            
class PurchaseItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='variant.variant_name')
    barcode = serializers.CharField(source='variant.barcode')
    currency = serializers.IntegerField(source='purchase.currency_id')
    class Meta:
        model = PurchaseItem
        fields = [
            'product_name', 'barcode', 'quantity',
            'unit_cost', 'line_total', 'currency'
        ]


class PurchaseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for purchase listings"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    total_items = serializers.ReadOnlyField()
    total_quantity = serializers.ReadOnlyField()
    
    class Meta:
        model = Purchase
        fields = [
            'id', 'purchase_number', 'vendor_name', 'location_name',
            'purchase_date', 'currency', 'total_amount', 'notes',
            'status', 'total_items', 'total_quantity'
        ]


class PurchaseDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for purchase CRUD operations"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    items = PurchaseItemSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    total_quantity = serializers.ReadOnlyField()
    
    class Meta:
        model = Purchase
        fields = [
            'id', 'purchase_number', 'vendor_name',
            'location_name', 'purchase_date',
            'total_amount', 'currency',
            'status', 'notes',
            'total_items', 'total_quantity', 'items',
        ]
        read_only_fields = [
            'purchase_number', 'subtotal', 'total_amount', 'created_by_name',
            'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        """Validate purchase data"""
        purchase_date = data.get('purchase_date')
        delivery_date = data.get('delivery_date')
        
        # Validate delivery date is not before purchase date
        if delivery_date and purchase_date and delivery_date < purchase_date:
            raise serializers.ValidationError(
                "Delivery date cannot be before purchase date"
            )
        
        # Validate status transitions
        if self.instance:
            current_status = self.instance.status
            new_status = data.get('status', current_status)
            
            invalid_transitions = {
                'received': ['draft', 'pending'],
                'cancelled': ['received', 'partially_received']
            }
            
            if current_status in invalid_transitions:
                if new_status in invalid_transitions[current_status]:
                    raise serializers.ValidationError(
                        f"Cannot change status from {current_status} to {new_status}"
                    )
        
        return data






class ReceiveItemsSerializer(serializers.Serializer):
    """Serializer for receiving purchase items"""
    items = serializers.ListField(
        child=serializers.DictField(
            child=serializers.DecimalField(max_digits=10, decimal_places=3)
        ),
        write_only=True
    )
    
    def validate_items(self, items_data):
        """Validate received items data"""
        if not items_data:
            raise serializers.ValidationError("Items data is required")
        
        purchase = self.context['purchase']
        
        for item_data in items_data:
            item_id = item_data.get('item_id')
            quantity = item_data.get('quantity')
            
            if not item_id or not quantity:
                raise serializers.ValidationError(
                    "Each item must have item_id and quantity"
                )
            
            try:
                item = purchase.items.get(id=item_id)
            except PurchaseItem.DoesNotExist:
                raise serializers.ValidationError(
                    f"Purchase item with id {item_id} not found"
                )
            
            if quantity <= 0:
                raise serializers.ValidationError("Quantity must be positive")
            
            if item.received_quantity + quantity > item.quantity:
                raise serializers.ValidationError(
                    f"Cannot receive more than ordered quantity for item {item_id}"
                )
        
        return items_data
    
    def save(self):
        """Process received items"""
        purchase = self.context['purchase']
        items_data = self.validated_data['items']
        
        for item_data in items_data:
            item = purchase.items.get(id=item_data['item_id'])
            item.receive_quantity(item_data['quantity'])
        
        return purchase


class VendorStatsSerializer(serializers.Serializer):
    """Serializer for vendor statistics"""
    total_vendors = serializers.IntegerField()
    active_vendors = serializers.IntegerField()
    inactive_vendors = serializers.IntegerField()
    total_purchases_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_purchases = serializers.IntegerField()
    this_month_purchases = serializers.DecimalField(max_digits=15, decimal_places=2)


class PurchaseStatsSerializer(serializers.Serializer):
    """Serializer for purchase statistics"""
    total_purchases = serializers.IntegerField()
    pending_purchases = serializers.IntegerField()
    received_purchases = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    this_month_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_purchase_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    

class PurchaseUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating purchase status and handling inventory changes"""
    
    class Meta:
        model = Purchase
        fields = ['status', 'notes', 'delivery_date']
    
    def update(self, instance, validated_data):
        """Update purchase and handle status-specific logic"""
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        with transaction.atomic():
            # Update purchase
            purchase = super().update(instance, validated_data)
            
            # Handle status transitions
            if old_status != new_status:
                self._handle_status_change(purchase, old_status, new_status)
            
            return purchase
    
    def _handle_status_change(self, purchase, old_status, new_status):
        """Handle inventory and financial changes based on status transitions"""
        user = self.context['request'].user
        
        # Status: draft -> pending/ordered
        if old_status == 'draft' and new_status in ['pending', 'ordered', 'approved']:
            self._handle_order_confirmation(purchase, user)
        
        # Status: * -> partially_received/received
        elif new_status in ['partially_received', 'received']:
            self._handle_receipt(purchase, user)
        
        # Status: * -> cancelled
        elif new_status == 'cancelled':
            self._handle_cancellation(purchase, user)
    
    def _handle_order_confirmation(self, purchase, user):
        """Handle purchase order confirmation - reserve inventory if needed"""
        # Create transaction record for purchase commitment
        Transaction.objects.create(
            tenant=purchase.tenant,
            transaction_date=timezone.now(),
            amount=purchase.total_amount,
            currency=purchase.currency,
            description=f"Purchase Order {purchase.purchase_number} - Committed",
            party_type='vendor',
            party_id=purchase.vendor_id,
            transaction_type='purchase_commitment',
            reference_type='purchase',
            reference_id=purchase.id,
            created_by_user=user
        )
    
    def _handle_receipt(self, purchase, user):
        """Handle inventory receipt - update stock levels"""
        for item in purchase.items.all():
            # Update inventory
            inventory, created = Inventory.objects.get_or_create(
                tenant=purchase.tenant,
                variant=item.variant,
                batch=item.batch,
                location=purchase.location,
                defaults={'quantity_on_hand': Decimal('0')}
            )
            
            # Determine received quantity (for now, assume full receipt)
            received_qty = item.quantity - item.received_quantity
            if received_qty > 0:
                inventory.quantity_on_hand += received_qty
                inventory.save()
                
                # Update received quantity
                item.received_quantity += received_qty
                item.save()
                
                # Create stock movement
                StockMovement.objects.create(
                    tenant=purchase.tenant,
                    variant=item.variant,
                    batch=item.batch,
                    location=purchase.location,
                    movement_type='purchase_receipt',
                    quantity=received_qty,
                    reference_type='purchase',
                    reference_id=purchase.id,
                    notes=f"Received from Purchase {purchase.purchase_number}",
                    created_by_user=user
                )
    
    def _handle_cancellation(self, purchase, user):
        """Handle purchase cancellation - reverse any reservations"""
        # Create reversal transaction
        Transaction.objects.create(
            tenant=purchase.tenant,
            transaction_date=timezone.now(),
            amount=-purchase.total_amount,
            currency=purchase.currency,
            description=f"Purchase Order {purchase.purchase_number} - Cancelled",
            party_type='vendor',
            party_id=purchase.vendor_id,
            transaction_type='purchase_cancellation',
            reference_type='purchase',
            reference_id=purchase.id,
            created_by_user=user
        )


# class PurchasePaymentSerializer(serializers.Serializer):
#     """Handle purchase payments"""
#     amount = serializers.DecimalField(max_digits=12, decimal_places=2)
#     currency_id = serializers.IntegerField()
#     payment_method = serializers.CharField(max_length=50)
#     cash_drawer_id = serializers.IntegerField(required=False, allow_null=True)
#     notes = serializers.CharField(required=False, allow_blank=True)
    
#     def create(self, validated_data):
#         """Create payment for purchase"""
#         purchase = self.context['purchase']
#         user = self.context['request'].user
#         tenant = get_current_tenant()
        
#         with transaction.atomic():
#             # Generate payment number
#             payment_count = Payment.objects.filter(tenant=tenant).count()
#             payment_number = f"PAY-{timezone.now().strftime('%Y%m')}-{payment_count + 1:04d}"
            
#             # Create payment
#             payment = Payment.objects.create(
#                 tenant=tenant,
#                 payment_number=payment_number,
#                 amount=validated_data['amount'],
#                 currency_id=validated_data['currency_id'],
#                 payment_method=validated_data['payment_method'],
#                 payment_date=timezone.now(),
#                 reference_type='purchase',
#                 reference_id=purchase.id,
#                 cash_drawer_id=validated_data.get('cash_drawer_id'),
#                 notes=validated_data.get('notes', ''),
#                 processed_by_user=user
#             )
            
#             # Create transaction
#             Transaction.objects.create(
#                 tenant=tenant,
#                 transaction_date=timezone.now(),
#                 amount=-validated_data['amount'],  # Negative for outgoing payment
#                 currency_id=validated_data['currency_id'],
#                 description=f"Payment for Purchase {purchase.purchase_number}",
#                 party_type='vendor',
#                 party_id=purchase.vendor_id,
#                 transaction_type='purchase_payment',
#                 reference_type='payment',
#                 reference_id=payment.id,
#                 cash_drawer_id=validated_data.get('cash_drawer_id'),
#                 created_by_user=user
#             )
            
#             # Update cash drawer if specified
#             if validated_data.get('cash_drawer_id'):
#                 from finance.models import CashDrawerMoney
#                 drawer_money, created = CashDrawerMoney.objects.get_or_create(
#                     cash_drawer_id=validated_data['cash_drawer_id'],
#                     currency_id=validated_data['currency_id'],
#                     defaults={'amount': Decimal('0')}
#                 )
#                 drawer_money.amount -= validated_data['amount']
#                 drawer_money.save()
            
#             return payment
