from django.urls import path, include
from rest_framework_nested import routers
from .views import SalesViewSet, ReturnsViewSet, ReturnItemViewSet

# Main router
router = routers.DefaultRouter()
router.register(r'sales', SalesViewSet, basename='sales')
router.register(r'returns', ReturnsViewSet, basename='returns')

# Nested routers for sale items
sales_router = routers.NestedSimpleRouter(router, r'sales', lookup='sale')

# Nested routers for return items
returns_router = routers.NestedSimpleRouter(router, r'returns', lookup='return')
returns_router.register(r'items', ReturnItemViewSet, basename='return-items')

app_name = 'sales'

urlpatterns = [
    path('', include(router.urls)),
    path('', include(sales_router.urls)),
    path('', include(returns_router.urls)),
]