from arrow import now
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.db import transaction

from accounts.models import Employee
from core.models import Currency
from catalog.models import ProductPrice
from core.permissions import TenantPermissionMixin
from core.utils import get_cached_exchange_rate
from customers.models import Customer
from hr.models import Member
from vendors.models import Vendor
from .models import (
    CashDrawer, CashDrawerMoney, Payment, Transaction, 
    ExpenseCategory, Expense, MonthlyPayment
)
from .serializers import (
    CashDrawerSerializer,
    CashDrawerReportSerializer, CashDrawerMoneySerializer, DepartmentSalesReportSerializer, DirectTransactionsSerializer,
    MonthlyReportSerializer,
    SaleItemDetailSerializer, TransactionCreateSerializer, TransactionSerializer, ExpenseCategorySerializer,
    ExpenseSerializer, MonthlyPaymentSerializer, CashFlowSummarySerializer,
    ExpenseSummarySerializer, YearlyReportSerializer
)
from .filters import (
    TransactionFilter
)


class CashDrawerViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    """ViewSet for managing cash drawers"""
    queryset = CashDrawer.objects.all()
    serializer_class = CashDrawerSerializer
    permission_module = 'finance'
    ordering = ['-created_at']

    @action(detail=True, methods=['get'])
    def balance_by_currency(self, request, pk=None):
        """Get cash drawer balance by currency"""
        cash_drawer = self.get_object()
        balances = CashDrawerMoney.objects.filter(cash_drawer=cash_drawer)
        serializer = CashDrawerMoneySerializer(balances, many=True)
        return Response(serializer.data)


class TransactionViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    """ViewSet for managing transactions"""
    permission_module = 'finance'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TransactionFilter
    search_fields = ['description']
    ordering_fields = ['transaction_date', 'amount', 'transaction_type', 'created_at']
    ordering = ['-transaction_date']
    queryset = Transaction.objects.all()
    
    def get_serializer_class(self):
        if self.action == "create":
            return TransactionCreateSerializer
        return TransactionSerializer

    @action(detail=False, methods=['get'])
    def cash_flow(self, request):
        """Get cash flow summary for a period"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            # Default to current month
            now = timezone.now()
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        transactions = self.get_queryset().filter(
            transaction_date__range=[start_date, end_date]
        )
        
        summary = transactions.values('currency__code').annotate(
            total_income=Sum('amount', filter=Q(transaction_type='income')),
            total_expense=Sum('amount', filter=Q(transaction_type='expense'))
        )
        
        result = []
        for item in summary:
            income = item['total_income'] or Decimal('0.00')
            expense = item['total_expense'] or Decimal('0.00')
            result.append({
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'total_income': income,
                'total_expenses': expense,
                'net_cash_flow': income - expense,
                'currency_code': item['currency__code']
            })
        
        serializer = CashFlowSummarySerializer(result, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def parties(self, request):
        parties = [Vendor, Customer, Employee, Member]
        
        data = {
            f"{party.__name__.lower()}s":  party.objects.all().values('id', 'name') for party in parties
        }
        return Response(
            data
        )
   
    @action(detail=False, methods=['GET'], url_path='direct-transactions')
    def direct_transactions(self, request):
        queryset = Transaction.objects.filter(is_direct=True)
        serializer = DirectTransactionsSerializer(queryset, many=True)
        return Response(
            serializer.data,
        )
        
        
class ExpenseCategoryViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    """ViewSet for managing expense categories"""
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_module = 'finance'
    ordering = ['name']

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get categories in tree structure"""
        categories = self.get_queryset().filter(parent_category__isnull=True)
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)


class ExpenseViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    """ViewSet for managing expenses"""
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_module = 'finance'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering = ['-expense_date']

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):        # 1. Restore CashDrawerMoney
        instance = self.get_object()
        drawer_money = CashDrawerMoney.objects.filter(
            cash_drawer=instance.cash_drawer,
            currency=instance.currency
        ).first()
        
        if drawer_money:
            drawer_money.amount += instance.amount
            drawer_money.save()

        # 2. Delete related Payment and Transaction
        Payment.objects.filter(
            reference_type="expense",
            reference_id=instance.id
        ).delete()

        Transaction.objects.filter(
            reference_type="expense",
            reference_id=instance.id
        ).delete()

        # 3. Delete the expense itself
        return super().destroy(request, *args, **kwargs)
        
    @action(detail=False, methods=['get'])
    def summary_by_category(self, request):
        """Get expense summary by category"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = self.get_queryset().filter(status__in=['approved', 'paid'])
        
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(expense_date__range=[start_date, end_date])
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        summary = queryset.values(
            'expense_category__name', 'currency__code'
        ).annotate(
            total_amount=Sum('amount'),
            expense_count=Count('id')
        ).order_by('-total_amount')
        
        result = []
        for item in summary:
            result.append({
                'category_name': item['expense_category__name'],
                'total_amount': item['total_amount'],
                'expense_count': item['expense_count'],
                'currency_code': item['currency__code']
            })
        
        serializer = ExpenseSummarySerializer(result, many=True)
        return Response(serializer.data)


class MonthlyPaymentViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    """ViewSet for managing monthly payments"""
    queryset = MonthlyPayment.objects.all()
    serializer_class = MonthlyPaymentSerializer
    permission_module = 'finance'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering = ['payment_day', 'name']

    @action(detail=False, methods=['get'])
    def references(self, request):
        data = {
            "expense_categories": ExpenseCategory.objects.all().values('id', 'name'),
            "employees": Employee.objects.all().values('id', 'name')
        }
        return Response(
            data
        )


    @action(detail=False, methods=['get'])
    def due_this_month(self, request):
        """Get monthly payments due this month"""
        now = timezone.now()
        year = now.year
        month = now.month
        
        due_payments = []
        for payment in self.get_queryset().filter(is_active=True):
            if payment.is_due_for_month(year, month):
                due_payments.append(payment)
        
        serializer = self.get_serializer(due_payments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def create_expense(self, request, pk=None):
        """Create expense for this monthly payment"""
        monthly_payment = self.get_object()
        year = request.data.get('year', timezone.now().year)
        month = request.data.get('month', timezone.now().month)
        
        try:
            year = int(year)
            month = int(month)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid year or month'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not monthly_payment.is_due_for_month(year, month):
            return Response(
                {'error': 'Payment is not due for this month'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense = monthly_payment.create_expense_for_month(year, month, request.user)
        
        if expense:
            serializer = ExpenseSerializer(expense)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'error': 'Failed to create expense'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def generate_monthly_expenses(self, request):
        """Generate expenses for all due monthly payments"""
        year = request.data.get('year', timezone.now().year)
        month = request.data.get('month', timezone.now().month)
        
        try:
            year = int(year)
            month = int(month)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid year or month'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_expenses = []
        
        for monthly_payment in self.get_queryset().filter(is_active=True):
            if monthly_payment.is_due_for_month(year, month):
                expense = monthly_payment.create_expense_for_month(year, month, request.user)
                if expense:
                    created_expenses.append(expense)
        
        return Response({
            'message': f'Created {len(created_expenses)} expenses for {year}-{month:02d}',
            'created_count': len(created_expenses)
        })
        
        
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Sum, F
from datetime import datetime

from sales.models import SaleItem, Sales


class QuickReportViewSet(viewsets.ViewSet):
    """
    A ViewSet for generating quick reports like total sales, purchases, etc.
    """

    @action(detail=False, methods=["get"])
    def summary(self, request):
        filter_type = request.query_params.get("filter", "today")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        today = now().date()
        if filter_type == "today":
            start = end = today
        elif filter_type == "yesterday":
            start = end = today - timedelta(days=1)
        elif filter_type == "date_range":
            if not (start_date and end_date):
                return Response({"error": "start_date and end_date required"}, status=400)
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)
            start, end = start_date, end_date
        else:
            return Response({"error": "Invalid filter"}, status=400)
        sale_items = (
            SaleItem.objects
            .annotate(sale_date_only=TruncDate('sale__sale_date'))
            .filter(
            sale_date_only__range=[start, end],
            sale__tenant=request.tenant  # Filter by tenant from request
            )
            .select_related(
            'sale',
            'inventory__variant',
            'sale__currency',
            'inventory__variant__product__category__department'
            ).prefetch_related(
            'inventory__variant__variant_prices'  # Prefetch prices to reduce queries
            )
        )

        department_report = {}

        for item in sale_items:
            sale_date = item.sale.sale_date.date()
            # if not (start <= sale_date <= end):
            #     continue
            department = item.inventory.variant.product.category.department
            if not department:
                continue

            department_key = department.id
            department_name = department.name

            sale_currency = item.sale.currency
            sale_rate = get_cached_exchange_rate(sale_currency.id, sale_date)
            total_sold = item.line_total / sale_rate
            product_price = (
                ProductPrice.objects
                .filter(variant=item.inventory.variant, is_current=True)
                .order_by("-effective_date")
                .first()
            )
            cost_price = Decimal("0.0")
            cost_currency = None

            if product_price:
                cost_price = product_price.cost_price
                cost_currency = product_price.cost_currency
            cost_rate = get_cached_exchange_rate(cost_currency.id, sale_date) if cost_currency else Decimal("1")

            total_cost = (cost_price * item.quantity) / cost_rate
            profit = total_sold - total_cost

            if department_key not in department_report:
                department_report[department_key] = {
                    "department_id": department_key,
                    "department": department_name,
                    "total_quantity": Decimal("0.0"),
                    "total_sold": Decimal("0.0"),
                    "total_cost": Decimal("0.0"),
                    "total_profit": Decimal("0.0"),
                }

            d = department_report[department_key]
            d["total_quantity"] += item.quantity
            d["total_sold"] += total_sold
            d["total_cost"] += total_cost
            d["total_profit"] += profit

        department_data = DepartmentSalesReportSerializer(department_report.values(), many=True).data


        # -------- Transactions -------- #
        transactions = Transaction.objects.filter(transaction_date__date__range=[start, end])
        transaction_data = TransactionSerializer(transactions, many=True).data

        # -------- Cash Drawers -------- #
        cash_drawers = CashDrawer.objects.prefetch_related("cash_drawer_money").all()
        cash_drawer_data = CashDrawerReportSerializer(
            cash_drawers,
            many=True,
            context={"start": start, "end": end}
        ).data


        revenue = Decimal("0.00")
        total_cost = Decimal("0.00")

        for item in sale_items:
            quantity = item.quantity
            line_total = item.line_total
            sale_currency_id = item.sale.currency_id
            sale_date = item.sale.sale_date.date()
            # Get product price
            product_price = ProductPrice.objects.filter(
                variant=item.inventory.variant,
            ).filter(
                # Q(is_current=True) |
                Q(effective_date__lte=sale_date) | (Q(end_date__gte=sale_date) &
                Q(end_date__isnull=True))
            ).order_by("-effective_date").first()

            if not product_price:
                continue

            cost_price = product_price.cost_price
            cost_currency_id = product_price.cost_currency_id

            # Exchange rates
            sell_rate = get_cached_exchange_rate(sale_currency_id, sale_date)  # Assuming 1 is base
            cost_rate = get_cached_exchange_rate(cost_currency_id, sale_date)
            
            # Add revenue
            revenue += line_total / sell_rate

            # Add true cost
            total_cost += (cost_price * quantity) / cost_rate

        profit = revenue - total_cost
        net_profit = profit  # You can subtract expenses here if needed later        
        
        return Response({
            "department_sales": department_data,
            "transactions": transaction_data,
            "cash_drawers": cash_drawer_data,
            "sales_summary": {
                "revenue": round(revenue, 2),
                "cost": round(total_cost, 2),
                "profit": round(profit, 2),
                "net_profit": round(net_profit, 2),
            }
        })

    @action(detail=False, methods=["get"])
    def top_products(self, request):
        """
        Return top 5 selling products between two dates.
        """
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # Validate dates
        if not start_date or not end_date:
            return Response({"detail": "start_date and end_date are required."}, status=400)

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        top_products = (
            Sales.objects
            .filter(sale_date__range=(start, end))
            .values(name=F("item__name"))
            .annotate(total_quantity=Sum("quantity"))
            .order_by("-total_quantity")[:5]
        )

        return Response(top_products)



#-----------------------------------------------------

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Q, F
from decimal import Decimal
from datetime import datetime, date
from calendar import monthrange


class MonthlyReportViewSet(viewsets.ViewSet):
    
    
    @action(detail=False, methods=['get'], url_path="monthly-report")
    def monthly_report(self, request):
        """
        Generate monthly report with daily breakdown
        Parameters: year, month
        """
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        
        if not year or not month:
            return Response(
                {'error': 'Year and month parameters are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            year = int(year)
            month = int(month)
            if not (1 <= month <= 12):
                raise ValueError("Month must be between 1 and 12")
        except ValueError as e:
            return Response(
                {'error': f'Invalid year or month: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get number of days in the month
        _, days_in_month = monthrange(year, month)
        
        # Get base currency
        try:
            base_currency = Currency.get_base_currency()
        except Exception:
            return Response(
                {'error': 'Base currency not configured'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        report_data = []
        
        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)
            
            # Calculate daily metrics
            daily_sales = self._calculate_daily_sales(current_date, base_currency)
            daily_expenses = self._calculate_daily_expenses(current_date, base_currency)
            daily_cost = self._calculate_daily_cost(current_date, base_currency)
            
            # Calculate profit and net profit
            profit = daily_sales - daily_cost
            net_profit = profit - daily_expenses
            
            report_data.append({
                'date': str(day),
                'sales': round(daily_sales, 2),
                'expense': round(daily_expenses, 2),
                'cost': round(daily_cost, 2),
                'profit': round(profit, 2),
                'netProfit': round(net_profit, 2)
            })
        
        serializer = MonthlyReportSerializer(report_data, many=True)
        return Response(serializer.data)
    
    def _calculate_daily_sales(self, target_date, base_currency):
        """Calculate total sales for a specific day in base currency"""
        sales = Sales.objects.filter(
            sale_date__date=target_date,
            tenant=self.request.user.tenant
        )
        
        total_sales = Decimal('0.00')
        
        for sale in sales:
            # Convert sale total to base currency using rate effective on sale date
            if sale.currency.id == base_currency.id:
                converted_amount = sale.total_amount
            else:
                # Get exchange rate effective on sale date
                rate = sale.currency.rates.filter(
                    effective_date__lte=sale.sale_date
                ).order_by('-effective_date').first()
                
                if rate:
                    # Convert to base currency
                    converted_amount = sale.total_amount / rate.rate
                else:
                    # Use current exchange rate if no historical rate found
                    current_rate = sale.currency.exchange_rate
                    if current_rate:
                        converted_amount = sale.total_amount / current_rate
                    else:
                        converted_amount = sale.total_amount  # Fallback
            
            total_sales += converted_amount
        
        return total_sales
    
    def _calculate_daily_expenses(self, target_date, base_currency):
        """Calculate total paid expenses for a specific day in base currency"""
        expenses = Expense.objects.filter(
            expense_date=target_date,
            tenant=self.request.user.tenant
        )
        
        total_expenses = Decimal('0.00')
        
        for expense in expenses:
            # Convert expense amount to base currency
            if expense.currency.id == base_currency.id:
                converted_amount = expense.amount
            else:
                # Get exchange rate effective on expense date
                rate = expense.currency.rates.filter(
                    effective_date__lte=expense.expense_date
                ).order_by('-effective_date').first()
                
                if rate:
                    converted_amount = expense.amount / rate.rate
                else:
                    # Use current exchange rate if no historical rate found
                    current_rate = expense.currency.exchange_rate
                    if current_rate:
                        converted_amount = expense.amount / current_rate
                    else:
                        converted_amount = expense.amount  # Fallback
            
            total_expenses += converted_amount
        
        return total_expenses
    
    def _calculate_daily_cost(self, target_date, base_currency):

        """Calculate total cost of goods sold for a specific day in base currency"""
        from catalog.models import ProductPrice
        
        # Get all sale items for the day
        sale_items = SaleItem.objects.filter(
            sale__sale_date__date=target_date,
            sale__tenant=self.request.user.tenant
        ).select_related('inventory__variant', 'sale')
        
        total_cost = Decimal('0.00')
        
        for item in sale_items:
            variant = item.inventory.variant
            sale_date = item.sale.sale_date
            
            # Get the product price effective on sale date
            product_price = ProductPrice.objects.filter(
                variant=variant,
                effective_date__lte=sale_date,
                tenant=self.request.user.tenant
            ).order_by('-effective_date').first()
            
            if product_price:
                cost_per_unit = product_price.cost_price
                cost_currency = product_price.cost_currency
                
                # Convert cost to base currency using rate effective on sale date
                if cost_currency.id == base_currency.id:
                    converted_cost_per_unit = cost_per_unit
                else:
                    # Get exchange rate effective on sale date
                    rate = cost_currency.rates.filter(
                        effective_date__lte=sale_date
                    ).order_by('-effective_date').first()
                    
                    if rate:
                        converted_cost_per_unit = cost_per_unit / rate.rate
                    else:
                        # Use current exchange rate if no historical rate found
                        current_rate = cost_currency.exchange_rate
                        if current_rate:
                            converted_cost_per_unit = cost_per_unit / current_rate
                        else:
                            converted_cost_per_unit = cost_per_unit  # Fallback
                
                # Calculate total cost for this item
                item_total_cost = converted_cost_per_unit * item.quantity
                total_cost += item_total_cost
        
        return total_cost
    



#---------------------------new code--------------
# views.py
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from core.pagination import StandardResultsSetPagination
from core.permissions import TenantPermissionMixin


class SaleItemFilter(django_filters.FilterSet):
    """Filter for SaleItem queryset"""
    
    # Date range filters
    date_from = django_filters.DateTimeFilter(field_name='sale__sale_date', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='sale__sale_date', lookup_expr='lte')
    
    # Customer filters
    customer = django_filters.NumberFilter(field_name='sale__customer__id')
    customer_name = django_filters.CharFilter(field_name='sale__customer__name', lookup_expr='icontains')
    
    # Product filters
    product = django_filters.NumberFilter(field_name='inventory__variant__product__id')
    category = django_filters.NumberFilter(field_name='inventory__variant__product__category__id')
    department = django_filters.NumberFilter(field_name='inventory__variant__product__category__department__id')
    
    # Location filter
    location = django_filters.NumberFilter(field_name='inventory__location__id')
    
    # Sale filters
    sale_number = django_filters.CharFilter(field_name='sale__sale_number', lookup_expr='icontains')
    payment_status = django_filters.ChoiceFilter(field_name='sale__payment_status', choices=Sales.PAYMENT_STATUS_CHOICES)
    sale_status = django_filters.ChoiceFilter(field_name='sale__status', choices=Sales.STATUS_CHOICES)
    
    # Barcode filter
    barcode = django_filters.CharFilter(field_name='inventory__variant__barcode', lookup_expr='icontains')
    
    # Item name filter
    item_name = django_filters.CharFilter(field_name='inventory__variant__variant_name', lookup_expr='icontains')

    class Meta:
        model = SaleItem
        fields = [
            'date_from', 'date_to', 'customer', 'customer_name',
            'product', 'category', 'department', 'location',
            'sale_number', 'payment_status', 'sale_status',
            'barcode', 'item_name'
        ]


class SaleItemDetailViewSet(TenantPermissionMixin,viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for SaleItem details with comprehensive information
    Provides detailed information about each sale item including:
    - Product details (barcode, name, category, department)
    - Financial data (cost, price, profit, discount)
    - Sale information (date, customer, session number)
    - Location and inventory data
    """
    
    serializer_class = SaleItemDetailSerializer
    permission_module='finance'
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SaleItemFilter
    
    search_fields = [
        'inventory__variant__variant_name',
        'inventory__variant__barcode', 
        'sale__sale_number',
        'sale__customer__name',
        'inventory__variant__product__name'
    ]
    
    ordering_fields = [
        'sale__sale_date', 'quantity', 'unit_price', 'line_total',
        'sale__sale_number', 'inventory__variant__variant_name'
    ]
    
    ordering = ['-sale__sale_date', '-created_at']  # Default ordering

    def get_queryset(self):
        """
        Get queryset with optimized select_related and prefetch_related
        to minimize database queries
        """
        return SaleItem.objects.select_related(
            'sale',
            'sale__customer', 
            'sale__currency',
            'sale__created_by_user',
            'inventory',
            'inventory__variant',
            'inventory__variant__product',
            'inventory__variant__product__category',
            'inventory__variant__product__category__department',
            'inventory__location'
        ).prefetch_related(
            'inventory__variant__variant_prices',
            'sale__currency__rates'
        ).filter(
            sale__tenant=self.request.user.tenant
        )

    def get_serializer_context(self):
        """Add request context to serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    
    
    

class YearlyReportViewSet(TenantPermissionMixin, viewsets.ViewSet):
    permission_module = "finance"
    
    @action(detail=False, methods=['get'], url_path="yearly-report")
    def yearly_report(self, request):
        """
        Generate yearly report with monthly breakdown
        Parameters: year
        """
        year = request.query_params.get('year')
        
        if not year:
            return Response(
                {'error': 'Year parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            year = int(year)
        except ValueError as e:
            return Response(
                {'error': f'Invalid year: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get base currency
        try:
            base_currency = Currency.get_base_currency()
        except Exception:
            return Response(
                {'error': 'Base currency not configured'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Month names mapping
        month_names = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
        }
        
        report_data = []
        
        for month in range(1, 13):
            # Get number of days in the month
            _, days_in_month = monthrange(year, month)
            
            monthly_sales = Decimal('0.00')
            monthly_expenses = Decimal('0.00')
            monthly_cost = Decimal('0.00')
            
            # Calculate monthly totals by summing daily values
            for day in range(1, days_in_month + 1):
                current_date = date(year, month, day)
                
                monthly_sales += self._calculate_daily_sales(current_date, base_currency)
                monthly_expenses += self._calculate_daily_expenses(current_date, base_currency)
                monthly_cost += self._calculate_daily_cost(current_date, base_currency)
            
            # Calculate profit and net profit
            profit = monthly_sales - monthly_cost
            net_profit = profit - monthly_expenses
            
            report_data.append({
                'month': month_names[month],
                'sales': round(monthly_sales, 2),
                'expense': round(monthly_expenses, 2),
                'cost': round(monthly_cost, 2),
                'profit': round(profit, 2),
                'netProfit': round(net_profit, 2)
            })
        
        serializer = YearlyReportSerializer(report_data, many=True)
        return Response(serializer.data)
    
    def _calculate_daily_sales(self, target_date, base_currency):
        """Calculate total sales for a specific day in base currency"""
        sales = Sales.objects.filter(
            sale_date__date=target_date,
            tenant=self.request.user.tenant
        )
        
        total_sales = Decimal('0.00')
        
        for sale in sales:
            # Convert sale total to base currency using rate effective on sale date
            if sale.currency.id == base_currency.id:
                converted_amount = sale.total_amount
            else:
                # Get exchange rate effective on sale date
                rate = sale.currency.rates.filter(
                    effective_date__lte=sale.sale_date
                ).order_by('-effective_date').first()
                
                if rate:
                    # Convert to base currency
                    converted_amount = sale.total_amount / rate.rate
                else:
                    # Use current exchange rate if no historical rate found
                    current_rate = sale.currency.exchange_rate
                    if current_rate:
                        converted_amount = sale.total_amount / current_rate
                    else:
                        converted_amount = sale.total_amount  # Fallback
            
            total_sales += converted_amount
        
        return total_sales
    
    def _calculate_daily_expenses(self, target_date, base_currency):
        """Calculate total paid expenses for a specific day in base currency"""
        expenses = Expense.objects.filter(
            expense_date=target_date,
            tenant=self.request.user.tenant
        )
        
        total_expenses = Decimal('0.00')
        
        for expense in expenses:
            # Convert expense amount to base currency
            if expense.currency.id == base_currency.id:
                converted_amount = expense.amount
            else:
                # Get exchange rate effective on expense date
                rate = expense.currency.rates.filter(
                    effective_date__lte=expense.expense_date
                ).order_by('-effective_date').first()
                
                if rate:
                    converted_amount = expense.amount / rate.rate
                else:
                    # Use current exchange rate if no historical rate found
                    current_rate = expense.currency.exchange_rate
                    if current_rate:
                        converted_amount = expense.amount / current_rate
                    else:
                        converted_amount = expense.amount  # Fallback
            
            total_expenses += converted_amount
        
        return total_expenses
    
    def _calculate_daily_cost(self, target_date, base_currency):
        """Calculate total cost of goods sold for a specific day in base currency"""
        from catalog.models import ProductPrice
        
        # Get all sale items for the day
        sale_items = SaleItem.objects.filter(
            sale__sale_date__date=target_date,
            sale__tenant=self.request.user.tenant
        ).select_related('inventory__variant', 'sale')
        
        total_cost = Decimal('0.00')
        
        for item in sale_items:
            variant = item.inventory.variant
            sale_date = item.sale.sale_date
            
            # Get the product price effective on sale date
            product_price = ProductPrice.objects.filter(
                variant=variant,
                effective_date__lte=sale_date,
                tenant=self.request.user.tenant
            ).order_by('-effective_date').first()
            
            if product_price:
                cost_per_unit = product_price.cost_price
                cost_currency = product_price.cost_currency
                
                # Convert cost to base currency using rate effective on sale date
                if cost_currency.id == base_currency.id:
                    converted_cost_per_unit = cost_per_unit
                else:
                    # Get exchange rate effective on sale date
                    rate = cost_currency.rates.filter(
                        effective_date__lte=sale_date
                    ).order_by('-effective_date').first()
                    
                    if rate:
                        converted_cost_per_unit = cost_per_unit / rate.rate
                    else:
                        # Use current exchange rate if no historical rate found
                        current_rate = cost_currency.exchange_rate
                        if current_rate:
                            converted_cost_per_unit = cost_per_unit / current_rate
                        else:
                            converted_cost_per_unit = cost_per_unit  # Fallback
                
                # Calculate total cost for this item
                item_total_cost = converted_cost_per_unit * item.quantity
                total_cost += item_total_cost
        
        return total_cost
        
        