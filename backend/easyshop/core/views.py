from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, CharFilter, DateFilter
from django.utils import timezone
from django.db.models import Count
from rest_framework.parsers import MultiPartParser


from catalog.models import Department
from catalog.serializers import DepartmentSerializer
from finance.models import CashDrawer
from finance.serializers import CashDrawerSerializer
from inventory.serializers import LocationSerializer
from inventory.models import Location
from vendors.models import Vendor
from vendors.serializers import VendorListSerializer


from .models import (
    Tenant, TenantSettings, Currency, Unit, ActivityLog
)
from .serializers import (
    EmailSettingsSerializer, ShopSettingsSerializer, TenantSerializer, TenantCreateSerializer, CurrencySerializer, UnitSerializer, ActivityLogSerializer
)
from .permissions import (
    HasTenantLogoPermission, IsTenantUser, HasModulePermission, IsTenantOwnerOrAdmin, 
    IsSystemAdmin, CanAccessTenantSettings, TenantPermissionMixin
)


# Filters
class TenantFilter(FilterSet):
    name = CharFilter(lookup_expr='icontains')
    business_type = CharFilter(exact=True)
    status = CharFilter(exact=True)
    contact_email = CharFilter(lookup_expr='icontains')
    created_after = DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Tenant
        fields = ['name', 'business_type', 'status', 'contact_email']


class ActivityLogFilter(FilterSet):
    action = CharFilter(exact=True)
    table_name = CharFilter(lookup_expr='icontains')
    user = CharFilter(field_name='user__username', lookup_expr='icontains')
    date_from = DateFilter(field_name='timestamp', lookup_expr='gte')
    date_to = DateFilter(field_name='timestamp', lookup_expr='lte')
    ip_address = CharFilter(exact=True)

    class Meta:
        model = ActivityLog
        fields = ['action', 'table_name', 'user', 'ip_address']


# ViewSets
class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TenantFilter
    search_fields = ['name', 'contact_email', 'domain']
    ordering_fields = ['name', 'created_at', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return TenantCreateSerializer
        return TenantSerializer

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend a tenant"""
        tenant = self.get_object()
        tenant.status = 'suspended'
        tenant.save()
        return Response({'status': 'Tenant suspended'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a tenant"""
        tenant = self.get_object()
        tenant.status = 'active'
        tenant.save()
        return Response({'status': 'Tenant activated'})

    @action(detail=True, methods=['get'])
    def usage_report(self, request, pk=None):
        """Get detailed usage report for a tenant"""
        tenant = self.get_object()
        report = {
            'users': {
                'total': tenant.users.count(),
                'active': tenant.users.filter(is_active=True).count(),
                'limit': tenant.max_users,
                'usage_percentage': (tenant.users.filter(is_active=True).count() / tenant.max_users) * 100
            },
            'products': {
                'total': tenant.products.filter(deleted_at__isnull=True).count(),
                'limit': tenant.max_products,
                'usage_percentage': (tenant.products.filter(deleted_at__isnull=True).count() / tenant.max_products) * 100
            },
            'locations': {
                'total': tenant.locations.filter(deleted_at__isnull=True).count(),
                'limit': tenant.max_locations,
                'usage_percentage': (tenant.locations.filter(deleted_at__isnull=True).count() / tenant.max_locations) * 100
            }
        }
        return Response(report)


class TenantSettingsViewSet(TenantPermissionMixin, viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsTenantUser, CanAccessTenantSettings]
    
    @action(detail=False, methods=['get', 'put'], url_path='shop')
    def shop_settings(self, request):
        """
        GET or PUT /api/settings/shop/
        """
        keys = ['shop_name', 'phone_number', 'contact_email', 'address']

        if request.method == 'GET':
            settings = TenantSettings.objects.filter(setting_key__in=keys)
            data = {key: "" for key in keys}
            for s in settings:
                data[s.setting_key] = s.get_typed_value()
            return Response(data)
        
        
        serializer = ShopSettingsSerializer(
            data=request.data,
            context={
                'tenant': request.tenant
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get', 'put'], url_path='email')
    def email_settings(self, request):
        """
        GET or PUT /api/settings/email/
        """
        keys = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'from_email']

        if request.method == 'GET':
            settings = TenantSettings.objects.filter(setting_key__in=keys, tenant=request.tenant)
            data = {key: "" for key in keys}
            for s in settings:
                data[s.setting_key] = s.get_typed_value()
            # Never return smtp_password if you want security
            data['smtp_password'] = None
            return Response(data)

        serializer = EmailSettingsSerializer(
            data=request.data,
            context={'tenant': request.tenant}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get', 'put'], url_path='logo', parser_classes=[MultiPartParser], permission_classes=[HasTenantLogoPermission])
    def logo_settings(self, request):
        """
        GET /api/settings/logo/     → Get current logo URL
        PUT /api/settings/logo/     → Upload or update logo image
        """
        tenant = request.tenant
        key = 'shop_logo'
        shop_key = "shop_name"
        if request.method == 'GET':
            try:
                setting = TenantSettings.objects.get(setting_key=key, setting_type='image')
                shop_name = TenantSettings.objects.get(setting_key=shop_key)
                logo_url = request.build_absolute_uri(setting.get_typed_value())
                return Response({'logo': logo_url, 'shop_name': shop_name.get_typed_value()}, status=200)
            except TenantSettings.DoesNotExist:
                return Response({'logo': None, 'shop_name': ''}, status=200)

        # PUT logic: handle file upload
        file = request.FILES.get('logo')
        if not file:
            return Response({'error': 'No file uploaded'}, status=400)

        setting, created = TenantSettings.objects.get_or_create(
            tenant=tenant,
            setting_key=key,
            defaults={
                'setting_type': 'image',
                'category': 'branding',
                'description': 'Shop logo',
            }
        )

        setting.setting_image = file
        setting.save()
        logo_url = request.build_absolute_uri(setting.get_typed_value())

        return Response({'logo': logo_url}, status=200)


class CurrencyViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = [IsAuthenticated, IsTenantUser, HasModulePermission]
    permission_module = 'currency'
    ordering = ['name']
    

class UnitViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_module = 'units'
    ordering = ['unit_type', 'name']


class ActivityLogViewSet(TenantPermissionMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated, IsTenantUser, IsTenantOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ActivityLogFilter
    ordering_fields = ['timestamp', 'action', 'user']
    ordering = ['-timestamp']

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get activity statistics for dashboard"""
        from datetime import timedelta
        
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        queryset = self.get_queryset()
        
        stats = {
            'today': queryset.filter(timestamp__date=today).count(),
            'this_week': queryset.filter(timestamp__date__gte=week_ago).count(),
            'this_month': queryset.filter(timestamp__date__gte=month_ago).count(),
            'by_action': list(queryset.values('action').annotate(count=Count('id')).order_by('-count')[:5]),
            'by_user': list(queryset.values('user__username', 'user__first_name', 'user__last_name')
                          .annotate(count=Count('id')).order_by('-count')[:5]),
            'recent_activities': ActivityLogSerializer(
                queryset[:10], many=True, context={'request': request}
            ).data
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export activity logs (simplified - returns data for now)"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        # In a real implementation, you'd generate CSV/Excel file
        return Response({
            'count': queryset.count(),
            'data': serializer.data[:1000]  # Limit for performance
        })
        
        
from rest_framework.views import APIView
class InitializeView(TenantPermissionMixin, APIView):
    def get(self, request):
        return Response(_get_initial_data(request))
    
    
def _get_initial_data(request):
    department_serializer = DepartmentSerializer(Department.objects.all(), many=True)
    unit_serializer = UnitSerializer(Unit.objects.all(), many=True)
    currency_serializer = CurrencySerializer(Currency.objects.all(), many=True)
    vendor_serializer = VendorListSerializer(Vendor.objects.all(), many=True, context={'request': request})
    location_serializer = LocationSerializer(Location.objects.all(), many=True)
    cashDrawer_serializer = CashDrawerSerializer(CashDrawer.objects.all(), many=True)

    return {
        "departments": department_serializer.data,
        "units": unit_serializer.data,
        "currencies": currency_serializer.data,
        "vendors": vendor_serializer.data,
        "locations": location_serializer.data,
        "cash_drawers": cashDrawer_serializer.data,
        "settings": _get_settings(request)
    }

def _get_settings(request):
    
    keys = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'from_email']
    settings = TenantSettings.objects.filter(setting_key__in=keys)
    email_settings = {key: "" for key in keys}
    for s in settings:
        email_settings[s.setting_key] = s.get_typed_value()
    # Never return smtp_password if you want security
    email_settings['smtp_password'] = None
    key = 'shop_logo'
    try:
        setting = TenantSettings.objects.get(setting_key=key, setting_type='image')
        logo_url = request.build_absolute_uri(setting.get_typed_value())
        logo_settings = {'logo': logo_url}
    except TenantSettings.DoesNotExist:
        logo_settings = {'logo': None}

    keys = ['shop_name', 'phone_number', 'contact_email', 'address']

    settings = TenantSettings.objects.filter(setting_key__in=keys)
    shop_settings = {key: "" for key in keys}
    for s in settings:
        shop_settings[s.setting_key] = s.get_typed_value()

    return {
        "shop_settings": shop_settings,
        "logo_settings": logo_settings,
        "email_settings": email_settings
    }