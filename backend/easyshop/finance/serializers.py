from rest_framework import serializers
from django.db import transaction
from decimal import Decimal
from django.db.models import Sum
from accounts.models import Employee
from core.models import Currency
from customers.models import Customer
from hr.models import Member
from vendors.models import Vendor
from .models import (
    CashDrawer, CashDrawerMoney, Payment, Transaction, 
    ExpenseCategory, Expense, MonthlyPayment
)
from django.utils import timezone


class CashDrawerMoneySerializer(serializers.ModelSerializer):

    value = serializers.DecimalField(source="amount", max_digits=15, decimal_places=2, default=Decimal('0.00'))
    class Meta:
        model = CashDrawerMoney
        fields = [
            'id', 'currency',
            'value',
        ]
        read_only_fields = ['id']


class CashDrawerSerializer(serializers.ModelSerializer):
    amounts = CashDrawerMoneySerializer(many=True, read_only=True, source="cash_drawer_money")
    total_balance = serializers.ReadOnlyField()

    class Meta:
        model = CashDrawer
        fields = [
            'id', 'name', 'location', 'description',
            'amounts', 'total_balance',
        ]
        read_only_fields = ['id', 'created_by_user', 'created_at', 'updated_at']

    def validate(self, data):
        # Check if cash drawer with same name exists in same location
        if self.instance:
            existing = CashDrawer.objects.filter(
                # tenant=self.context['request'].user.tenant,
                name=data.get('name', self.instance.name),
                location=data.get('location', self.instance.location)
            ).exclude(id=self.instance.id).first()
        else:
            existing = CashDrawer.objects.filter(
                # tenant=self.context['request'].user.tenant,
                name=data['name'],
                location=data['location']
            ).first()
        
        if existing:
            raise serializers.ValidationError(
                "A cash drawer with this name already exists in this location."
            )
        
        return data

    @transaction.atomic
    def create(self, validated_data):
        cash_drawer = super().create(validated_data)
        base_currency = Currency.get_base_currency()
        CashDrawerMoney.objects.create(
            cash_drawer=cash_drawer,
            currency=base_currency
        )
        return cash_drawer


class TransactionCreateSerializer(serializers.ModelSerializer):
    transaction_type = serializers.ChoiceField(choices=["pay", "receive"])
    party_type = serializers.ChoiceField(choices=["employees", "members", "customers", "vendors"])
    party_id = serializers.IntegerField()
    currency = serializers.PrimaryKeyRelatedField(queryset=Currency.objects.all())
    cash_drawer = serializers.PrimaryKeyRelatedField(queryset=CashDrawer.objects.all())
    description = serializers.CharField(required=False, allow_blank=True)
    transaction_date = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = Transaction
        fields = [
            'transaction_type',
            'party_type',
            'party_id',
            'amount',
            'currency',
            'cash_drawer',
            'description',
            'transaction_date'
        ]

    def validate(self, attrs):
        if attrs['amount'] <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return attrs

    def get_party_object(self, category, pk):
        if category == "employees":
            model = Employee
        elif category == "customers":
            model = Customer
        elif category == "members":
            model = Member
        elif category == "vendors":
            model = Vendor
        else:
            raise serializers.ValidationError("Invalid transaction category")

        try:
            return model.objects.get(pk=pk)
        except model.DoesNotExist:
            raise serializers.ValidationError(f"{category[:-1].capitalize()} Not Found!")


    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        type_map = {"pay": "expense", "receive": "income"}
        tx_type = type_map[validated_data["transaction_type"]]
        transaction_date = validated_data.get('transaction_date', timezone.now())
        party_obj = self.get_party_object(validated_data["party_type"], validated_data["party_id"])
        tenant = request.tenant
        
        # 1. Create Transaction
        transaction = Transaction.objects.create(
            tenant=tenant,
            transaction_date=transaction_date,
            amount=validated_data["amount"],
            currency=validated_data["currency"],
            description=validated_data.get("description", ""),
            party_type=validated_data["party_type"][:-1],  # "employees" -> "employee"
            party_id=party_obj.id,
            transaction_type=tx_type,
            cash_drawer=validated_data['cash_drawer'],
            created_by_user=request.user,
            is_direct=True
        )

        # 2. Create Payment
        payment = Payment.objects.create(
            tenant=tenant,
            amount=validated_data["amount"],
            currency=validated_data["currency"],
            payment_method="cash",
            payment_date=transaction_date,
            reference_type=validated_data['party_type'],
            reference_id=party_obj.id,
            cash_drawer=validated_data.get("cash_drawer"),
            created_by_user=request.user
        )

        # 3. Update CashDrawerMoney
        drawer = validated_data["cash_drawer"]
        currency = validated_data["currency"]
        is_income = tx_type == "income"

        drawer_money, _ = CashDrawerMoney.objects.get_or_create(
            cash_drawer=drawer,
            currency=currency,
        )

        if is_income:
            amount = validated_data["amount"]
        else:
            amount = -validated_data["amount"]

        drawer_money.amount += amount
        drawer_money.save()

        amount = Currency.convert_to_base_currency(amount, validated_data['currency'].pk)
        
        # 4. Update party balance
        party_obj.balance += amount
        party_obj.save()

        return transaction


class DirectTransactionsSerializer(serializers.ModelSerializer):
    party_name = serializers.SerializerMethodField()
    transaction_type = serializers.SerializerMethodField()
    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_date', 'amount', 'currency',
            'description', 'party_type', 'party_name', 'transaction_type',
            'cash_drawer_id',
        ]
        read_only_fields = ['id']
        
    def get_party_name(self, obj):
        party = obj.party_type
        if party == "employee":
            model = Employee
        elif party == "customers":
            model = Customer
        elif party == "member":
            model = Member
        elif party == "vendor":
            model = Vendor
        
        try:
            obj = model.objects.get(pk=obj.party_id)
            return obj.name
        except model.DoesNotExist:
            return None
    
    def get_transaction_type(self, obj):
        return "receive" if obj.transaction_type == "income" else "pay"


class TransactionSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    cash_drawer_name = serializers.CharField(source='cash_drawer.name', read_only=True)
    created_by_user_name = serializers.CharField(source='created_by_user.get_full_name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_date', 'amount', 'currency', 'currency_code', 'currency_symbol',
            'description', 'party_type', 'party_id', 'transaction_type',
            'reference_type', 'reference_id', 'cash_drawer', 'cash_drawer_name',
            'created_by_user', 'created_by_user_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ExpenseCategorySerializer(serializers.ModelSerializer):
    # parent_category_name = serializers.CharField(source='parent_category.name', read_only=True)
    # subcategories = serializers.SerializerMethodField()
    # full_path = serializers.ReadOnlyField()
    # total_expenses = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseCategory
        fields = [
            'id', 'name', 'description',
        ]

    def validate_name(self, name):
        """Ensure category name is unique within parent category"""
        expenses = ExpenseCategory.objects.filter(name=name)
        if self.instance:
            expenses = expenses.exclude(id=self.instance.id)            
        if expenses.exists():
            raise serializers.ValidationError("Category with this name already exists.")
        return name

    # def get_subcategories(self, obj):
    #     if hasattr(obj, 'subcategories'):
    #         return ExpenseCategorySerializer(obj.subcategories.filter(is_active=True), many=True).data
    #     return []

    # def get_total_expenses(self, obj):
    #     """Get total expenses for this category this month"""
    #     from django.utils import timezone
    #     from datetime import datetime
        
    #     current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    #     return obj.expenses.filter(
    #         expense_date__gte=current_month,
    #         status__in=['approved', 'paid']
    #     ).count()

    # def validate(self, data):
    #     # Prevent circular parent-child relationships
    #     if data.get('parent_category') and self.instance:
    #         parent = data['parent_category']
    #         current = self.instance
            
    #         # Check if parent is a descendant of current category
    #         while parent:
    #             if parent == current:
    #                 raise serializers.ValidationError(
    #                     "Cannot set parent category to a descendant of this category."
    #                 )
    #             parent = parent.parent_category
        
    #     return data


class ExpenseSerializer(serializers.ModelSerializer):
    expense_category_name = serializers.CharField(source='expense_category.full_path', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'expense_number',
            'expense_category', 'expense_category_name', 'amount', 'currency',
            'expense_date', 'description', 'cash_drawer',
        ]
        read_only_fields = ['id', 'expense_number', 'expense_date',]
        write_only_fields = ['expense_category']

    @transaction.atomic
    def create(self, validated_data):
        expense = Expense.objects.create(**validated_data)
        # 1. Create Transaction
        transaction = Transaction.objects.create(
            tenant=expense.tenant,
            transaction_date=expense.expense_date,
            amount=expense.amount,
            currency=expense.currency,
            description=expense.description or f"Payment for expense: {expense.expense_number} - {expense.amount} {expense.currency.code}",
            party_type="other",
            transaction_type="expense",
            reference_type="expense",
            reference_id=expense.id,
            cash_drawer=expense.cash_drawer,
            created_by_user=expense.created_by_user,
        )

        # 2. Create Payment
        payment = Payment.objects.create(
            tenant=expense.tenant,
            amount=expense.amount,
            currency=expense.currency,
            payment_method="cash",
            payment_date=expense.expense_date,
            reference_type="expense",
            reference_id=expense.id,
            cash_drawer=expense.cash_drawer,
            created_by_user=expense.created_by_user
        )

        # 3. Update CashDrawerMoney
        drawer = expense.cash_drawer
        currency = expense.currency
        amount = expense.amount
        
        drawer_money, _ = CashDrawerMoney.objects.get_or_create(
            cash_drawer=drawer,
            currency=currency,
        )
        
        drawer_money.amount -= amount
        drawer_money.save()
        return expense

    
class MonthlyPaymentSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    next_due_date = serializers.SerializerMethodField()

    class Meta:
        model = MonthlyPayment
        fields = [
            'id', 'name', 'amount', 'currency', 'currency_code', 'currency_symbol',
            'payment_method', 'start_date', 'end_date', 'payment_day',
            'reference_type', 'reference_id',
            'is_active', 'description', 'next_due_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_next_due_date(self, obj):
        """Get next due date for this monthly payment"""
        from datetime import date, datetime
        from dateutil.relativedelta import relativedelta
        
        if not obj.is_active:
            return None
        
        today = date.today()
        
        # Start from current month
        current_month = today.replace(day=1)
        
        # Check next 12 months
        for i in range(12):
            check_date = current_month + relativedelta(months=i)
            payment_date = date(check_date.year, check_date.month, min(obj.payment_day, 28))
            
            if payment_date >= today and obj.is_due_for_month(check_date.year, check_date.month):
                return payment_date
        
        return None

    def validate(self, data):
        # Validate payment day
        payment_day = data.get('payment_day')
        if payment_day and (payment_day < 1 or payment_day > 31):
            raise serializers.ValidationError(
                "Payment day must be between 1 and 31."
            )
        
        # Validate date range
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                "End date must be after start date."
            )
        
        return data

    
# Specialized serializers for reports and analytics
class CashFlowSummarySerializer(serializers.Serializer):
    """Summary of cash flow for a period"""
    period = serializers.CharField()
    total_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_cash_flow = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency_code = serializers.CharField()


class ExpenseSummarySerializer(serializers.Serializer):
    """Expense summary by category"""
    category_name = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    expense_count = serializers.IntegerField()
    currency_code = serializers.CharField()


class DepartmentSalesReportSerializer(serializers.Serializer):
    department_id = serializers.IntegerField()
    department = serializers.CharField()
    total_quantity = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_sold = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=15, decimal_places=2)


class TransactionSerializer(serializers.ModelSerializer):
    cash_drawer_name = serializers.CharField(source='cash_drawer.name')
    created_by_name = serializers.CharField(source='created_by_user.get_full_name')
    class Meta:
        model = Transaction
        fields = ['id', 'party_type', 'reference_type', 'description', 'amount', 'currency', 'transaction_type', 'cash_drawer', 'transaction_date', 'cash_drawer_name', 'created_by_name']
        
        
class CashDrawerMoneyReportSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()

    class Meta:
        model = CashDrawerMoney
        fields = ['id', 'currency', 'amount']

    def get_amount(self, obj):
        # Get filter context passed from view
        start = self.context.get('start')
        end = self.context.get('end')

        # Get all transactions for this drawer and currency in the range
        txns = Transaction.objects.filter(
            cash_drawer=obj.cash_drawer,
            currency=obj.currency,
            transaction_date__date__range=[start, end]
        ).values('transaction_type').annotate(total=Sum('amount'))

        came = Decimal("0.00")
        gone = Decimal("0.00")

        for tx in txns:
            if tx["transaction_type"] in ["income", "transfer"]:
                came += tx["total"] or Decimal("0.00")
            elif tx["transaction_type"] == "expense":
                gone += tx["total"] or Decimal("0.00")
        net = came - gone

        # Final amount = current amount + net movement
        return str(obj.amount + net)


class CashDrawerReportSerializer(serializers.ModelSerializer):
    amounts = CashDrawerMoneyReportSerializer(many=True, source='cash_drawer_money')
    class Meta:
        model = CashDrawer
        fields = ['id', 'name', 'description', 'location', 'amounts']



from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from .models import  Transaction, Expense
from core.models import Currency


class MonthlyReportSerializer(serializers.Serializer):
    date = serializers.CharField()
    sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    netProfit = serializers.DecimalField(max_digits=15, decimal_places=2)


#--------------------new code----------------
# serializers.py

from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal
from core.models import CurrencyRate
from sales.models import SaleItem
from catalog.models import ProductPrice
from customers.models import Customer, Currency


class SaleItemDetailSerializer(serializers.ModelSerializer):
    # Basic item info
    barcode = serializers.SerializerMethodField()
    item = serializers.SerializerMethodField()
    price = serializers.DecimalField(source='unit_price', max_digits=15, decimal_places=4, read_only=True)
    profit = serializers.SerializerMethodField()
    discount = serializers.DecimalField(source='discount_amount', max_digits=15, decimal_places=4, read_only=True)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=4, read_only=True)
    
    # Location and categorization
    location = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    
    # Sale info
    session_no = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    customer_acc_name = serializers.SerializerMethodField()
    
    # Cost and financial data
    cost = serializers.SerializerMethodField()
    currency = serializers.IntegerField(source='sale.currency_id')
    line_total = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    total_cost = serializers.SerializerMethodField()

    class Meta:
        model = SaleItem
        fields = [
            'id', 'barcode', 'item', 'price', 'profit', 'discount', 
            'quantity', 'location', 'department', 'category', 
            'session_no', 'date', 'customer_acc_name', 'cost', 
            'currency', 'line_total', 'total_cost'
        ]

    def get_barcode(self, obj):
        """Get barcode from product variant"""
        return obj.inventory.variant.barcode if obj.inventory and obj.inventory.variant else None

    def get_item(self, obj):
        """Get item name from product variant"""
        if obj.inventory and obj.inventory.variant:
            return str(obj.inventory.variant)
        return None

    def get_location(self, obj):
        """Get location name where item was sold from"""
        if obj.inventory and obj.inventory.location:
            return obj.inventory.location.name
        return None

    def get_department(self, obj):
        """Get department name"""
        if obj.inventory and obj.inventory.variant and obj.inventory.variant.product:
            return obj.inventory.variant.product.category.department.name
        return None

    def get_category(self, obj):
        """Get category name"""
        if obj.inventory and obj.inventory.variant and obj.inventory.variant.product:
            return obj.inventory.variant.product.category.name
        return None

    def get_session_no(self, obj):
        """Get sale number as session number"""
        return obj.sale.receipt_id

    def get_date(self, obj):
        """Get sale date"""
        return obj.sale.sale_date

    def get_customer_acc_name(self, obj):
        """Get customer account name"""
        if obj.sale.customer:
            return obj.sale.customer.name
        return None

    def get_currency(self, obj):
        """Get sale currency"""
        return {
            'code': obj.sale.currency.code,
            'symbol': obj.sale.currency.symbol,
            'name': obj.sale.currency.name
        }

    def get_cost(self, obj):
        """Get cost price effective on sale date, converted to sale currency"""
        if not (obj.inventory and obj.inventory.variant):
            return Decimal('0.00')

        variant = obj.inventory.variant
        sale_date = obj.sale.sale_date
        sale_currency = obj.sale.currency

        # Get cost price effective on sale date
        cost_price_record = ProductPrice.objects.filter(
            variant=variant,
            effective_date__lte=sale_date,
            end_date__isnull=True
        ).order_by('-effective_date').first()

        if not cost_price_record:
            # Fallback to any current price
            cost_price_record = ProductPrice.objects.filter(
                variant=variant,
                is_current=True
            ).first()

        if not cost_price_record:
            return Decimal('0.00')

        cost_price = cost_price_record.cost_price
        cost_currency = cost_price_record.cost_currency

        # Convert to sale currency if different
        if cost_currency.id != sale_currency.id:
            # Get exchange rate effective on sale date
            cost_rate = self._get_exchange_rate(cost_currency, sale_date)
            sale_rate = self._get_exchange_rate(sale_currency, sale_date)
            
            if cost_rate and sale_rate:
                # Convert to base currency then to sale currency
                base_amount = cost_price / cost_rate
                converted_cost = base_amount * sale_rate
                return converted_cost
            else:
                # Fallback to current conversion
                return cost_currency.convert_to(cost_price, sale_currency.id)
        
        return cost_price

    def get_total_cost(self, obj):
        """Calculate total cost (cost * quantity)"""
        cost = self.get_cost(obj)
        return cost * obj.quantity

    def get_profit(self, obj):
        """Calculate profit (line_total - total_cost)"""
        total_cost = self.get_total_cost(obj)
        return obj.line_total - total_cost

    def _get_exchange_rate(self, currency, date):
        """Get exchange rate effective on a specific date"""
        rate_record = CurrencyRate.objects.filter(
            currency=currency,
            effective_date__lte=date
        ).order_by('-effective_date').first()
        
        return rate_record.rate if rate_record else currency.exchange_rate
    

class YearlyReportSerializer(serializers.Serializer):
    month = serializers.CharField()
    sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    netProfit = serializers.DecimalField(max_digits=15, decimal_places=2)
        