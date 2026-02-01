from rest_framework.permissions import BasePermission


class HRPermission(BasePermission):
    """
    Custom permission class for HR module operations
    """
    
    def has_permission(self, request, view):
        """
        Check if user has permission to access HR module
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get user's active role
        user_role = getattr(request.user, 'user_roles', None)
        if not user_role:
            return False
        
        active_role = user_role.filter(is_active=True).first()
        if not active_role:
            return False
        
        # Define required permissions based on action
        action = getattr(view, 'action', None)
        
        # Admin users have all permissions
        if active_role.role_name == 'admin':
            return True
        
        # HR managers have full access to HR module
        if active_role.role_name == 'hr_manager':
            return True
        
        # Managers have limited access
        if active_role.role_name == 'manager':
            # Managers can read employee data and some basic operations
            if action in ['list', 'retrieve', 'statistics', 'payroll_summary']:
                return True
            # Can promote employees
            if action == 'promote':
                return True
            return False
        
        # Supervisors have read-only access
        if active_role.role_name == 'supervisor':
            if action in ['list', 'retrieve']:
                return True
            return False
        
        # Check custom permissions using the role's permission system
        return self._check_module_permission(active_role, action)
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user has permission to access specific HR object
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get user's active role
        user_role = getattr(request.user, 'user_roles', None)
        if not user_role:
            return False
        
        active_role = user_role.filter(is_active=True).first()
        if not active_role:
            return False
        
        # Admin and HR managers have access to all objects
        if active_role.role_name in ['admin', 'hr_manager']:
            return True
        
        # Additional object-level permissions can be implemented here
        # For example, employees might only see their own records
        
        return self.has_permission(request, view)
    
    def _check_module_permission(self, role, action):
        """
        Check if role has specific permission for HR module action
        """
        if not role.permissions:
            return False
        
        hr_permissions = role.permissions.get('hr', [])
        
        # Map actions to required permissions
        action_permission_map = {
            'list': 'read',
            'retrieve': 'read',
            'create': 'create',
            'update': 'update',
            'partial_update': 'update',
            'destroy': 'delete',
            'statistics': 'read',
            'payroll_summary': 'read',
            'promote': 'update',
            'career_history': 'read',
            'ownership_summary': 'read',
            'adjust_ownership': 'update',
        }
        
        required_permission = action_permission_map.get(action, 'read')
        return required_permission in hr_permissions


class EmployeePermission(BasePermission):
    """
    Specific permission class for Employee operations
    """
    
    def has_permission(self, request, view):
        """Check employee-specific permissions"""
        return HRPermission().has_permission(request, view)
    
    def has_object_permission(self, request, view, obj):
        """
        Employee-specific object permissions
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get user's active role
        user_role = getattr(request.user, 'user_roles', None)
        if not user_role:
            return False
        
        active_role = user_role.filter(is_active=True).first()
        if not active_role:
            return False
        
        # Admin and HR managers have access to all employees
        if active_role.role_name in ['admin', 'hr_manager']:
            return True
        
        # Employees can only view their own record (if user is linked to employee)
        if hasattr(request.user, 'employee_profile'):
            if request.method in ['GET', 'HEAD', 'OPTIONS']:
                return obj == request.user.employee_profile
        
        # Managers might have access to employees in their department
        if active_role.role_name == 'manager':
            # This would require additional logic to determine department hierarchy
            # For now, allow read access
            if request.method in ['GET', 'HEAD', 'OPTIONS']:
                return True
        
        return False


class PayrollPermission(BasePermission):
    """
    Permission class for payroll-related operations
    """
    
    def has_permission(self, request, view):
        """Check payroll access permissions"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'user_roles', None)
        if not user_role:
            return False
        
        active_role = user_role.filter(is_active=True).first()
        if not active_role:
            return False
        
        # Only admin, HR managers, and accountants can access payroll
        allowed_roles = ['admin', 'hr_manager', 'accountant']
        
        if active_role.role_name in allowed_roles:
            return True
        
        # Check custom permissions
        if active_role.permissions:
            payroll_permissions = active_role.permissions.get('payroll', [])
            return 'read' in payroll_permissions
        
        return False


class MemberPermission(BasePermission):
    """
    Permission class for business member operations
    """
    
    def has_permission(self, request, view):
        """Check member access permissions"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'user_roles', None)
        if not user_role:
            return False
        
        active_role = user_role.filter(is_active=True).first()
        if not active_role:
            return False
        
        # Only admin and specific roles can access member data
        if active_role.role_name == 'admin':
            return True
        
        # Members might be able to view their own information
        action = getattr(view, 'action', None)
        if action in ['list', 'retrieve'] and active_role.role_name in ['manager', 'hr_manager']:
            return True
        
        # Check custom permissions
        if active_role.permissions:
            member_permissions = active_role.permissions.get('members', [])
            action_permission_map = {
                'list': 'read',
                'retrieve': 'read',
                'create': 'create',
                'update': 'update',
                'partial_update': 'update',
                'destroy': 'delete',
                'ownership_summary': 'read',
                'adjust_ownership': 'update',
            }
            
            required_permission = action_permission_map.get(action, 'read')
            return required_permission in member_permissions
        
        return False