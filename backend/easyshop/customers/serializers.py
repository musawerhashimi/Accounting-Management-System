from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from finance.models import CashDrawerMoney, Transaction
from sales.serializers import SaleListSerializer
from .models import Customer, CustomerStatement
from core.models import Currency



class CustomerStatementSerializer(serializers.ModelSerializer):
    sale_receipt_id = serializers.CharField(source='sale.receipt_id', read_only=True)
    created_by_name = serializers.CharField(source='created_by_user.get_full_name', read_only=True)
    class Meta:
        model = CustomerStatement
        fields = [
            'id', 'customer', 'amount', 'currency', 'statement_type',
            'statement_date', 'sale', 'sale_receipt_id', 'cash_drawer', 'notes', 'created_by_name',
        ]
        read_only_fields = ['id', 'statement_date']
        write_only_fields = ['sale']

    def validate(self, attrs):
        # Ensure amount is positive
        if attrs.get('amount', Decimal('0')) <= 0:
            raise serializers.ValidationError("Amount must be a positive value.")
        
        # Validate that customer exists
        customer = attrs.get('customer')
        if not customer:
            raise serializers.ValidationError("Customer is required.")
        
        if not Customer.objects.filter(id=customer.id).exists():
            raise serializers.ValidationError("Customer does not exist.")
        
        # Validate that cash drawer exists if provided
        cash_drawer = attrs.get('cash_drawer')
        if cash_drawer and not CashDrawerMoney.objects.filter(cash_drawer=cash_drawer).exists():
            raise serializers.ValidationError("Cash drawer does not exist.")
        
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        # validated_data['created_by_user'] = request.user

        # Create the CustomerStatement
        statement = CustomerStatement.objects.create(**validated_data)

        Transaction.objects.create(
            tenant=statement.tenant,
            transaction_date=statement.statement_date,
            amount=statement.amount,
            currency=statement.currency,
            description=f"Customer Statement for #{statement.customer.name} - {statement.statement_type}",
            party_type='customer',
            party_id=statement.customer.pk,
            transaction_type='income' if statement.statement_type=="cash" else "expense",
            reference_type='statement',
            reference_id=statement.pk,
            cash_drawer=statement.cash_drawer,
            created_by_user=statement.created_by_user
        )
        # Update or create CashDrawerMoney
        cash_drawer = validated_data.get('cash_drawer')
        currency = validated_data.get('currency')
        amount = validated_data.get('amount')
        
        if validated_data["statement_type"] == "loan":
            amount = -amount
        customer = validated_data.get("customer")
        base_amount = Currency.convert_to_base_currency(amount, currency.id)
        
        customer.balance += base_amount
        customer.save()
        if cash_drawer and currency:
            drawer_money, _ = CashDrawerMoney.objects.get_or_create(
                cash_drawer=cash_drawer,
                currency=currency,
            )
            drawer_money.amount += amount
            drawer_money.save()

        return statement


class CustomerSalesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'balance',
        ]
        read_only_fields = ['id']


class CustomerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for customer lists"""
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_number', 'name',
            'email', 'phone', 'address', 'balance'
        ]


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for customer CRUD operations"""
    
    # Computed fields
    total_purchases = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    purchase_count = serializers.IntegerField(read_only=True)
    last_purchase_date = serializers.DateField(read_only=True)
    sales = SaleListSerializer(many=True, read_only=True)

    # Related field names
    created_by_user_name = serializers.CharField(source='created_by_user.get_full_name', read_only=True)
    gender = serializers.CharField(source='get_gender_display')
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_number', 'name', 'gender', 
            'photo', 'email', 'phone',
            'discount_percentage', 'balance', 
            'date_joined', 'status', 'notes',
            'birth_date', 'total_purchases',
            'purchase_count', 'last_purchase_date',
            'total_purchases', 'purchase_count',
            'address', 'city',
            'created_by_user_name', 'sales'
        ]
        read_only_fields = [
            'id', 'customer_number', 'full_name', 'date_joined', 
            'total_purchases', 'purchase_count', 'last_purchase_date',
            'available_credit', 'is_over_credit_limit', 'created_by_user_name',
            'sales_rep_name', 'preferred_currency_code', 'contacts', 
            'addresses', 'group_memberships', 'notes', 'created_at', 'updated_at'
        ]

    def validate_email(self, value):
        if value:
            request = self.context.get('request')
            if request and hasattr(request, 'user') and hasattr(request.user, 'tenant_id'):
                tenant_id = request.user.tenant_id
                existing = Customer.objects.filter(
                    tenant_id=tenant_id, 
                    email__iexact=value
                )
                if self.instance:
                    existing = existing.exclude(pk=self.instance.pk)
                if existing.exists():
                    raise serializers.ValidationError("Customer with this email already exists.")
        return value

    def validate_credit_limit(self, value):
        if value < 0:
            raise serializers.ValidationError("Credit limit cannot be negative.")
        return value

    def validate_discount_percentage(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Discount percentage must be between 0 and 100.")
        return value

    def validate(self, data):
        
        # Validate birth_date is not in future
        if data.get('birth_date') and data['birth_date'] > timezone.now().date():
            raise serializers.ValidationError({
                'birth_date': 'Birth date cannot be in the future.'
            })
        
        return data


class CustomerCreateSerializer(serializers.ModelSerializer):
    """Serializer for customer creation with required fields"""
    
    class Meta:
        model = Customer
        fields = [
            'name', 'birth_date', 'email',
            'phone', 'address', 'city',
            'photo', 'gender'
        ]
    
    
    def validate_email(self, value):
        if value:
            existing = Customer.objects.filter(
                email__iexact=value
            )
            if existing.exists():
                raise serializers.ValidationError("Customer with this email already exists.")
        return value
    
    def validate_name(self, name):
        customers = Customer.objects.filter(name=name)
        if customers.exists():
            raise serializers.ValidationError(f"{name} Already Exists")
        return name
    
    def validate(self, data):    
        # Validate birth_date is not in future
        if data.get('birth_date') and data['birth_date'] > timezone.now().date():
            raise serializers.ValidationError({
                'birth_date': 'Birth date cannot be in the future.'
            })
        
        return data


class CustomerUpdateSerializer(serializers.ModelSerializer):
    """Lightweight serializer for customer updates"""
    
    class Meta:
        model = Customer
        fields = [
            'name', 'birth_date', 'email',
            'phone', 'address', 'city',
            'gender'
        ]

    def validate_email(self, value):
        if value:
            existing = Customer.objects.filter(
                email__iexact=value
            ).exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError("Customer with this email already exists.")
        return value


class CustomerStatsSerializer(serializers.Serializer):
    """Serializer for customer statistics"""
    total_customers = serializers.IntegerField()
    active_customers = serializers.IntegerField()
    new_customers_this_month = serializers.IntegerField()
    customers_over_credit_limit = serializers.IntegerField()
    total_customer_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_customer_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    top_customers = CustomerListSerializer(many=True)
