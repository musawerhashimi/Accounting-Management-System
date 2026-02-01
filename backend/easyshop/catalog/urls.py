from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DepartmentViewSet, CategoryViewSet, ProductVariantViewSet, BarcodeViewSet
)

app_name = 'catalog'

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductVariantViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
    
    # Department endpoints
    path('departments/active/', DepartmentViewSet.as_view({'get': 'active'}), name='department-active'),
    
    # Category endpoints
    path('categories/by-department/', CategoryViewSet.as_view({'get': 'by_department'}), name='category-by-department'),

    # Barcode
    path('generate-barcode', BarcodeViewSet.as_view({'post': 'generate_barcode'}), name="generate-barcode"),
    path('check-barcode', BarcodeViewSet.as_view({'post': 'check_barcode'}), name="check-barcode"),
    path('barcode-info', BarcodeViewSet.as_view({'post': 'barcode_info'}), name="barcode-info")
]