from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F, Case, When, DecimalField, Value
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from core.permissions import TenantPermissionMixin, HasModulePermission
from core.pagination import StandardResultsSetPagination
from .filters import InventoryFilter

from .models import (
    Location, ProductBatch, Inventory, StockMovement,
    InventoryCountItem
)
from .serializers import (
    LocationSerializer, ProductBatchSerializer, InventorySerializer,
    StockMovementSerializer, InventoryAdjustmentSerializer,
    InventoryCountSerializer, InventoryCountItemSerializer,
    BulkStockMovementSerializer, InventoryTransferSerializer,
    InventoryReportSerializer,
    ExpiryReportSerializer
)


class LocationViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    serializer_class = LocationSerializer
    permission_module = 'stock_and_warehouse'
    ordering = ['name']
    queryset = Location.objects.all()
    @action(detail=True, methods=['get'])
    def inventory_summary(self, request, pk=None):
        """Get inventory summary for a location"""
        location = self.get_object()
        
        # Get inventory statistics
        inventory_stats = location.inventory_records.aggregate(
            total_products=Sum(Case(
                When(quantity_on_hand__gt=0, then=Value(1)),
                default=Value(0),
                output_field=DecimalField()
            )),
            total_quantity=Sum('quantity_on_hand'),
            total_reserved=Sum('reserved_quantity'),
            low_stock_items=Sum(Case(
                When(quantity_on_hand__lte=F('reorder_level'), then=Value(1)),
                default=Value(0),
                output_field=DecimalField()
            ))
        )
        
        # Get recent movements
        recent_movements = StockMovement.objects.filter(
            tenant=request.user.tenant,
            location=location
        ).select_related(
            'variant__product', 'batch', 'created_by_user'
        ).order_by('-created_at')[:10]
        
        return Response({
            'location': LocationSerializer(location).data,
            'stats': inventory_stats,
            'recent_movements': StockMovementSerializer(recent_movements, many=True).data
        })

    @action(detail=True, methods=['get'])
    def low_stock_items(self, request, pk=None):
        """Get low stock items for a location"""
        location = self.get_object()
        
        low_stock = Inventory.objects.filter(
            tenant=request.user.tenant,
            location=location,
            quantity_on_hand__lte=F('reorder_level')
        ).select_related(
            'variant__product', 'batch', 'location'
        ).order_by('quantity_on_hand')
        
        serializer = InventorySerializer(low_stock, many=True)
        return Response(serializer.data)


class ProductBatchViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    serializer_class = ProductBatchSerializer
    permission_module = 'inventory'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['variant', 'is_active']
    search_fields = ['batch_number', 'supplier_batch_ref', 'variant__variant_name']
    ordering_fields = ['batch_number', 'manufacture_date', 'expiry_date', 'created_at']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by expiry status
        expiry_filter = self.request.query_params.get('expiry_status')
        if expiry_filter == 'expired':
            queryset = queryset.filter(expiry_date__lt=timezone.now().date())
        elif expiry_filter == 'expiring_soon':
            days = int(self.request.query_params.get('days', 30))
            cutoff_date = timezone.now().date() + timedelta(days=days)
            queryset = queryset.filter(
                expiry_date__lte=cutoff_date,
                expiry_date__gte=timezone.now().date()
            )
        
        return queryset.select_related('variant__product')

    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get batches expiring within specified days"""
        days = int(request.query_params.get('days', 30))
        cutoff_date = timezone.now().date() + timedelta(days=days)
        
        expiring_batches = self.get_queryset().filter(
            expiry_date__lte=cutoff_date,
            expiry_date__gte=timezone.now().date(),
            is_active=True
        ).order_by('expiry_date')
        
        page = self.paginate_queryset(expiring_batches)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(expiring_batches, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def expired(self, request):
        """Get expired batches"""
        expired_batches = self.get_queryset().filter(
            expiry_date__lt=timezone.now().date(),
            is_active=True
        ).order_by('expiry_date')
        
        page = self.paginate_queryset(expired_batches)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(expired_batches, many=True)
        return Response(serializer.data)


class InventoryViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    serializer_class = InventorySerializer
    permission_module = 'inventory'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InventoryFilter
    search_fields = ['variant__variant_name', 'variant__product__name', 'location__name', 'variant__barcode']
    ordering_fields = ['quantity_on_hand', 'reserved_quantity', 'reorder_level', 'last_counted_date']
    ordering = ['-updated_at']
    pagination_class = StandardResultsSetPagination
    def get_queryset(self):
        queryset = Inventory.objects.all()
        # queryset = super().get_queryset()
        
        # Filter by stock status
        stock_filter = self.request.query_params.get('stock_status')
        if stock_filter == 'low_stock':
            queryset = queryset.filter(quantity_on_hand__lte=F('reorder_level'))
        elif stock_filter == 'out_of_stock':
            queryset = queryset.filter(quantity_on_hand=0)
        elif stock_filter == 'in_stock':
            queryset = queryset.filter(quantity_on_hand__gt=0)
        
        return queryset.select_related(
            'variant__product__base_unit', 'batch', 'location'
        )

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get low stock items across all locations"""
        low_stock = self.get_queryset().filter(
            quantity_on_hand__lte=F('reorder_level')
        ).order_by('quantity_on_hand')
        
        page = self.paginate_queryset(low_stock)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(low_stock, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def out_of_stock(self, request):
        """Get out of stock items"""
        out_of_stock = self.get_queryset().filter(quantity_on_hand=0)
        
        page = self.paginate_queryset(out_of_stock)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(out_of_stock, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def transfer(self, request):
        """Transfer inventory between locations"""
        serializer = InventoryTransferSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            result = serializer.save()
            return Response({
                'message': 'Inventory transferred successfully',
                'transfer_details': {
                    'quantity': result['quantity_transferred'],
                    'from_location': result['outbound_movement'].location.name,
                    'to_location': result['inbound_movement'].location.name,
                    'variant': result['outbound_movement'].variant.variant_name
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reserve(self, request, pk=None):
        """Reserve inventory quantity"""
        inventory = self.get_object()
        quantity = Decimal(str(request.data.get('quantity', 0)))
        
        if quantity <= 0:
            return Response(
                {'error': 'Quantity must be greater than 0'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if inventory.reserve_quantity(quantity):
            return Response({
                'message': f'Reserved {quantity} units successfully',
                'available_quantity': inventory.available_quantity,
                'reserved_quantity': inventory.reserved_quantity
            })
        else:
            return Response(
                {'error': 'Insufficient available quantity'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def release_reservation(self, request, pk=None):
        """Release reserved inventory quantity"""
        inventory = self.get_object()
        quantity = Decimal(str(request.data.get('quantity', 0)))
        
        if quantity <= 0:
            return Response(
                {'error': 'Quantity must be greater than 0'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if inventory.release_reservation(quantity):
            return Response({
                'message': f'Released {quantity} units successfully',
                'available_quantity': inventory.available_quantity,
                'reserved_quantity': inventory.reserved_quantity
            })
        else:
            return Response(
                {'error': 'Insufficient reserved quantity'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], url_path='barcode-search')
    def barcode_search(self, request):
        """Search inventory by barcode"""
        barcode = request.query_params.get('barcode', '').strip()
        if not barcode:
            return Response({'error': 'Barcode parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        inventory = self.get_queryset().filter(variant__barcode=barcode).select_related(
            'variant__product', 'batch', 'location'
        )
        
        if not inventory.exists():
            return Response({'message': 'No item found with this barcode'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(inventory.first())
        return Response(serializer.data)


class StockMovementViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    permission_module = 'inventory'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['variant', 'batch', 'location', 'movement_type', 'reference_type']
    search_fields = ['variant__variant_name', 'variant__product__name', 'notes']
    ordering_fields = ['created_at', 'quantity']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset.select_related(
            'variant__product', 'batch', 'location', 'created_by_user'
        )

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple stock movements"""
        serializer = BulkStockMovementSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            result = serializer.save()
            return Response({
                'message': f'Created {len(result["movements"])} stock movements',
                'movements': StockMovementSerializer(result['movements'], many=True).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get stock movement summary"""
        # Get date range
        start_date = request.query_params.get('start_date', timezone.now().date() - timedelta(days=30))
        end_date = request.query_params.get('end_date', timezone.now().date())
        
        movements = self.get_queryset().filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        # Summary by movement type
        summary = {}
        for movement_type, display_name in StockMovement.MOVEMENT_TYPES:
            type_movements = movements.filter(movement_type=movement_type)
            summary[movement_type] = {
                'display_name': display_name,
                'count': type_movements.count(),
                'total_quantity': type_movements.aggregate(
                    total=Sum('quantity')
                )['total'] or 0
            }
        
        return Response({
            'date_range': {'start_date': start_date, 'end_date': end_date},
            'summary': summary,
            'total_movements': movements.count()
        })


class InventoryAdjustmentViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    serializer_class = InventoryAdjustmentSerializer
    permission_module = 'inventory'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['variant', 'batch', 'location', 'reason', 'approved_by_user']
    search_fields = ['adjustment_number', 'variant__variant_name', 'notes']
    ordering_fields = ['adjustment_date', 'adjustment_quantity', 'cost_impact']
    ordering = ['-adjustment_date']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by approval status
        approval_filter = self.request.query_params.get('approval_status')
        if approval_filter == 'approved':
            queryset = queryset.filter(approved_by_user__isnull=False)
        elif approval_filter == 'pending':
            queryset = queryset.filter(approved_by_user__isnull=True)
        
        return queryset.select_related(
            'variant__product', 'batch', 'location', 'currency',
            'approved_by_user', 'created_by_user'
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an inventory adjustment"""
        adjustment = self.get_object()
        
        if adjustment.approved_by_user:
            return Response(
                {'error': 'Adjustment already approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            adjustment.approved_by_user = request.user
            adjustment.save(update_fields=['approved_by_user', 'updated_at'])
            
            # Create stock movement
            adjustment.create_stock_movement()
        
        return Response({
            'message': 'Adjustment approved successfully',
            'adjustment': InventoryAdjustmentSerializer(adjustment).data
        })

    @action(detail=False, methods=['get'])
    def pending_approval(self, request):
        """Get adjustments pending approval"""
        pending = self.get_queryset().filter(approved_by_user__isnull=True)
        
        page = self.paginate_queryset(pending)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)


class InventoryCountViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    serializer_class = InventoryCountSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    permission_module = 'inventory'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['location', 'status', 'created_by_user']
    search_fields = ['count_number']
    ordering_fields = ['count_date', 'status']
    ordering = ['-count_date']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return super().get_queryset().select_related(
            'location', 'created_by_user', 'completed_by_user'
        ).prefetch_related('count_items__variant__product')

    @action(detail=True, methods=['post'])
    def start_count(self, request, pk=None):
        """Start an inventory count"""
        count = self.get_object()
        
        if count.status != 'planned':
            return Response(
                {'error': 'Count must be in planned status to start'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create count items for all inventory at the location
        inventory_records = Inventory.objects.filter(
            tenant=request.user.tenant,
            location=count.location,
            quantity_on_hand__gt=0
        ).select_related('variant', 'batch')
        
        count_items = []
        for inventory in inventory_records:
            count_items.append(InventoryCountItem(
                count=count,
                variant=inventory.variant,
                batch=inventory.batch,
                system_quantity=inventory.quantity_on_hand,
                counted_quantity=0  # To be filled during count
            ))
        
        InventoryCountItem.objects.bulk_create(count_items)
        
        count.status = 'in_progress'
        count.save(update_fields=['status', 'updated_at'])
        
        return Response({
            'message': 'Inventory count started',
            'items_to_count': len(count_items)
        })

    @action(detail=True, methods=['post'])
    def complete_count(self, request, pk=None):
        """Complete an inventory count"""
        count = self.get_object()
        
        if count.status != 'in_progress':
            return Response(
                {'error': 'Count must be in progress to complete'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            count.complete_count(request.user)
            return Response({
                'message': 'Inventory count completed',
                'variances_found': count.variances_found
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def count_items(self, request, pk=None):
        """Get count items for a count"""
        count = self.get_object()
        items = count.count_items.select_related(
            'variant__product', 'batch', 'counted_by_user'
        ).order_by('variant__variant_name')
        
        page = self.paginate_queryset(items)
        if page is not None:
            serializer = InventoryCountItemSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = InventoryCountItemSerializer(items, many=True)
        return Response(serializer.data)


class InventoryCountItemViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    serializer_class = InventoryCountItemSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    permission_module = 'inventory'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['count', 'variant', 'counted_by_user']
    search_fields = ['variant__variant_name', 'variant__product__name']
    
    def get_queryset(self):
        return super().get_queryset().select_related(
            'count', 'variant__product', 'batch', 'counted_by_user'
        )

    def perform_update(self, serializer):
        # Set the user who counted the item
        serializer.save(counted_by_user=self.request.user)


class InventoryReportViewSet(TenantPermissionMixin, viewsets.ViewSet):
    """Inventory reports and analytics"""
    permission_module = 'inventory'

    @action(detail=False, methods=['get'])
    def stock_levels(self, request):
        """Stock level report"""
        filter_serializer = InventoryReportSerializer(
            data=request.query_params,
            context={'request': request}
        )
        
        if filter_serializer.is_valid():
            filters = filter_serializer.validated_data
            queryset = Inventory.objects.filter(
                tenant=request.user.tenant
            ).select_related(
                'variant__product', 'batch', 'location'
            )
            
            # Apply filters
            if 'location' in filters:
                queryset = queryset.filter(location=filters['location'])
            if 'variant' in filters:
                queryset = queryset.filter(variant=filters['variant'])
            if 'batch' in filters:
                queryset = queryset.filter(batch=filters['batch'])
            
            # Aggregate stock levels
            stock_levels = queryset.values(
                'location__name', 'variant__variant_name', 'batch__batch_number'
            ).annotate(
                total_quantity=Sum('quantity_on_hand'),
                reserved_quantity=Sum('reserved_quantity'),
                available_quantity=F('quantity_on_hand') - F('reserved_quantity')
            ).order_by('location__name', 'variant__variant_name')
            
            return Response(stock_levels)
        
        return Response(filter_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def expiry_report(self, request):
        """Expiry report"""
        filter_serializer = ExpiryReportSerializer(
            data=request.query_params,
            context={'request': request}
        )
        
        if filter_serializer.is_valid():
            filters = filter_serializer.validated_data
            queryset = ProductBatch.objects.filter(
                tenant=request.user.tenant,
                is_active=True
            ).select_related('variant__product')
            
            # Apply filters
            if 'expiry_status' in filters:
                if filters['expiry_status'] == 'expired':
                    queryset = queryset.filter(expiry_date__lt=timezone.now().date())
                elif filters['expiry_status'] == 'expiring_soon':
                    days = filters.get('days', 30)
                    cutoff_date = timezone.now().date() + timedelta(days=days)
                    queryset = queryset.filter(
                        expiry_date__lte=cutoff_date,
                        expiry_date__gte=timezone.now().date()
                    )
            
            # Aggregate expiry data
            expiry_data = queryset.values(
                'variant__variant_name', 'batch_number', 'expiry_date'
            ).annotate(
                total_quantity=Sum('inventory__quantity_on_hand')
            ).order_by('expiry_date')
            
            return Response(expiry_data)
        
        return Response(filter_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    



#---------------------------------------

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Prefetch
from catalog.models import ProductVariant
from .serializers import ProductVariantInventorySerializer
from .models import Inventory, Location


class ProductVariantInventoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Product Variant Inventory information
    
    Provides inventory and sales data for product variants.
    Can be filtered by location_id to show data for specific locations.
    """
    serializer_class = ProductVariantInventorySerializer
    pagination_class= StandardResultsSetPagination
    def get_queryset(self):
        queryset = ProductVariant.objects.filter(
            is_active=True,
            product__is_active=True
        ).select_related(
            'product',
            'product__category',
            'product__category__department'
        ).prefetch_related(
            Prefetch(
                'inventory_records',
                queryset=Inventory.objects.select_related('location')
            )
        )
        
        # Filter by location if provided
        location_id = self.request.query_params.get('location_id')
        if location_id:
            # Only include variants that have inventory in the specified location
            queryset = queryset.filter(
                inventory_records__location_id=location_id,
                inventory_records__location__is_active=True
            ).distinct()
        
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['location_id'] = self.request.query_params.get('location_id')
        return context
    
    def list(self, request, *args, **kwargs):
        """
        List all product variants with inventory information
        
        Query Parameters:
        - location_id: Filter by specific location (optional)
        - department: Filter by department name (optional)
        - category: Filter by category name (optional)
        """
        queryset = self.get_queryset()
        
        # Additional filtering options
        department = request.query_params.get('department')
        if department:
            queryset = queryset.filter(
                product__category__department__name__icontains=department
            )
        
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(
                product__category__name__icontains=category
            )
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_location(self, request):
        """
        Get inventory summary grouped by location
        
        Returns inventory data for all locations or filtered by location_id
        """
        location_id = request.query_params.get('location_id')
        
        if location_id:
            try:
                location = Location.objects.get(id=location_id, is_active=True)
                locations = [location]
            except Location.DoesNotExist:
                return Response(
                    {'error': 'Location not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            locations = Location.objects.filter(is_active=True)
        
        result = []
        for location in locations:
            # Get variants for this location
            variants_data = []
            variants = ProductVariant.objects.filter(
                inventory_records__location=location,
                is_active=True
            ).distinct()
            
            for variant in variants:
                serializer = self.get_serializer(
                    variant, 
                    context={'location_id': location.id}
                )
                variants_data.append(serializer.data)
            
            result.append({
                'location_id': location.id,
                'location_name': location.name,
                'location_type': location.location_type,
                'variants': variants_data
            })
        
        return Response(result)
    
    @action(detail=True, methods=['get'])
    def inventory_detail(self, request, pk=None):
        """
        Get detailed inventory information for a specific variant
        """
        variant = self.get_object()
        location_id = request.query_params.get('location_id')
        
        # Get inventory records
        inventory_qs = variant.inventory_records.select_related(
            'location', 'batch'
        )
        
        if location_id:
            inventory_qs = inventory_qs.filter(location_id=location_id)
        
        inventory_data = []
        for inv in inventory_qs:
            inventory_data.append({
                'location_id': inv.location.id,
                'location_name': inv.location.name,
                'batch_number': inv.batch.batch_number if inv.batch else None,
                'quantity_on_hand': inv.quantity_on_hand,
                'reserved_quantity': inv.reserved_quantity,
                'available_quantity': inv.available_quantity,
                'reorder_level': inv.reorder_level,
                'needs_reorder': inv.needs_reorder,
                'last_counted_date': inv.last_counted_date
            })
        
        serializer = self.get_serializer(variant)
        result = serializer.data
        result['inventory_details'] = inventory_data
        
        return Response(result)