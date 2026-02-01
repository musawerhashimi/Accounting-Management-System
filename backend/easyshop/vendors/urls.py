from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VendorViewSet, PurchaseViewSet, PurchaseItemViewSet

app_name = 'vendors'

router = DefaultRouter()
router.register(r'vendors', VendorViewSet, basename='vendor')
router.register(r'purchases', PurchaseViewSet, basename='purchase')
router.register(r'purchase-items', PurchaseItemViewSet, basename='purchaseitem')

urlpatterns = [
    path('', include(router.urls)),
]