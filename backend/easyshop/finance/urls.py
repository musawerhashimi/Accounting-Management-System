from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
  ExpenseCategoryViewSet,
  CashDrawerViewSet,
  MonthlyReportViewSet,
  QuickReportViewSet,
  SaleItemDetailViewSet,
  TransactionViewSet,
  ExpenseViewSet,
  MonthlyPaymentViewSet,
  YearlyReportViewSet
)


router = DefaultRouter()
router.register('expense-categories', ExpenseCategoryViewSet, basename='ExpenseCategoryViewSet')
router.register('cash-drawers', CashDrawerViewSet, basename='CashDrawerViewSet')
router.register('transactions', TransactionViewSet, basename='TransactionViewSet')
router.register('expenses', ExpenseViewSet, basename='ExpenseViewSet')
router.register('monthly-payments', MonthlyPaymentViewSet, basename='MonthlyPaymentViewSet')
router.register('quick-reports', QuickReportViewSet, basename='quick-reports')
router.register('reports', MonthlyReportViewSet, basename='reports')
router.register('sales-data', SaleItemDetailViewSet, basename='sales-data')
router.register('yearly-reports', YearlyReportViewSet, basename='yearly-report')
     

urlpatterns = [
  path('', include(router.urls))
]
