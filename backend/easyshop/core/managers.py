from .threads import get_current_tenant
# Custom manager that uses thread-local tenant
from django.db import models
from django.contrib.auth.models import UserManager


class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted objects by default"""
    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(self.model, 'deleted_at'):
            return queryset.filter(deleted_at__isnull=True)
        return queryset


class TenantManager(SoftDeleteManager):
    """Manager for tenant-aware models"""
    def __init__(self, tenant_field='tenant'):
        super().__init__()
        self.tenant_field = tenant_field
    
    def get_queryset(self):
        tenant = get_current_tenant()
        queryset = super().get_queryset().all()

        if tenant and hasattr(self.model, self.tenant_field):
            queryset = queryset.filter(**{self.tenant_field: tenant})

        return queryset


class UserManager(UserManager, SoftDeleteManager):
    """Manager for tenant-aware users"""
    def __init__(self, tenant_field='tenant'):
        super().__init__()
        self.tenant_field = tenant_field
    
    def get_queryset(self):
        tenant = get_current_tenant()
        queryset = super().get_queryset().all()

        if tenant and hasattr(self.model, self.tenant_field):
            queryset = queryset.filter(**{self.tenant_field: tenant})

        return queryset
    
