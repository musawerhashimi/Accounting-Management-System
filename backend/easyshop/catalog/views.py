from django.db.models import Sum, Q, Max
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser

from core.permissions import TenantPermissionMixin
from inventory.models import Inventory
from sales.models import SaleItem, ReturnItem
from vendors.models import PurchaseItem
from core.models import CurrencyRate, Currency

from .models import (
    Department, Category, ProductVariant
)
from .serializers import (
    DepartmentSerializer, CategorySerializer, ProductVariantSerializer, ProductVariantDetailSerializer, ProductVariantSearchSerializer
)


class DepartmentViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_module = 'purchases'
    ordering = ['name']
            
    def get_queryset(self):
        return Department.objects.select_related('created_by_user')

    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """Toggle department active status"""
        department = self.get_object()
        department.is_active = not department.is_active
        department.save()
        
        return Response({
            'id': department.id,
            'is_active': department.is_active,
            'message': f'Department {"activated" if department.is_active else "deactivated"}'
        })
        

class CategoryViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_module = 'purchases'
    
    def get_queryset(self):
        return Category.objects.select_related(
            'department', 'created_by_user'
        )
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """Toggle category active status"""
        category = self.get_object()
        category.is_active = not category.is_active
        category.save()
        
        return Response({
            'id': category.id,
            'is_active': category.is_active,
            'message': f'Category {"activated" if category.is_active else "deactivated"}'
        })


class ProductVariantViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    permission_module = 'product_details'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['sku', 'barcode', 'variant_name']
    ordering_fields = ['sku', 'variant_name', 'selling_price', 'created_at']
    ordering = ['-is_default', 'variant_name']
    
    def get_queryset(self):
        if self.action == "update":
            return ProductVariant.objects.select_related("product")
        product_id = self.request.query_params.get('product_id')
        queryset = ProductVariant.objects.select_related('product').prefetch_related(
            'variant_prices'
        ).annotate(
            current_stock=Sum('inventory_records__quantity_on_hand')
        )
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update', 'retrieve']:
            return ProductVariantDetailSerializer
        return ProductVariantSerializer
    
    @action(detail=False, methods=['GET'], permission_module='purchases')
    def search(self, request):
        """Search for the products"""
        keyword = request.query_params.get("q")
        if keyword == None:
            return Response({
                "details": "Keyword 'q' is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        queryset = ProductVariant.objects.select_related(
            "product__category__department",
            "product"
        
        ).filter(
            Q(product__name__icontains=keyword) |
            Q(variant_name__icontains=keyword) |
            Q(sku__icontains=keyword) |
            Q(barcode__icontains=keyword)
        ).distinct()[:20]
        serializer = ProductVariantSearchSerializer(queryset, many=True)
        # serializer.is_valid(raise_exception=True)
        return Response(
            data=serializer.data
        )
    
    @action(
        detail=True,
        methods=['post'],
        url_path='upload-image',
        parser_classes=[MultiPartParser, FormParser],
        description="Upload/replace the image for this variant"
    )
    def upload_image(self, request, pk=None):
        variant = self.get_object()
        image = request.FILES.get('image')

        if not image:
            return Response(
                {'detail': 'Image is not Provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Override and save
        variant.image = image
        variant.save()
        image_url = request.build_absolute_uri(variant.image.url)
        
        return Response({'image': image_url})

    @action(
        detail=True,
        methods=['get'],
        description="Get stock & movement stats for this variant at a given location"
    )
    def stats(self, request, pk=None):
        location_id = request.query_params.get('location_id')
        if not location_id:
            return Response(
                {'detail': 'location_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        variant = self.get_object()
        tenant = request.tenant
        # 1) Available on hand at this location
        available = Inventory.objects.filter(
            variant=variant,
            location_id=location_id
        ).aggregate(total=Sum('quantity_on_hand'))['total'] or 0

        # 2) Total purchased to this location
        purchased = PurchaseItem.objects.filter(
            variant=variant,
            purchase__tenant=tenant,
            purchase__location_id=location_id
        ).aggregate(total=Sum('quantity'))['total'] or 0

        # 3) Total sold from this location
        sold = SaleItem.objects.filter(
            inventory__variant=variant,
            inventory__location_id=location_id,
            sale__tenant=tenant,
        ).aggregate(total=Sum('quantity'))['total'] or 0

        # 4) Total returned at this location
        returned = ReturnItem.objects.filter(
            sale_item__inventory__variant=variant,
            return_order__tenant=tenant,
            sale_item__inventory__location_id=location_id
        ).aggregate(total=Sum('quantity_returned'))['total'] or 0

        # 5) List of individual purchases (purchase header + quantity)
        purchase_qs = PurchaseItem.objects.filter(
            variant=variant,
            purchase__tenant=tenant,
            purchase__location_id=location_id
        ).select_related('purchase', 'purchase__vendor').order_by('-purchase__purchase_date')

        purchases = [
            {
                'purchase_id': pi.purchase.id,
                'cost_price': pi.unit_cost,
                'cost_currency': pi.purchase.currency_id,
                'purchas_date': pi.purchase.purchase_date,
                'quantity': pi.quantity,
                'sale_price': pi.variant.current_price.selling_price,
                'sale_currency': pi.variant.current_price.selling_currency.id,
                'vendor': pi.purchase.vendor.name,
                'added_by': pi.purchase.created_by_user.get_full_name(),
            }
            for pi in purchase_qs[:100]
        ]

        return Response({
            'name': variant.variant_name,
            'available': available,
            'purchased': purchased,
            'sold': sold,
            'returned': returned,
            'purchases': purchases
        }, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['get'],
        url_path='top-customers',
        description="Get top 10 customers for this product with spend & last purchase"
    )
    def top_customers(self, request, pk=None):
        variant = self.get_object()
        tenant = request.user.tenant

        # First, get aggregated quantity & last date per customer
        cust_stats = (
            SaleItem.objects
            .filter(
                inventory__variant=variant,
                sale__tenant=tenant,
                sale__customer__isnull=False,
            )
            .values(
                'sale__customer_id',
                'sale__customer__name'
            )
            .annotate(
                total_quantity=Sum('quantity'),
                last_purchase_date=Max('sale__sale_date')
            )
            .filter(total_quantity__gt=0)
            .order_by('-total_quantity')[:10]
        )

        results = []
        for stat in cust_stats:
            cust_id   = stat['sale__customer_id']
            cust_name = stat['sale__customer__name']
            last_date = stat['last_purchase_date']

            # Sum up total_spent by looping sale items for this customer
            total_spent = 0
            items = SaleItem.objects.filter(
                inventory__variant=variant,
                sale__tenant=tenant,
                sale__customer_id=cust_id
            ).select_related('sale')

            for item in items:
                sale_date = item.sale.sale_date
                currency  = item.sale.currency

                # get the rate effective on or before the sale_date
                rate_obj = CurrencyRate.objects.filter(
                    currency=currency,
                    effective_date__lte=sale_date,
                    tenant=tenant
                ).order_by('-effective_date').first()

                if rate_obj and rate_obj.rate:
                    total_spent += (item.line_total / rate_obj.rate)
                else:
                    # fallback: treat rate=1 if none found
                    total_spent += item.line_total

            results.append({
                'name': variant.variant_name,
                'customer_id': cust_id,
                'customer_name': cust_name,
                'total_quantity': stat['total_quantity'],
                'total_spent': total_spent,
                'currency': Currency.get_base_currency().id,
                'last_purchase_date': last_date,
            })

        return Response(results, status=status.HTTP_200_OK)


from .utils import generate_barcode as generate, check_barcode as check

class BarcodeViewSet(TenantPermissionMixin, viewsets.ViewSet):
    """Authentication viewset"""
    permission_module = "purchases"
    # permission_action = "add"
    
    @action(detail=False, methods=['POST'])
    def check_barcode(self, request):
        barcode = request.data.get("barcode")
        return Response({
            "isUnique": check(barcode),
        }, status=200)

    @action(detail=False, methods=['POST'])
    def generate_barcode(self, request):
        existingBarcodes = request.data.get("existingBarcodes", [])
        return Response({
            "barcode": generate(existingBarcodes)
        })
    
    @action(detail=False, methods=['POST'], permission_module=None)
    def barcode_info(self, request):
        barcode = request.data.get("barcode")
        if not barcode:
            return Response({
                "message": "Barcode is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            variant = ProductVariant.objects.get(barcode=barcode)
        except ProductVariant.DoesNotExist:
            return Response({
                "message": "Barcode Not Found"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({
            'name': variant.variant_name,
            'price': variant.current_price.cost_price if variant.current_price else None,
            'currency_code': variant.current_price.cost_currency.code if variant.current_price else None,
        })
