from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmployeeViewSet,
    EmployeePositionViewSet,
    EmployeeCareerViewSet,
    MemberViewSet,
)

app_name = 'hr'

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'positions', EmployeePositionViewSet, basename='position')
router.register(r'careers', EmployeeCareerViewSet, basename='career')
router.register(r'members', MemberViewSet, basename='member')

urlpatterns = [
    path('', include(router.urls)),
    
    # Additional custom endpoints
    path('employees/<int:employee_id>/careers/', 
         EmployeeViewSet.as_view({'get': 'careers'}), 
         name='employee-careers'),
    path('employees/<int:employee_id>/add-career/', 
         EmployeeViewSet.as_view({'post': 'add_career'}), 
         name='employee-add-career'),
    path('employees/<int:employee_id>/terminate/', 
         EmployeeViewSet.as_view({'post': 'terminate'}), 
         name='employee-terminate'),
    
    path('positions/<int:position_id>/employees/', 
         EmployeePositionViewSet.as_view({'get': 'employees'}), 
         name='position-employees'),
    
    path('careers/<int:career_id>/end/', 
         EmployeeCareerViewSet.as_view({'post': 'end_career'}), 
         name='career-end'),
    
    path('members/<int:member_id>/withdraw/', 
         MemberViewSet.as_view({'post': 'withdraw'}), 
         name='member-withdraw'),
    path('members/<int:member_id>/profit-share/', 
         MemberViewSet.as_view({'post': 'calculate_profit_share'}), 
         name='member-profit-share'),
    
    # Stats endpoints
    path('employees/stats/', 
         EmployeeViewSet.as_view({'get': 'stats'}), 
         name='employee-stats'),
    path('positions/stats/', 
         EmployeePositionViewSet.as_view({'get': 'stats'}), 
         name='position-stats'),
    path('members/stats/', 
         MemberViewSet.as_view({'get': 'stats'}), 
         name='member-stats'),
    path('members/ownership-distribution/', 
         MemberViewSet.as_view({'get': 'ownership_distribution'}), 
         name='member-ownership-distribution'),
]