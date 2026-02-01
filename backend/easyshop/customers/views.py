from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, Avg, F, ExpressionWrapper, OuterRef, Subquery, DecimalField
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from decimal import Decimal

from core.models import CurrencyRate
from core.permissions import TenantPermissionMixin
from core.pagination import StandardResultsSetPagination
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from .models import Customer, CustomerStatement
from .serializers import (
    CustomerListSerializer, CustomerDetailSerializer, CustomerCreateSerializer, CustomerSalesSerializer, CustomerStatementSerializer,
    CustomerUpdateSerializer,
    CustomerStatsSerializer
)
from .filters import CustomerFilter



class CustomerViewSet(TenantPermissionMixin, ModelViewSet):
    """
    ViewSet for managing customers with full CRUD operations
    Supports both JSON and FormData (multipart) content types
    """
    permission_module = 'customers'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CustomerFilter
    search_fields = ['name', 'customer_number', 'email', 'phone']
    ordering_fields = ['name', 'customer_number', 'created_at', 'balance']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination
    
    # Add parsers to handle different content types
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = Customer.objects.select_related(
            'preferred_currency', 'created_by_user'
        )

        # Add computed fields for list view
        if self.action == 'retrieve':
            # Subquery: Get exchange rate valid at or before the sale date
            exchange_rate_subquery = CurrencyRate.objects.filter(
                currency=OuterRef('sales__currency'),
                effective_date__lte=OuterRef('sales__sale_date')
            ).order_by('-effective_date').values('rate')[:1]
            
            queryset = queryset.annotate(
                total_purchases=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F('sales__total_amount') / Coalesce(
                                Subquery(exchange_rate_subquery, output_field=DecimalField()),
                                Value(1)
                            ),
                            output_field=DecimalField(max_digits=15, decimal_places=4)
                        ),
                        filter=Q(sales__status='completed')
                    ),
                    Value(0),
                    output_field=DecimalField(max_digits=15, decimal_places=4)
                ),
                purchase_count=Count('sales', filter=Q(sales__status='completed')),
            )
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return CustomerListSerializer
        elif self.action == 'create':
            return CustomerCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CustomerUpdateSerializer
        return CustomerDetailSerializer

    def create(self, request, *args, **kwargs):
        """
        Enhanced create method that handles both JSON and FormData
        """
        try:
            # Get the appropriate serializer
            serializer_class = self.get_serializer_class()
            
            # Handle different content types
            data = self._process_request_data(request)
            
            # Create serializer instance with processed data
            serializer = serializer_class(data=data, context={'request': request})
            
            if serializer.is_valid():
                # Perform the creation
                self.perform_create(serializer)
                
                # Return success response
                headers = self.get_success_headers(serializer.data)
                return Response(
                    {
                        'success': True,
                        'message': 'Customer created successfully',
                        'data': serializer.data
                    },
                    status=status.HTTP_201_CREATED,
                    headers=headers
                )
            else:
                # Return validation errors
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            # Handle unexpected errors
            return Response(
                {
                    'success': False,
                    'message': 'An error occurred while creating customer',
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """
        Enhanced update method that handles both JSON and FormData
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            # Get the appropriate serializer
            serializer_class = self.get_serializer_class()
            
            # Handle different content types
            data = self._process_request_data(request)
            
            # Create serializer instance with processed data
            serializer = serializer_class(
                instance, 
                data=data, 
                partial=partial, 
                context={'request': request}
            )
            
            if serializer.is_valid():
                # Perform the update
                self.perform_update(serializer)
                
                # Handle cache invalidation if needed
                if getattr(instance, '_prefetched_objects_cache', None):
                    instance._prefetched_objects_cache = {}
                
                return Response(
                    {
                        'success': True,
                        'message': 'Customer updated successfully',
                        'data': serializer.data
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'success': False,
                        'message': 'Validation failed',
                        'errors': serializer.errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'message': 'An error occurred while updating customer',
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_request_data(self, request):
        """
        Process request data based on content type
        Handles both JSON and FormData submissions
        """
        content_type = request.content_type
        
        if content_type and 'multipart/form-data' in content_type:
            # Handle FormData (multipart)
            data = request.data.copy()
            
            # Convert specific fields that might come as strings from FormData
            self._convert_formdata_types(data)
            
            return data
            
        elif content_type and 'application/json' in content_type:
            # Handle JSON data
            return request.data
            
        else:
            # Default handling - try to use request.data as-is
            return request.data

    def _convert_formdata_types(self, data):
        """
        Convert FormData string values to appropriate types
        """
        # Define fields that should be converted to specific types
        boolean_fields = ['is_active', 'is_company', 'tax_exempt']
        decimal_fields = ['credit_limit', 'balance']
        integer_fields = ['payment_terms_days']
        
        # Convert boolean fields
        for field in boolean_fields:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    data[field] = value.lower() in ['true', '1', 'yes', 'on']
        
        # Convert decimal fields
        for field in decimal_fields:
            if field in data and data[field]:
                try:
                    from decimal import Decimal
                    data[field] = Decimal(str(data[field]))
                except (ValueError, TypeError):
                    pass  # Let serializer handle validation
        
        # Convert integer fields
        for field in integer_fields:
            if field in data and data[field]:
                try:
                    data[field] = int(data[field])
                except (ValueError, TypeError):
                    pass  # Let serializer handle validation
        
        # Handle date fields if they come as strings
        date_fields = ['birth_date', 'created_at']
        for field in date_fields:
            if field in data and isinstance(data[field], str):
                # Let the serializer handle date parsing
                pass

    @action(detail=True, methods=['patch'], parser_classes=[MultiPartParser, FormParser])
    def photo(self, request, pk=None):
        customer = self.get_object()
        
        if 'photo' not in request.data:
            return Response(
                {'error': 'No photo provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        customer.photo = request.data['photo']
        customer.save()
        photo_url = request.build_absolute_uri(customer.photo.url)
        return Response(
            {'photo': photo_url}, 
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='sales-search')
    def seles_search(self, request):
        keyword = request.query_params.get('q', '')
        if not keyword:
            return Response({'error': 'Keyword is required'}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset().filter(
            Q(name__icontains=keyword)
        ).values('id', 'name', 'balance',).distinct()
        
        serialzier = CustomerSalesSerializer(queryset, many=True)
        return Response(serialzier.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get customer statistics"""
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        queryset = self.get_queryset()
        
        stats = {
            'total_customers': queryset.count(),
            'active_customers': queryset.filter(status='active').count(),
            'new_customers_this_month': queryset.filter(created_at__gte=month_start).count(),
            'customers_over_credit_limit': queryset.filter(
                balance__lt=0,
                credit_limit__gt=0
            ).extra(
                where=["ABS(balance) > credit_limit"]
            ).count(),
            'total_customer_balance': queryset.aggregate(
                total=Sum('balance')
            )['total'] or Decimal('0.00'),
            'average_customer_value': queryset.filter(
                sales__status='completed'
            ).aggregate(
                avg=Avg('sales__total_amount')
            )['avg'] or Decimal('0.00'),
            'top_customers': queryset.annotate(
                total_purchases=Sum('sales__total_amount', filter=Q(sales__status='completed'))
            ).filter(
                total_purchases__isnull=False
            ).order_by('-total_purchases')[:10]
        }
        
        serializer = CustomerStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def purchase_history(self, request, pk=None):
        """Get customer purchase history"""
        customer = self.get_object()
        from sales.models import Sale
        from sales.serializers import SaleListSerializer
        
        sales = Sale.objects.filter(customer=customer).order_by('-sale_date')
        
        # Apply pagination
        page = self.paginate_queryset(sales)
        if page is not None:
            serializer = SaleListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = SaleListSerializer(sales, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def transaction_history(self, request, pk=None):
        """Get customer transaction history"""
        customer = self.get_object()
        from finance.models import Transaction
        from finance.serializers import TransactionListSerializer
        
        transactions = Transaction.objects.filter(
            party_type='customer',
            party_id=customer.id
        ).order_by('-transaction_date')
        
        # Apply pagination
        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = TransactionListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = TransactionListSerializer(transactions, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def top_customers(self, request):
        """Get top customers by purchase amount"""
        limit = int(request.query_params.get('limit', 20))
        
        queryset = self.get_queryset().annotate(
            total_purchases=Sum('sales__total_amount', filter=Q(sales__status='completed')),
            purchase_count=Count('sales', filter=Q(sales__status='completed')),
        ).filter(
            total_purchases__isnull=False
        ).order_by('-total_purchases')[:limit]
        
        serializer = CustomerListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def statements(self, request, pk=None):
        customer = self.get_object()
        customer_statements = customer.statements
        search = request.query_params.get("search", None)
        if search:
            customer_statements = customer_statements.filter(
                Q(customer__name__icontains=search) |
                Q(customer__email__icontains=search) |
                Q(customer__phone__icontains=search)
            )
            
        serializer = CustomerStatementSerializer(customer_statements, many=True)
        return Response({
            "name": customer.name,
            "statements": serializer.data
        })


class CustomerStatementViewSet(TenantPermissionMixin, ModelViewSet):
    permission_module = 'customers'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['customer__name', 'customer__email', 'customer__phone']
    ordering_fields = ['customer__name', 'customer__email', 'created_at', 'amount']
    ordering = ['-statement_date']
    
    queryset = CustomerStatement.objects.all()
    serializer_class = CustomerStatementSerializer

    def get_allowed_methods(self):
        # Only allow list and create
        return ['GET', 'POST']

