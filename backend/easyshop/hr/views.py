from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Sum
from django.utils import timezone
from core.permissions import TenantPermissionMixin, HasModulePermission
from core.pagination import StandardResultsSetPagination
from .models import Employee, EmployeePosition, EmployeeCareer, Member
from .serializers import (
    EmployeeSerializer, EmployeeListSerializer, EmployeeCreateUpdateSerializer,
    EmployeePositionSerializer, EmployeePositionListSerializer,
    EmployeeCareerSerializer, MemberSerializer, MemberListSerializer,
    EmployeeStatsSerializer
)
from .filters import EmployeeFilter, EmployeePositionFilter, MemberFilter


class EmployeePositionViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    model = EmployeePosition
    permission_module = 'hr'
    permission_classes = [HasModulePermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EmployeePositionFilter
    search_fields = ['position_name', 'description']
    ordering_fields = ['position_name', 'base_salary', 'created_at']
    ordering = ['position_name']

    def get_queryset(self):
        return EmployeePosition.objects.select_related(
            'department', 'currency'
        ).prefetch_related('careers')

    def get_serializer_class(self):
        if self.action == 'list':
            return EmployeePositionListSerializer
        return EmployeePositionSerializer

    @action(detail=True, methods=['get'])
    def employees(self, request, pk=None):
        """Get all employees in this position"""
        position = self.get_object()
        employees = Employee.objects.filter(
            careers__position=position,
            careers__status='active',
            careers__end_date__isnull=True
        ).distinct()
        
        serializer = EmployeeListSerializer(employees, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get position statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total_positions': queryset.count(),
            'active_positions': queryset.filter(is_active=True).count(),
            'avg_base_salary': queryset.aggregate(
                avg=Avg('base_salary')
            )['avg'] or 0,
            'positions_with_employees': queryset.filter(
                careers__status='active',
                careers__end_date__isnull=True
            ).distinct().count()
        }
        
        return Response(stats)


class EmployeeViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    model = Employee
    permission_module = 'hr'
    # permission_classes = [HasModulePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EmployeeFilter
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['name', 'hire_date', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        return Employee.objects.select_related(
            'created_by_user'
        ).prefetch_related(
            'careers__position',
            'careers__currency'
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return EmployeeListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return EmployeeCreateUpdateSerializer
        return EmployeeSerializer


    @action(detail=True, methods=['get'])
    def careers(self, request, pk=None):
        """Get employee career history"""
        employee = self.get_object()
        careers = employee.careers.select_related(
            'position', 'currency', 'created_by_user'
        ).order_by('-start_date')
        
        serializer = EmployeeCareerSerializer(careers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_career(self, request, pk=None):
        """Add new career/position for employee"""
        employee = self.get_object()
        serializer = EmployeeCareerSerializer(data=request.data)
        
        if serializer.is_valid():
            # End current active career if exists
            current_career = employee.careers.filter(
                status='active',
                end_date__isnull=True
            ).first()
            
            if current_career:
                current_career.end_date = serializer.validated_data['start_date']
                current_career.status = 'promoted'
                current_career.save()
            
            serializer.save(
                employee=employee,
                created_by_user=request.user
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def terminate(self, request, pk=None):
        """Terminate employee"""
        employee = self.get_object()
        termination_date = request.data.get('termination_date', timezone.now().date())
        reason = request.data.get('reason', '')
        
        # Update employee status
        employee.status = 'terminated'
        employee.save()
        
        # End active career
        active_career = employee.careers.filter(
            status='active',
            end_date__isnull=True
        ).first()
        
        if active_career:
            active_career.end_date = termination_date
            active_career.status = 'terminated'
            active_career.notes = f"Terminated. Reason: {reason}"
            active_career.save()
        
        return Response({'message': 'Employee terminated successfully'})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get employee statistics"""
        queryset = self.get_queryset()
        
        # Calculate service years for active employees
        active_employees = queryset.filter(status='active')
        today = timezone.now().date()
        
        service_years = []
        for emp in active_employees:
            years = (today - emp.hire_date).days / 365.25
            service_years.append(years)
        
        avg_service_years = sum(service_years) / len(service_years) if service_years else 0
        
        # Calculate average salary
        active_careers = EmployeeCareer.objects.filter(
            employee__tenant=request.user.tenant,
            status='active',
            end_date__isnull=True
        )
        avg_salary = active_careers.aggregate(avg=Avg('salary'))['avg'] or 0
        
        stats = {
            'total_employees': queryset.count(),
            'active_employees': queryset.filter(status='active').count(),
            'inactive_employees': queryset.filter(status='inactive').count(),
            'terminated_employees': queryset.filter(status='terminated').count(),
            'avg_salary': avg_salary,
            'avg_service_years': round(avg_service_years, 1),
            'total_positions': EmployeePosition.objects.filter(
                tenant=request.user.tenant
            ).count()
        }
        
        serializer = EmployeeStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def birthdays_this_month(self, request):
        """Get employees with birthdays this month"""
        # This would require a birthday field in the model
        # For now, returning empty list
        return Response([])


class EmployeeCareerViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    model = EmployeeCareer
    permission_module = 'hr'
    # permission_classes = [HasModulePermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['employee__name', 'position__position_name', 'notes']
    ordering_fields = ['start_date', 'end_date', 'salary', 'created_at']
    ordering = ['-start_date']

    def get_queryset(self):
        return EmployeeCareer.objects.select_related(
            'employee', 'position', 'currency', 'created_by_user'
        )

    def get_serializer_class(self):
        return EmployeeCareerSerializer

    def perform_create(self, serializer):
        serializer.save(created_by_user=self.request.user)

    @action(detail=True, methods=['post'])
    def end_career(self, request, pk=None):
        """End this career position"""
        career = self.get_object()
        end_date = request.data.get('end_date', timezone.now().date())
        status_choice = request.data.get('status', 'terminated')
        notes = request.data.get('notes', '')
        
        career.end_date = end_date
        career.status = status_choice
        if notes:
            career.notes = f"{career.notes}\n{notes}" if career.notes else notes
        career.save()
        
        serializer = self.get_serializer(career)
        return Response(serializer.data)


class MemberViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    permission_module = 'hr'
    # permission_classes = [HasModulePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = MemberFilter
    search_fields = ['name']
    ordering_fields = ['name', 'ownership_percentage', 'investment_amount', 'start_date']
    ordering = ['name']

    def get_queryset(self):
        return Member.objects.select_related('currency')

    def get_serializer_class(self):
        if self.action == 'list':
            return MemberListSerializer
        return MemberSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get member statistics"""
        queryset = self.get_queryset()
        active_members = queryset.filter(status='active')
        
        stats = {
            'total_members': queryset.count(),
            'active_members': active_members.count(),
            'total_ownership': active_members.aggregate(
                total=Sum('ownership_percentage')
            )['total'] or 0,
            'total_investment': active_members.aggregate(
                total=Sum('investment_amount')
            )['total'] or 0,
            'avg_ownership': active_members.aggregate(
                avg=Avg('ownership_percentage')
            )['avg'] or 0
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def ownership_distribution(self, request):
        """Get ownership distribution"""
        active_members = self.get_queryset().filter(status='active')
        
        distribution = []
        for member in active_members:
            distribution.append({
                'name': member.name,
                'ownership_percentage': member.ownership_percentage,
                'investment_amount': member.investment_amount
            })
        
        return Response(distribution)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw member from business"""
        member = self.get_object()
        withdrawal_date = request.data.get('withdrawal_date', timezone.now().date())
        reason = request.data.get('reason', '')
        
        member.end_date = withdrawal_date
        member.status = 'withdrawn'
        member.save()
        
        return Response({'message': 'Member withdrawn successfully'})

    @action(detail=True, methods=['post'])
    def calculate_profit_share(self, request, pk=None):
        """Calculate profit share for member"""
        member = self.get_object()
        total_profit = request.data.get('total_profit', 0)
        
        if total_profit > 0:
            member_share = (member.profit_share / 100) * total_profit
            return Response({
                'member_name': member.name,
                'profit_share_percentage': member.profit_share,
                'total_profit': total_profit,
                'member_profit_share': member_share
            })
        
        return Response({'error': 'Total profit must be greater than 0'}, 
                       status=status.HTTP_400_BAD_REQUEST)