from rest_framework import permissions
from django.core.exceptions import PermissionDenied

from accounts.models import User


class IsTenantUser(permissions.BasePermission):
    """
    Permission class to ensure user belongs to the tenant being accessed.
    This is the base permission class that should be used in all tenant-aware views.
    """
    message = "You don't have permission to access this data."
    
    def has_permission(self, request, view):
        """Check if user is authenticated and has tenant access"""
        if not request.user.is_authenticated:
            return False
        
        # Allow superusers to access any tenant
        if request.user.is_superuser:
            return True
        
        # Check if user has a tenant
        return request.tenant == request.user.tenant
        # if not hasattr(request.user, 'tenant_id') or not request.user.tenant_id:
        #     return False
        
        # return True
    
    def has_object_permission(self, request, view, obj):
        """Check if user can access the specific object"""
        if not request.user.is_authenticated:
            return False
        
        # Superusers can access everything
        if request.user.is_superuser:
            return True
        
        # Check if object has tenant_id attribute
        if hasattr(obj, 'tenant_id'):
            return obj.tenant_id == request.user.tenant.id
        elif hasattr(obj, 'tenant'):
            return obj.tenant == request.user.tenant
        
        # For objects without tenant relationship, allow access
        return True


class IsSelfOrHasPermission(permissions.BasePermission):
    """
    Permission class to ensure user has the permission or it is the user itself accessing this
    """
    message = "You don't have permission to access this data."
    
    def has_object_permission(self, request, view, obj):
        """Check if user can access the specific object"""
        if not request.user.is_authenticated:
            return False
        
        # Superusers can access everything
        if request.user.is_superuser:
            return True
        
        if obj.id == request.user.id:
            return True
        
        # Get permission requirements from view
        permission_module = getattr(view, 'permission_module', None)
        permission_action = getattr(view, 'permission_action', None)
        
        if not permission_module or not permission_action:
            return True
        # Map HTTP methods to actions if not explicitly set
        if permission_action == 'auto':
            action_map = {
                'GET': 'view',
                'POST': 'add',
                'PUT': 'change',
                'PATCH': 'change',
                'DELETE': 'delete',
            }
            permission_action = action_map.get(request.method, 'view')
        
                
        # Check if user has the permission through their roles
        return _user_has_permission(request.user, permission_module, permission_action)


class HasTenantLogoPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        """Check if user has required module permission"""
        if request.method == "GET":
            return True
        
        if not request.user.is_authenticated:
            return False
        
        # Superusers have all permissions
        if request.user.is_superuser:
            return True
                
        # Check if user has the permission through their roles
        return _user_has_permission(request.user, 'settings', 'change')


class HasModulePermission(permissions.BasePermission):
    """
    Permission class for checking module-specific permissions.
    Usage: Add permission_module and permission_action attributes to your view.
    """
    
    def has_permission(self, request, view):
        """Check if user has required module permission"""
        if not request.user.is_authenticated:
            return False
        
        # Superusers have all permissions
        if request.user.is_superuser:
            return True
        
        # Get permission requirements from view
        permission_module = getattr(view, 'permission_module', None)
        permission_action = getattr(view, 'permission_action', None)
        
        if not permission_module or not permission_action:
            return True
            # If no specific permission is required, just check tenant access
            # return hasattr(request.user, 'tenant_id') and request.user.tenant_id
        
        # Map HTTP methods to actions if not explicitly set
        if permission_action == 'auto':
            action_map = {
                'GET': 'view',
                'POST': 'add',
                'PUT': 'change',
                'PATCH': 'change',
                'DELETE': 'delete',
            }
            permission_action = action_map.get(request.method, 'view')
        
                
        # Check if user has the permission through their roles
        return _user_has_permission(request.user, permission_module, permission_action)


class IsTenantOwnerOrAdmin(permissions.BasePermission):
    """
    Permission for tenant owners or admins only.
    """
    message = "Only administrators can perform this action."
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        user: User = request.user
        # Check if user is tenant owner or admin
        if request.tenant == user.tenant:
            # You can customize this logic based on your role system
            return user.role_name == 'admin'
        
        return False


class IsSystemAdmin(permissions.BasePermission):
    """
    Permission for system administrators only.
    """
    message = "Only system administrators can perform this action."
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser


class CanAccessTenantSettings(permissions.BasePermission):
    """
    Permission for accessing tenant settings.
    """
    message = "You don't have permission to modify settings."
    
    def has_permission(self, request, view):
        user: User = request.user
        if not user.is_authenticated:
            return False
        
        if user.is_superuser:
            return True
        
        # Only allow GET requests for non-admin users
        if request.method in permissions.SAFE_METHODS:
            return request.tenant == user.tenant
        
        # For modify operations, check admin role
        return user.role_name == 'admin'
        

class TenantPermissionMixin:
    """
    Mixin to add tenant-aware permission checking to views.
    """
    permission_classes = [IsTenantUser]
    permission_module = None
    permission_action = 'auto'
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions that this view requires.
        """
        if hasattr(self, 'action') and self.action:
            action_obj = getattr(self.__class__, self.action, None)
            if action_obj is not None:
                # check if the action has its own permission_classes defined
                if hasattr(action_obj, 'kwargs') and 'permission_classes' in action_obj.kwargs:
                    return [permission() for permission in action_obj.kwargs['permission_classes']]
                
                if hasattr(action_obj, 'kwargs') and 'permission_module' in action_obj.kwargs:
                    self.permission_module = action_obj.kwargs['permission_module']
        permission_classes = self.permission_classes.copy()
        
        # Add module permission if specified
        if self.permission_module:
            permission_classes.append(HasModulePermission)
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Filter queryset by tenant if the model has tenant relationship.
        """
        queryset = super().get_queryset()
        
        if not self.request.user.is_superuser:
            # Check if model has tenant relationship
            if hasattr(queryset.model, 'tenant'):
                queryset = queryset.filter(tenant=self.request.user.tenant)
        
        return queryset

    def perform_create(self, serializer):
        """
        Set tenant_id when creating objects.
        """
        # Check if the model has tenant relationship
        if hasattr(serializer.Meta.model, 'tenant'):
            if hasattr(serializer.Meta.model, 'created_by_user'):
                serializer.save(tenant=self.request.tenant, created_by_user=self.request.user)
            else:
                serializer.save(tenant=self.request.tenant)
        else:
            serializer.save()

    def perform_destroy(self, instance):
        if hasattr(instance, 'deleted_at'):
            if hasattr(instance, 'soft_delete'):
                instance.soft_delete()
            else:
                from django.utils.timezone import now
                instance.deleted_at = now()
            return
        instance.delete()


# Decorator for function-based views
def tenant_required(view_func):
    """
    Decorator to ensure user belongs to a tenant.
    """
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required.")
        
        if not request.user.is_superuser:
            if request.tenant != request.user.tenant:
                raise PermissionDenied("User does not belong to this tenant.")
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def permission_required(permission_module, permission_action):
    """
    Decorator to check specific permission.
    """
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required.")
            
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            
            permission_codename = f"{permission_module}.{permission_action}"
            if not _user_has_permission(request.user, permission_module, permission_action):
                raise PermissionDenied(f"Permission '{permission_codename}' required.")
                
            # Check permission through user roles
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


def _user_has_permission(user: User, permission_module, permission_action):
    """Check if user has specific permission through their roles"""
    from accounts.models import UserPermission, RolePermission  # Import here to avoid circular imports
    permission_actions = [permission_action, 'all']
    override = UserPermission.objects.filter(
        user=user,
        permission__module=permission_module,
        permission__action__in=permission_actions
    )
    if override.exists():
        if override.count() > 1:
            override = override.filter(permission_action='all')
        return override.first().allow
    try:
        # Get user's roles and check permissions
        role_name = user.role_name
        return RolePermission.objects.filter(
            role_name=role_name,
            permission__module=permission_module,
            permission__action__in=permission_actions
        ).exists()
    except:
        return False
        