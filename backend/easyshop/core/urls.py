from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'core'

router = DefaultRouter()
router.register(r'tenants', views.TenantViewSet, basename='tenant')
router.register(r'settings', views.TenantSettingsViewSet, basename='tenant-settings')
router.register(r'currencies', views.CurrencyViewSet, basename='currency')
router.register(r'units', views.UnitViewSet, basename='unit')
router.register(r'activity-logs', views.ActivityLogViewSet, basename='activity-log')

urlpatterns = [
    path('', include(router.urls)),
    path('initialize', views.InitializeView.as_view(), name="initialize")
]