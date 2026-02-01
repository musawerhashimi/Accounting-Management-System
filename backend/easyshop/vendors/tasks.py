
# vendors/tasks.py (for Celery background tasks)
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Purchase


@shared_task
def auto_close_received_purchases():
    """Automatically close purchases that have been fully received for 30 days"""
    cutoff_date = timezone.now() - timedelta(days=30)
    
    purchases_to_close = Purchase.objects.filter(
        status='received',
        updated_at__lte=cutoff_date
    )
    
    closed_count = 0
    for purchase in purchases_to_close:
        purchase.status = 'closed'
        purchase.save()
        closed_count += 1
    
    return f"Closed {closed_count} purchases"


@shared_task
def send_purchase_reminders():
    """Send reminders for overdue purchases"""
    overdue_purchases = Purchase.objects.filter(
        status__in=['ordered', 'approved'],
        delivery_date__lt=timezone.now()
    )
    
    # Implementation for sending notifications
    # This would integrate with your notification system
    
    return f"Sent reminders for {overdue_purchases.count()} overdue purchases"

