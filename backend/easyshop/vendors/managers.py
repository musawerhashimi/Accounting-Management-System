# vendors/managers.py

from django.db import models
from django.db.models import Q, Sum, Avg, Count
from django.utils import timezone
from core.managers import TenantManager

class VendorQuerySet(models.QuerySet):
    """Custom queryset for Vendor model"""
    
    def active(self):
        """Get only active vendors"""
        return self.filter(status='active')
    
    def inactive(self):
        """Get inactive vendors"""
        return self.filter(status='inactive')
    
    def suspended(self):
        """Get suspended vendors"""
        return self.filter(status='suspended')
    
    def blacklisted(self):
        """Get blacklisted vendors"""
        return self.filter(status='blacklisted')
    
    def over_credit_limit(self):
        """Get vendors who have exceeded their credit limit"""
        return self.extra(where=["ABS(balance) > credit_limit"])
    
    def with_outstanding_balance(self):
        """Get vendors with outstanding payments"""
        return self.filter(balance__gt=0)
    
    def with_credit_balance(self):
        """Get vendors with credit balance (negative balance)"""
        return self.filter(balance__lt=0)
    
    def by_rating(self, min_rating=None, max_rating=None):
        """Filter vendors by rating range"""
        queryset = self
        if min_rating is not None:
            queryset = queryset.filter(rating__gte=min_rating)
        if max_rating is not None:
            queryset = queryset.filter(rating__lte=max_rating)
        return queryset
    
    def top_vendors_by_purchases(self, limit=10, year=None):
        """Get top vendors by purchase amount"""
        queryset = self.annotate(
            total_purchases=Sum(
                'purchases__total_amount',
                filter=Q(purchases__status='completed')
            )
        )
        
        if year:
            queryset = queryset.annotate(
                yearly_purchases=Sum(
                    'purchases__total_amount',
                    filter=Q(
                        purchases__status='completed',
                        purchases__purchase_date__year=year
                    )
                )
            ).order_by('-yearly_purchases')
        else:
            queryset = queryset.order_by('-total_purchases')
        
        return queryset[:limit]
    
    def with_recent_activity(self, days=30):
        """Get vendors with recent purchase activity"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return self.filter(purchases__purchase_date__gte=cutoff_date).distinct()
    
    def search(self, query):
        """Search vendors by name, code, email, or phone"""
        if not query:
            return self
        
        return self.filter(
            Q(name__icontains=query) |
            Q(vendor_code__icontains=query) |
            Q(contact_person__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query) |
            Q(tax_id__icontains=query)
        )
    
    def with_purchase_stats(self):
        """Annotate vendors with purchase statistics"""
        return self.annotate(
            total_purchase_count=Count('purchases'),
            total_purchase_amount=Sum('purchases__total_amount'),
            avg_purchase_amount=Avg('purchases__total_amount'),
            last_purchase_date=models.Max('purchases__purchase_date')
        )


class VendorManager(TenantManager):
    """Custom manager for Vendor model"""
    
    def get_queryset(self):
        return VendorQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def inactive(self):
        return self.get_queryset().inactive()
    
    def suspended(self):
        return self.get_queryset().suspended()
    
    def blacklisted(self):
        return self.get_queryset().blacklisted()
    
    def over_credit_limit(self):
        return self.get_queryset().over_credit_limit()
    
    def with_outstanding_balance(self):
        return self.get_queryset().with_outstanding_balance()
    
    def with_credit_balance(self):
        return self.get_queryset().with_credit_balance()
    
    def by_rating(self, min_rating=None, max_rating=None):
        return self.get_queryset().by_rating(min_rating=min_rating, max_rating=max_rating)
    
    def top_vendors_by_purchases(self, limit=10, year=None):
        return self.get_queryset().top_vendors_by_purchases(limit=limit, year=year)
    
    def with_recent_activity(self, days=30):
        return self.get_queryset().with_recent_activity(days=days)
    
    def search(self, query):
        return self.get_queryset().search(query)
    
    def with_purchase_stats(self):
        return self.get_queryset().with_purchase_stats()
    

class PurchaseQuerySet(models.QuerySet):
    def pending(self):
        return self.filter(status='pending')
    
    def received(self):
        return self.filter(status='received')
    
    def cancelled(self):
        return self.filter(status='cancelled')
    
    def by_date_range(self, start_date, end_date):
        return self.filter(purchase_date__range=[start_date, end_date])
    
    def search(self, query):
        return self.filter(
            models.Q(purchase_number__icontains=query) |
            models.Q(vendor__name__icontains=query) |
            models.Q(notes__icontains=query)
        )


class PurchaseManager(TenantManager):
    def get_queryset(self):
        return PurchaseQuerySet(self.model, using=self._db)
    
    def pending(self):
        return self.get_queryset().pending()
    
    def received(self):
        return self.get_queryset().received()
    
    def by_date_range(self, start_date, end_date):
        return self.get_queryset().by_date_range(start_date, end_date)
    
    def search(self, query):
        return self.get_queryset().search(query)

