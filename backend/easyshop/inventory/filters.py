# inventory/filters.py
import django_filters

from .models import (
    Inventory
)

class InventoryFilter(django_filters.FilterSet):
    """Filter for Inventory model"""
    warehouse_id = django_filters.NumberFilter(field_name="location", lookup_expr='exact')
    category_id = django_filters.NumberFilter(field_name="variant__product__category_id", lookup_expr="exact")
    department_id = django_filters.NumberFilter(field_name="variant__product__category__department_id", lookup_expr="exact")
    
    is_loved = django_filters.BooleanFilter(method='filter_is_loved')
    is_favorite = django_filters.BooleanFilter(method='filter_is_favorite')
    is_bookmarked = django_filters.BooleanFilter(method='filter_is_bookmarked')
    
    class Meta:
        model = Inventory
        fields = [
            'category_id', 'department_id', 'warehouse_id',
            'is_loved', 'is_favorite', 'is_bookmarked',
            
        ]
    
    def filter_is_loved(self, queryset, name, value):
        if not value:
            return queryset
        
        user = self.request.user
        return queryset.filter(variant__user_preferences__user=user, variant__user_preferences__is_loved=True)

    def filter_is_favorite(self, queryset, name, value):
        if not value:
            return queryset
        
        user = self.request.user
        return queryset.filter(variant__user_preferences__user=user, variant__user_preferences__is_favorite=True)
        
    def filter_is_bookmarked(self, queryset, name, value):
        if not value:
            return queryset
        
        user = self.request.user
        return queryset.filter(variant__user_preferences__user=user, variant__user_preferences__is_bookmarked=True)
        
    