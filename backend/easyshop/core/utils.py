from decimal import Decimal
from .models import CurrencyRate
from django.utils.timezone import now

def get_exchange_rate(currency_id, target_date):
    """
    Return the exchange rate for a given currency on a specific date.
    If no rate is found, fallback to 1.0 (assuming base currency).
    """
    if not currency_id:
        return Decimal("1.0")

    if not target_date:
        target_date = now()
    rate_obj = (
        CurrencyRate.objects
        .filter(currency_id=currency_id, effective_date__lte=target_date)
        .order_by("-effective_date")
        .first()
    )
    
    return rate_obj.rate if rate_obj else Decimal("1.0")


exchange_rate_cache = {}

def get_cached_exchange_rate(currency_id, date):
    cache_key = f"{currency_id}_{date}"
    if cache_key not in exchange_rate_cache:
        exchange_rate_cache[cache_key] = get_exchange_rate(currency_id, date)
    return exchange_rate_cache[cache_key]