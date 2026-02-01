from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from decimal import Decimal

from core.models import Currency
from core.permissions import TenantPermissionMixin
from customers.models import CustomerStatement
from .models import Sales, SaleItem, Returns, ReturnItem
from .serializers import (
    SaleCreateUpdateSerializer, SaleListSerializer,
    ReturnCreateUpdateSerializer, ReturnListSerializer,
    ReturnItemSerializer
)
from .filters import SalesFilter, ReturnsFilter


class SalesViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    """ViewSet for managing sales"""
    
    permission_module = 'sales'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SalesFilter
    search_fields = ['sale_number', 'customer__name', 'notes']
    ordering_fields = ['sale_date', 'total_amount', 'created_at']
    ordering = ['-sale_date', '-created_at']
    
    def get_queryset(self):
        """Get filtered queryset"""
        queryset = Sales.objects.select_related(
            'customer', 'currency', 'created_by_user'
        ).prefetch_related('items__inventory__variant__product')
        
        # Add annotations for better performance
        queryset = queryset.annotate(
            items_count=Count('items'),
        )
        
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return SaleListSerializer
        return SaleCreateUpdateSerializer
   
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get sales dashboard statistics"""
        tenant = request.user.tenant
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Base queryset
        sales_qs = Sales.objects.filter(tenant=tenant, status='completed')
        
        # Today's stats
        today_sales = sales_qs.filter(sale_date__date=today).aggregate(
            total_amount=Sum('total_amount'),
            count=Count('id')
        )
        
        # This week's stats
        week_sales = sales_qs.filter(sale_date__date__gte=week_start).aggregate(
            total_amount=Sum('total_amount'),
            count=Count('id')
        )
        
        # This month's stats
        month_sales = sales_qs.filter(sale_date__date__gte=month_start).aggregate(
            total_amount=Sum('total_amount'),
            count=Count('id')
        )
        
        # Top selling products this month
        top_products = SaleItem.objects.filter(
            sale__tenant=tenant,
            sale__status='completed',
            sale__sale_date__date__gte=month_start
        ).values(
            'variant__product__name',
            'variant__variant_name'
        ).annotate(
            total_qty=Sum('quantity'),
            total_amount=Sum('line_total')
        ).order_by('-total_qty')[:10]
        
        # Recent sales
        recent_sales = sales_qs.order_by('-sale_date')[:10]
        recent_sales_data = SaleListSerializer(recent_sales, many=True).data
        
        return Response({
            'today': {
                'total_amount': today_sales['total_amount'] or Decimal('0.00'),
                'count': today_sales['count'] or 0
            },
            'this_week': {
                'total_amount': week_sales['total_amount'] or Decimal('0.00'),
                'count': week_sales['count'] or 0
            },
            'this_month': {
                'total_amount': month_sales['total_amount'] or Decimal('0.00'),
                'count': month_sales['count'] or 0
            },
            'top_products': list(top_products),
            'recent_sales': recent_sales_data
        })
    
    @action(detail=False, methods=['get'])
    def sales_report(self, request):
        """Generate sales report with filtering options"""
        # Get query parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        location_id = request.query_params.get('location_id')
        customer_id = request.query_params.get('customer_id')
        
        # Build queryset
        queryset = self.get_queryset().filter(status='completed')
        
        if start_date:
            queryset = queryset.filter(sale_date__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(sale_date__date__lte=end_date)
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # Calculate totals
        totals = queryset.aggregate(
            total_sales=Sum('total_amount'),
            total_discount=Sum('discount_amount'),
            total_tax=Sum('tax_amount'),
            count=Count('id')
        )
        
        # Group by date for trends
        daily_sales = queryset.extra(
            select={'date': 'DATE(sale_date)'}
        ).values('date').annotate(
            total_amount=Sum('total_amount'),
            count=Count('id')
        ).order_by('date')
        
        return Response({
            'totals': totals,
            'daily_trends': list(daily_sales),
            'sales_count': queryset.count()
        })

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # IMPORTANT: Prevent deletion if payments have been made
        if instance.paid_amount > 0:
            return Response(
                {'error': 'Cannot delete a sale with existing payments. Please reverse payments first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get a reference to the user before the sale is deleted
        user = instance.created_by_user

        # Reverse customer account balance adjustment
        self._reverse_customer_account_for_delete(instance, user)

        # Reverse inventory (return items to stock)
        self._reverse_inventory_for_delete(instance, user)
        
        # Delete related financial records (e.g., voiding transactions)
        # Depending on accounting rules, you might mark these as 'void' instead of deleting
        Transaction.objects.filter(reference_type='sale', reference_id=instance.pk).delete()
        
        # Finally, perform the delete
        self.perform_destroy(instance)
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _reverse_inventory_for_delete(self, sale, user):
        """Return all sold items back to inventory."""
        from inventory.models import StockMovement
        for item in sale.items.all():
            StockMovement.objects.create(
                tenant=sale.tenant,
                variant=item.inventory.variant,
                batch=item.inventory.batch,
                location=item.inventory.location,
                movement_type='sale_cancellation',
                quantity=item.quantity,  # Positive value returns to stock
                reference_type='sale',
                reference_id=sale.id,
                notes=f"Cancellation of Sale: {sale.sale_number}",
                created_by_user=user
            )

    def _reverse_customer_account_for_delete(self, sale, user):
        """Reverse the loan created by the sale from the customer's account."""
        if not sale.customer:
            return

        loan_statement = CustomerStatement.objects.filter(sale=sale, statement_type="loan").first()
        if loan_statement:
            loan_amount_base = Currency.convert_to_base_currency(
                loan_statement.amount, loan_statement.currency_id
            )
            sale.customer.balance += loan_amount_base
            sale.customer.save()
            loan_statement.delete()


class ReturnsViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    """ViewSet for managing returns"""
    
    permission_module = 'sales'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ReturnsFilter
    search_fields = ['return_number', 'original_sale__sale_number', 'customer__name']
    ordering_fields = ['return_date', 'total_refund_amount', 'created_at']
    ordering = ['-return_date', '-created_at']
    
    def get_queryset(self):
        """Get filtered queryset"""
        return Returns.objects.select_related(
            'customer', 'original_sale', 'currency', 'processed_by_user'
        ).prefetch_related('items__variant__product')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return ReturnListSerializer
        return ReturnCreateUpdateSerializer
    
    def perform_create(self, serializer):
        """Create return with proper tenant context"""
        serializer.save(tenant=self.request.user.tenant)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a return"""
        return_order = self.get_object()
        
        if return_order.status != 'pending':
            return Response(
                {'error': 'Only pending returns can be approved.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return_order.status = 'approved'
        return_order.processed_by_user = request.user
        return_order.save()
        
        return Response({'message': 'Return approved successfully.'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a return"""
        return_order = self.get_object()
        
        if return_order.status != 'pending':
            return Response(
                {'error': 'Only pending returns can be rejected.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return_order.status = 'rejected'
        return_order.processed_by_user = request.user
        return_order.save()
        
        return Response({'message': 'Return rejected successfully.'})
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process an approved return (restock items and create refund)"""
        return_order = self.get_object()
        
        if return_order.status != 'approved':
            return Response(
                {'error': 'Only approved returns can be processed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Restock items marked for restocking
        self._restock_return_items(return_order)
        
        # Create refund payment record
        self._create_refund_payment(return_order)
        
        return_order.status = 'processed'
        return_order.processed_by_user = request.user
        return_order.save()
        
        return Response({'message': 'Return processed successfully.'})
    
    def _restock_return_items(self, return_order):
        """Restock returned items to inventory"""
        from inventory.models import Inventory, StockMovement
        
        for item in return_order.items.filter(condition__in=['excellent', 'good']):
            if not item.restocked:
                # Add back to inventory
                inventory, created = Inventory.objects.get_or_create(
                    tenant=return_order.tenant,
                    variant=item.variant,
                    batch=item.batch,
                    location=return_order.original_sale.location,
                    defaults={'quantity_on_hand': 0, 'reserved_quantity': 0}
                )
                
                inventory.quantity_on_hand += item.quantity_returned
                inventory.save()
                
                # Create stock movement
                StockMovement.objects.create(
                    tenant=return_order.tenant,
                    variant=item.variant,
                    batch=item.batch,
                    location=return_order.original_sale.location,
                    movement_type='return',
                    quantity=item.quantity_returned,
                    reference_type='return',
                    reference_id=return_order.id,
                    notes=f"Return restocked: {return_order.return_number}",
                    created_by_user=return_order.processed_by_user
                )
                
                # Mark as restocked
                item.restocked = True
                item.save()
    
    def _create_refund_payment(self, return_order):
        """Create refund payment record"""
        from finance.models import Payment
        
        Payment.objects.create(
            tenant=return_order.tenant,
            amount=-return_order.total_refund_amount,  # Negative for refund
            currency=return_order.currency,
            payment_method='refund',
            payment_date=timezone.now(),
            reference_type='return',
            reference_id=return_order.id,
            notes=f"Refund for return: {return_order.return_number}",
            processed_by_user=return_order.processed_by_user
        )


class ReturnItemViewSet(TenantPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing return items"""
    
    permission_module = 'sales'
    serializer_class = ReturnItemSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['variant__variant_name', 'variant__product__name']
    
    def get_queryset(self):
        """Get return items for a specific return"""
        return_id = self.kwargs.get('return_pk')
        return ReturnItem.objects.filter(
            return_order_id=return_id,
            return_order__tenant=self.request.user.tenant
        ).select_related('variant__product', 'batch', 'sale_item')