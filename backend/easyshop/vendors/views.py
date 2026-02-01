from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Avg, F, OuterRef, Subquery, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from inventory.models import Location
from core.models import CurrencyRate
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Vendor, Purchase, PurchaseItem
from .serializers import (
    PurchaseDetailSerializer, VendorListSerializer, VendorDetailSerializer, PurchaseListSerializer,
    PurchaseCreateSerializer, PurchaseUpdateSerializer, PurchaseItemCreateSerializer,
    ReceiveItemsSerializer, VendorStatsSerializer, PurchaseStatsSerializer,
    PurchasePaymentSerializer, VendorUpdateSerializer
)
from core.permissions import TenantPermissionMixin
from core.pagination import StandardResultsSetPagination
from .filters import PurchaseFilter
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser


class PurchaseViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing purchases
    Provides CRUD operations, search, filtering, and receiving functionality
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_module = 'purchases'
    filter_backends = [DjangoFilterBackend, DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PurchaseFilter
    filterset_fields = ['status', 'vendor', 'location', 'created_by_user']
    search_fields = ['purchase_number', 'vendor__name', 'notes']
    ordering_fields = ['purchase_date', 'total_amount', 'status']
    ordering = ['-purchase_date']
    pagination_class = StandardResultsSetPagination
    
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return PurchaseUpdateSerializer
        elif self.action == "retrieve":
            return PurchaseDetailSerializer
        elif self.action == "create":
            return PurchaseCreateSerializer
        return PurchaseListSerializer
    
    def get_queryset(self):
        queryset = Purchase.objects.all()

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by vendor
        vendor_id = self.request.query_params.get('vendor_id')
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(purchase_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(purchase_date__lte=end_date)
        
        return queryset.select_related('vendor', 'location', 'currency', 'created_by_user'
                                       ).prefetch_related('items__variant__product')
    
   
    from django.core.handlers.wsgi import WSGIRequest
    def create(self, request: WSGIRequest, *args, **kwargs):
        import json
        if request.headers.get("Content-Type") != "application/json":
            items = json.loads(request.data.get("items", '[]'))

            for i, item in enumerate(items):
                if "product_data" in item:
                    variant = item["product_data"]["variants"][0]
                    image = request.FILES.get(f"variant_image_{i}")
                    if image:
                        variant["image"] = image

            payload = {
                "vendor": request.data["vendor"],
                "currency": request.data["currency"],
                "notes": request.data.get("notes", ""),
                "items": items,
                "payment": json.loads(request.data.get("payment"))
            }

            serializer = self.get_serializer(data=payload)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=201)
        else:
            # If the request is JSON, use the default create method
            return super().create(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get purchase statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total_purchases': queryset.count(),
            'pending_purchases': queryset.filter(status='pending').count(),
            'received_purchases': queryset.filter(status='received').count(),
        }
        
        # Calculate amounts
        amounts = queryset.aggregate(
            total=Sum('total_amount'),
            average=Avg('total_amount')
        )
        stats['total_amount'] = amounts['total'] or Decimal('0.00')
        stats['average_purchase_value'] = amounts['average'] or Decimal('0.00')
        
        # This month's purchases
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stats['this_month_amount'] = queryset.filter(
            purchase_date__gte=this_month_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        serializer = PurchaseStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def receive_items(self, request, pk=None):
        """Receive purchase items"""
        purchase = self.get_object()
        
        if purchase.status not in ['pending', 'partially_received']:
            return Response(
                {'error': 'Purchase must be pending or partially received to receive items'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ReceiveItemsSerializer(
            data=request.data,
            context={'purchase': purchase}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Return updated purchase
            purchase.refresh_from_db()
            purchase_serializer = self.get_serializer(purchase)
            return Response(purchase_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_received(self, request, pk=None):
        """Mark entire purchase as received"""
        purchase = self.get_object()
        location_id = request.data.get('location_id')

        if not location_id:
            return Response(
                {'error': 'location_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            location = Location.objects.get(id=location_id)
        except Location.DoesNotExist:
            return Response(
                {'error': 'invalid location_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if purchase.status == 'received':
            return Response(
                {'error': 'Purchase is already received'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        purchase.location = location
        purchase.save()
        # Receive all remaining quantities
        for item in purchase.items.all():
            remaining = item.remaining_quantity
            if remaining > 0:
                item.receive_quantity(remaining)
        
        purchase.refresh_from_db()
        serializer = self.get_serializer(purchase)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def make_payment(self, request, pk=None):
        """Make payment for purchase"""
        purchase = self.get_object()
        serializer = PurchasePaymentSerializer(
            data=request.data,
            context={'purchase': purchase, 'request': request}
        )
        
        if serializer.is_valid():
            payment = serializer.save()
            return Response({
                'message': 'Payment created successfully',
                'payment_id': payment.id,
                'payment_number': payment.payment_number
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a purchase"""
        purchase = self.get_object()
        
        if purchase.status in ['received', 'cancelled']:
            return Response(
                {'error': f'Cannot cancel a {purchase.status} purchase'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if purchase.received_quantity > 0:
            return Response(
                {'error': 'Cannot cancel a purchase with received items'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        purchase.status = 'cancelled'
        purchase.save()
        
        serializer = self.get_serializer(purchase)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a draft purchase"""
        purchase = self.get_object()
        
        if purchase.status != 'draft':
            return Response(
                {'error': 'Only draft purchases can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not purchase.items.exists():
            return Response(
                {'error': 'Cannot approve purchase without items'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        purchase.status = 'pending'
        purchase.save()
        
        serializer = self.get_serializer(purchase)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending purchases"""
        queryset = self.get_queryset().filter(status='pending')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PurchaseListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PurchaseListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue purchases (delivery date passed)"""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(
            status__in=['pending', 'partially_received'],
            delivery_date__lt=today
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PurchaseListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PurchaseListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_date_range(self, request):
        """Get purchases by date range"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            purchase_date__date__range=[start_date, end_date]
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PurchaseListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PurchaseListSerializer(queryset, many=True)
        return Response(serializer.data)


class PurchaseItemViewSet(TenantPermissionMixin, viewsets.ViewSet):
    """
    ViewSet for managing purchase items
    """
    permission_module = 'purchases'
    
    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        """Receive specific quantity of an item"""
        item = self.get_object()
        quantity = request.data.get('quantity')
        
        if not quantity:
            return Response(
                {'error': 'Quantity is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quantity = Decimal(str(quantity))
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid quantity format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            item.receive_quantity(quantity)
            serializer = self.get_serializer(item)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    

class VendorViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    
    """
    ViewSet for managing vendors
    Provides CRUD operations, search, filtering, and statistics
    """
    permission_module = 'purchases'
    
    # This line enables the ViewSet to accept JSON, form-data, and file uploads
    parser_classes = [MultiPartParser, FormParser, JSONParser] 
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'created_by_user']
    search_fields = ['name', 'contact_person', 'email', 'phone']
    ordering_fields = ['name', 'balance', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        return Vendor.objects.select_related('created_by_user').prefetch_related('addresses')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return VendorListSerializer
        elif self.action in ['update', 'partial_update']:
            return VendorUpdateSerializer
        return VendorDetailSerializer
    
    
    @action(detail=False, methods=['get'], url_path='vendors-stats')
    def vendors_stats(self, request):
        """Get vendor statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total_vendors': queryset.count(),
            'active_vendors': queryset.filter(status='active').count(),
            'inactive_vendors': queryset.filter(status='inactive').count(),
        }
        
        # Calculate purchase statistics
        purchases = Purchase.objects.filter(vendor__in=queryset)
        stats['total_purchases_amount'] = purchases.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        stats['pending_purchases'] = purchases.filter(status='pending').count()
        
        # This month's purchases
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stats['this_month_purchases'] = purchases.filter(
            purchase_date__gte=this_month_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        serializer = VendorStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Calculates vendor statistics, including total spending and a breakdown by product variant,
        all converted to the base currency.
        """
        vendor = self.get_object()

        # 1. Define a subquery to find the latest applicable currency rate for each purchase item.
        # This is the core optimization to avoid the N+1 query problem.
        latest_rate_subquery = CurrencyRate.objects.filter(
            currency_id=OuterRef('purchase__currency_id'),
            effective_date__lte=OuterRef('purchase__purchase_date')
        ).order_by('-effective_date').values('rate')[:1]

        # 2. Build the main query.
        # This single query fetches all necessary data and performs calculations in the database.
        variant_stats = PurchaseItem.objects.filter(
            purchase__vendor=vendor
        ).annotate(
            # Annotate each item with its applicable exchange rate.
            # Coalesce provides a default rate of 1.0 if no rate is found.
            rate=Coalesce(
                Subquery(latest_rate_subquery, output_field=DecimalField()),
                Decimal('1.0')
            ),
            # Calculate the cost in the base currency for each line item.
            base_currency_cost=F('line_total') / F('rate')
        ).values(
            # Group the results by variant name.
            'variant__variant_name'
        ).annotate(
            # Sum the quantities and base currency costs for each group.
            total_quantity=Sum('quantity'),
            total_amount=Sum('base_currency_cost')
        )

        # 3. Format the result list and calculate the grand total.
        # This is now a simple data transformation, as the heavy lifting is done.
        statistics_result = [
            {
                "name": item["variant__variant_name"],
                "total_quantity": item["total_quantity"],
                "total_amount": round(item["total_amount"], 2)
            }
            for item in variant_stats
        ]

        # The total amount is now a simple sum of the pre-calculated variant totals.
        total_vendor_amount = sum(item['total_amount'] for item in statistics_result)

        return Response({
            "statistics": statistics_result,
            "total_amount": round(total_vendor_amount, 2)
        })
    
    @action(detail=True, methods=['patch'], parser_classes=[MultiPartParser, FormParser])
    def photo(self, request, pk=None):
        vendor = self.get_object()
        
        if 'photo' not in request.data:
            return Response(
                {'error': 'No photo provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        vendor.photo = request.data['photo']
        vendor.save()
        photo_url = request.build_absolute_uri(vendor.photo.url)
        return Response(
            {'photo': photo_url}, 
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def purchases(self, request, pk=None):
        """Get vendor's purchases"""
        vendor = self.get_object()
        purchases = vendor.purchases.all()
        
        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter:
            purchases = purchases.filter(status=status_filter)
        
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from and date_to:
            purchases = purchases.filter(
                purchase_date__date__range=[date_from, date_to]
            )
        
        # Paginate
        page = self.paginate_queryset(purchases)
        if page is not None:
            serializer = PurchaseListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PurchaseListSerializer(purchases, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a vendor"""
        vendor = self.get_object()
        vendor.status = 'active'
        vendor.save()
        
        serializer = self.get_serializer(vendor)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a vendor"""
        vendor = self.get_object()
        vendor.status = 'inactive'
        vendor.save()
        
        serializer = self.get_serializer(vendor)
        return Response(serializer.data)
        
    @action(detail=False, methods=['get'])
    def overdue_purchases(self, request):
        """Get vendors with overdue purchases"""
        today = timezone.now().date()
        overdue_purchases = Purchase.objects.filter(
            status__in=['pending', 'partially_received'],
            delivery_date__lt=today
        ).values('vendor').annotate(
            total_overdue=Sum('total_amount')
        ).order_by('-total_overdue')
        
        # Get vendor details
        vendors = Vendor.objects.filter(id__in=[v['vendor'] for v in overdue_purchases])
        
        page = self.paginate_queryset(vendors)
        if page is not None:
            serializer = VendorListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = VendorListSerializer(vendors, many=True)
        return Response(serializer.data)