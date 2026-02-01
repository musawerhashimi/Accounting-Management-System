# inventory/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LocationViewSet, InventoryViewSet, ProductVariantInventoryViewSet, StockMovementViewSet,
    ProductBatchViewSet, InventoryAdjustmentViewSet,
    InventoryCountViewSet, InventoryReportViewSet,
    InventoryCountItemViewSet
)

app_name = 'inventory'

# DRF Router
router = DefaultRouter()
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'variant-inventory', ProductVariantInventoryViewSet, basename='variant-inventory')
router.register(r'', InventoryViewSet, basename='inventory')
router.register(r'inventory-count-item', InventoryCountItemViewSet, basename='inventory-count-item')
router.register(r'stock-movements', StockMovementViewSet, basename='stockmovement')
router.register(r'product-batch', ProductBatchViewSet, basename='product-batch')
router.register(r'adjustments', InventoryAdjustmentViewSet, basename='adjustment')
router.register(r'counts', InventoryCountViewSet, basename='count')
router.register(r'reports', InventoryReportViewSet, basename='reports')

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    
    # Additional custom endpoints
    # path('dashboard/', LocationViewSet.as_view({'get': 'list'}), name='dashboard'),
    # path('low-stock/', InventoryViewSet.as_view({'get': 'low_stock'}), name='low-stock'),
    # path('out-of-stock/', InventoryViewSet.as_view({'get': 'out_of_stock'}), name='out-of-stock'),
    # path('stock-transfer/', InventoryViewSet.as_view({'post': 'transfer'}), name='stock-transfer'),
    # path('valuation/', InventoryViewSet.as_view({'get': 'valuation'}), name='stock-valuation'),
    
    # # Movement endpoints
    # path('movements/summary/', StockMovementViewSet.as_view({'get': 'summary'}), name='movement-summary'),
    
    # # Adjustment endpoints
    # path('adjustments/pending/', InventoryAdjustmentViewSet.as_view({'get': 'pending'}), name='pending-adjustments'),
    # path('adjustments/<int:pk>/approve/', InventoryAdjustmentViewSet.as_view({'post': 'approve'}), name='approve-adjustment'),
    
    # # Count endpoints
    # path('counts/<int:pk>/start/', InventoryCountViewSet.as_view({'post': 'start'}), name='start-count'),
    # path('counts/<int:pk>/complete/', InventoryCountViewSet.as_view({'post': 'complete'}), name='complete-count'),
    # path('counts/<int:pk>/items/', InventoryCountViewSet.as_view({'get': 'items'}), name='count-items'),
    # path('counts/<int:pk>/update-item/', InventoryCountViewSet.as_view({'patch': 'update_item'}), name='update-count-item'),
    
    # # Reports endpoints
    # path('reports/turnover/', InventoryReportsViewSet.as_view({'get': 'turnover_analysis'}), name='turnover-report'),
    # path('reports/ageing/', InventoryReportsViewSet.as_view({'get': 'stock_ageing'}), name='ageing-report'),
    # path('reports/trends/', InventoryReportsViewSet.as_view({'get': 'movement_trends'}), name='trends-report'),
]