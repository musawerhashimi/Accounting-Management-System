from rest_framework import serializers
from django.db import transaction, models
from decimal import Decimal

from core.models import Currency
from customers.models import CustomerStatement
from finance.models import CashDrawer, CashDrawerMoney, Payment, Transaction
from .models import Sales, SaleItem, Returns, ReturnItem
from django.core.validators import MinValueValidator

    
class SaleItemSerializer(serializers.ModelSerializer):
    """Serializer for sale items"""
    
    variant_name = serializers.CharField(source='inventory.variant.variant_name', read_only=True)
    unit_name = serializers.CharField(source='inventory.variant.product.base_unit.name', read_only=True)
    
    class Meta:
        model = SaleItem
        fields = [
            'id', 'inventory', 'variant_name', 'unit_name',
            'quantity', 'unit_price', 'line_total', 
            'discount_amount', 'created_at'
        ]
        read_only_fields = ['id', 'line_total', 'created_at']
    
    def validate(self, attrs):
        """Validate sale item data"""
        quantity = attrs.get('quantity')
        inventory = attrs.get("inventory")
        
        available_qty = inventory.available_quantity
        
        if quantity > available_qty:
            raise serializers.ValidationError(
                {'quantity': f'Insufficient inventory. Available: {available_qty}'}
            )
        
        return attrs


class SalePaymentSerializer(serializers.Serializer):
    """Process payment for a sale"""
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.all()
    )
    cash_drawer = serializers.PrimaryKeyRelatedField(
        queryset=CashDrawer.objects.all()
    )
    notes = serializers.CharField(max_length=200, required=False, allow_null=True, allow_blank=True)

    
class SaleCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating sales"""
    items = SaleItemSerializer(many=True, write_only=True)
    payments = SalePaymentSerializer(many=True, write_only=True)
    
    class Meta:
        model = Sales
        fields = [
            'customer', 'sale_date', 'receipt_id',
            'discount_amount', 'tax_amount', 'payments',
            'currency', 'notes', 'items'
        ]
    
    def validate(self, attrs):
        """Validate sale data"""
        items_data = attrs.get('items', [])
        
        if not items_data:
            raise serializers.ValidationError(
                {'items': 'At least one item is required.'}
            )
        
        
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        """Create sale with items"""
        items_data = validated_data.pop('items')
        payments = validated_data.pop("payments", [])

        # Generate sale number
        last_sale = Sales.objects.order_by('-id').first()
        if last_sale:
            last_number = int(last_sale.sale_number.split('-')[-1])
            sale_number = f"SALE-{last_number + 1:06d}"
        else:
            sale_number = "SALE-000001"
        
        validated_data['sale_number'] = sale_number
        
        # Create sale
        sale = Sales.objects.create(**validated_data)
        
        # Create sale items and calculate totals
        subtotal = Decimal('0.00')
        total_discount = Decimal('0.00')
        
        for item_data in items_data:
            item_data['sale'] = sale
            item = SaleItem.objects.create(**item_data)
            subtotal += item.line_total
            total_discount += item.discount_amount
        
        # Update sale totals
        sale.subtotal = subtotal
        sale.discount_amount = total_discount
        sale.total_amount = subtotal + sale.tax_amount
        sale.save()
        

        for payment in payments:
            self._make_payment(payment, sale)
        
        sale.refresh_from_db()

        self._add_to_customer_account(sale)
        
        # Update inventory
        self._update_inventory_on_sale(sale)
        
        return sale
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """Handle the update of a sale and its related items."""
        items_data = validated_data.pop('items', [])
        
        # --- 1. Reverse Old Financial & Inventory State ---
        # Reverse the old customer balance entry before recalculating
        self._reverse_customer_account_update(instance)
        # Reverse old inventory movements before updating
        self._reverse_inventory_update(instance)

        # --- 2. Update Sale Items ---
        # This logic handles adding, updating, and removing items
        existing_items = {item.id: item for item in instance.items.all()}
        updated_item_ids = set()

        for item_data in items_data:
            item_id = item_data.get('id')
            if item_id and item_id in existing_items:
                # Update existing item
                item = existing_items[item_id]
                # Update fields like quantity, unit_price, etc.
                item.quantity = item_data.get('quantity', item.quantity)
                item.unit_price = item_data.get('unit_price', item.unit_price)
                item.discount_amount = item_data.get('discount_amount', item.discount_amount)
                item.save()
                updated_item_ids.add(item_id)
            elif not item_id:
                # Create new item
                SaleItem.objects.create(sale=instance, **item_data)

        # Delete items that were removed from the request
        items_to_delete_ids = set(existing_items.keys()) - updated_item_ids
        if items_to_delete_ids:
            SaleItem.objects.filter(id__in=items_to_delete_ids).delete()

        # --- 3. Update the Sale Instance & Recalculate Totals ---
        # Update simple fields from validated_data
        instance.customer = validated_data.get('customer', instance.customer)
        instance.notes = validated_data.get('notes', instance.notes)
        instance.tax_amount = validated_data.get('tax_amount', instance.tax_amount)
        # Other fields...
        
        # Refresh instance to get the new set of items
        instance.refresh_from_db()
        
        # Recalculate totals from scratch based on the new state of items
        subtotal = Decimal('0.00')
        total_discount = Decimal('0.00')
        for item in instance.items.all():
            subtotal += item.line_total
            total_discount += item.discount_amount
            
        instance.subtotal = subtotal
        instance.discount_amount = total_discount
        instance.total_amount = subtotal + instance.tax_amount
        instance.save()
        
        # --- 4. Apply New Financial & Inventory State ---
        # Update payment status and apply new balance to customer account
        instance.update_payment_status() # Assuming this method recalculates balance_due
        self._add_to_customer_account(instance) # Use your existing method
        
        # Create new stock movements for the final state of the sale
        self._update_inventory_on_sale(instance)
        
        instance.refresh_from_db()
        return instance
    
    def _update_inventory_on_sale(self, sale):
        """Update inventory when sale is created/confirmed"""
        for item in sale.items.all():
            
            # Create stock movement
            from inventory.models import StockMovement
            StockMovement.objects.create(
                tenant=sale.tenant,
                variant=item.inventory.variant,
                batch=item.inventory.batch,
                location=item.inventory.location,
                movement_type='sale',
                quantity=-item.quantity,
                reference_type='sale',
                reference_id=sale.id,
                notes=f"Sale: {sale.sale_number}",
                created_by_user=sale.created_by_user
            )
    
    def _make_payment(self, payment, sale):
        """Create payment and update financial records"""

        amount = payment.get('amount')
        if amount <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0")
        

        # Create payment record
        payment = Payment.objects.create(
            tenant=sale.tenant,
            amount=payment.get('amount'),
            currency=payment.get('currency'),
            payment_method="cash",
            reference_type='sale',
            reference_id=sale.pk,
            cash_drawer=payment.get('cash_drawer'),
            notes=payment.get('notes', ''),
            created_by_user=self.context['request'].user
        )
        
        # Create transaction record for audit trail
        Transaction.objects.create(
            tenant=payment.tenant,
            transaction_date=payment.payment_date,
            amount=payment.amount,
            currency=payment.currency,
            description=f"Payment for Sale #{sale.sale_number}",
            party_type='customer',
            party_id=sale.customer.pk if sale.customer else None,
            transaction_type='income' if type=="tender" else "expense",
            reference_type='sale',
            reference_id=sale.pk,
            cash_drawer=payment.cash_drawer,
            created_by_user=payment.created_by_user
        )
        if sale.customer:
            CustomerStatement.objects.create(
                tenant=payment.tenant,
                customer=sale.customer,
                amount=payment.amount,
                currency=payment.currency,
                statement_type="cash",
                statement_date=payment.payment_date,
                sale=sale,
                cash_drawer=payment.cash_drawer,
                notes=f"Statement for Sale #{sale.sale_number}",
                created_by_user=payment.created_by_user,
            )
        
        # Update cash drawer for cash payments
        if payment.payment_method == 'cash' and payment.cash_drawer_id:
            cash_drawer_money, _ = CashDrawerMoney.objects.get_or_create(
                cash_drawer_id=payment.cash_drawer_id,
                currency=payment.currency,
                defaults={'amount': Decimal('0')}
            )
            cash_drawer_money.amount += payment.amount
            cash_drawer_money.save()
        
        # Update sale payment status
        sale.update_payment_status()

    def _add_to_customer_account(self, sale):
        remaining_payment = round(sale.balance_due, 2)
        customer = sale.customer
        if remaining_payment > 0 and customer:

            remaining_payment_base = Currency.convert_to_base_currency(remaining_payment, sale.currency_id)
            customer.balance -= remaining_payment_base
            customer.save()   
        
            CustomerStatement.objects.create(
                tenant=sale.tenant,
                customer=sale.customer,
                amount=remaining_payment,
                currency=sale.currency,
                statement_type="loan",
                statement_date=sale.sale_date,
                sale=sale,
                notes=f"Loan for Sale #{sale.sale_number}",
                created_by_user=sale.created_by_user,
            )
       
    def _reverse_inventory_update(self, sale):
        """Create opposite stock movements to return items to inventory."""
        from inventory.models import StockMovement
        for item in sale.items.all():
            StockMovement.objects.create(
                tenant=sale.tenant,
                variant=item.inventory.variant,
                batch=item.inventory.batch,
                location=item.inventory.location,
                movement_type='sale_return', # Use a distinct type
                quantity=item.quantity, # Positive quantity to add it back
                reference_type='sale',
                reference_id=sale.id,
                notes=f"Reversal for updating Sale: {sale.sale_number}",
                created_by_user=sale.created_by_user
            )

    def _reverse_customer_account_update(self, sale):
        """Reverse the original loan amount from the customer's account."""
        # Find the original loan statement for this sale
        original_loan = CustomerStatement.objects.filter(
            sale=sale, 
            statement_type="loan"
        ).first()

        if original_loan and sale.customer:
            # Convert the loan amount back to the base currency to reverse it
            loan_amount_base = Currency.convert_to_base_currency(
                original_loan.amount, original_loan.currency_id
            )
            sale.customer.balance += loan_amount_base
            sale.customer.save()
            
            # It's often better to create a reversing entry than to delete
            CustomerStatement.objects.create(
                tenant=sale.tenant,
                customer=sale.customer,
                amount=-original_loan.amount, # Negative amount
                currency=original_loan.currency,
                statement_type="reversal",
                sale=sale,
                notes=f"Reversal for updating Sale #{sale.sale_number}",
                created_by_user=sale.created_by_user,
            )
            original_loan.delete() # Or mark as voided
         

class SaleListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing sales"""
    
    customer = serializers.SerializerMethodField()
    items_count = serializers.IntegerField(source='items.count', read_only=True)
    paid_amount = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    balance_due = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    
    user = serializers.CharField(
        source='created_by_user.get_full_name', read_only=True
    )
    items = serializers.SerializerMethodField()
    tenders = serializers.SerializerMethodField()

    type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = Sales
        fields = [
            'id', 'sale_number', 'customer', 'receipt_id',
            'sale_date', 'currency', 'payment_status', 'subtotal', 'total_amount', 'discount_amount',
            'status', 'type', 'items_count', 'paid_amount', 'balance_due', 'user', 'items', 'tenders',
        ]
    
    def get_type(self, obj):
        """Return type of sale"""
        return 'Cash' if obj.payment_status == 'paid' else 'Loan'

    def get_status(self, obj):
        """Return status of sale"""
        if obj.status == 'completed':
            return 'Processed'
        else:
            return 'Unprocessed'


    def get_customer(self, obj):
        """Return customer details as a dictionary"""
        if obj.customer:
            return {
                'id': obj.customer.id,
                'name': obj.customer.name,
                'balance': obj.customer.balance,
                'added_to_account': Currency.convert_to_base_currency(obj.balance_due, obj.currency_id),
            }
        return None

    def get_items(self, obj):
        """Return items in a structured format"""
        return [
            {
                'id': item.id,
                'inventory': item.inventory.id,
                'name': item.inventory.variant.variant_name,
                'quantity': item.quantity,
                'price': item.unit_price,
                'discount': item.discount_amount,
                'subtotal': item.line_total,
            }
            for item in obj.items.all()
        ]
        
    
    def get_tenders(self, obj):
        """Return payment details in a structured format"""
        payments = Payment.objects.filter(
            tenant=obj.tenant,
            reference_type='sale',
            reference_id=obj.id
        )
        return [
            {
                'id': payment.id,
                'amount': float(payment.amount),
                'currency': payment.currency.id,
                'cash_drawer': payment.cash_drawer.id if payment.cash_drawer else None,
                'notes': payment.notes,
            }
            for payment in payments.all()
        ]
    
   
class ReturnItemSerializer(serializers.ModelSerializer):
    """Serializer for return items"""
    
    variant_name = serializers.CharField(source='variant.variant_name', read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    original_quantity = serializers.CharField(source='sale_item.quantity', read_only=True)
    original_price = serializers.CharField(source='sale_item.unit_price', read_only=True)
    
    class Meta:
        model = ReturnItem
        fields = [
            'id', 'sale_item', 'variant', 'variant_name', 'product_name',
            'batch', 'quantity_returned', 'original_quantity', 'original_price',
            'condition', 'refund_amount', 'restocked', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, attrs):
        """Validate return item"""
        sale_item = attrs.get('sale_item')
        quantity_returned = attrs.get('quantity_returned')
        
        # Check if quantity doesn't exceed original quantity
        if quantity_returned > sale_item.quantity:
            raise serializers.ValidationError(
                {'quantity_returned': 'Cannot return more than original quantity.'}
            )
        
        # Check if item hasn't been fully returned already
        total_returned = ReturnItem.objects.filter(
            sale_item=sale_item
        ).aggregate(
            total=models.Sum('quantity_returned')
        )['total'] or Decimal('0')
        
        if total_returned + quantity_returned > sale_item.quantity:
            raise serializers.ValidationError(
                {'quantity_returned': 'Total return quantity exceeds original quantity.'}
            )
        
        return attrs


class ReturnCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating returns"""
    
    items = ReturnItemSerializer(many=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    sale_number = serializers.CharField(source='original_sale.sale_number', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Returns
        fields = [
            'id', 'return_number', 'original_sale', 'sale_number',
            'customer', 'customer_name', 'return_date', 'reason',
            'total_refund_amount', 'currency', 'currency_code', 'status',
            'processed_by_user', 'items', 'total_items',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'return_number', 'total_refund_amount',
            'created_at', 'updated_at'
        ]
    
    def validate(self, attrs):
        """Validate return data"""
        original_sale = attrs.get('original_sale')
        items_data = attrs.get('items', [])
        
        if not items_data:
            raise serializers.ValidationError(
                {'items': 'At least one item is required for return.'}
            )
        
        if not original_sale.can_be_returned():
            raise serializers.ValidationError(
                {'original_sale': 'This sale cannot be returned.'}
            )
        
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        """Create return with items"""
        items_data = validated_data.pop('items')
        request = self.context['request']
        tenant = request.user.tenant
        
        # Generate return number
        last_return = Returns.objects.filter(tenant=tenant).order_by('-id').first()
        if last_return:
            last_number = int(last_return.return_number.split('-')[-1])
            return_number = f"RET-{last_number + 1:06d}"
        else:
            return_number = "RET-000001"
        
        validated_data['return_number'] = return_number
        
        # Create return
        return_order = Returns.objects.create(**validated_data)
        
        # Create return items and calculate total refund
        total_refund = Decimal('0.00')
        
        for item_data in items_data:
            item_data['return_order'] = return_order
            item = ReturnItem.objects.create(**item_data)
            total_refund += item.refund_amount
        
        # Update return total
        return_order.total_refund_amount = total_refund
        return_order.save()
        
        return return_order
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """Update return"""
        items_data = validated_data.pop('items', [])
        
        # Update return basic info
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if items_data:
            # Remove existing items
            instance.items.all().delete()
            
            # Create new items
            total_refund = Decimal('0.00')
            
            for item_data in items_data:
                item_data['return_order'] = instance
                item = ReturnItem.objects.create(**item_data)
                total_refund += item.refund_amount
            
            # Update total
            instance.total_refund_amount = total_refund
        
        instance.save()
        return instance


class ReturnListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing returns"""
    
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    sale_number = serializers.CharField(source='original_sale.sale_number', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    items_count = serializers.IntegerField(source='items.count', read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Returns
        fields = [
            'id', 'return_number', 'sale_number', 'customer_name',
            'return_date', 'reason', 'total_refund_amount', 'currency_code',
            'status', 'items_count', 'total_items'
        ]