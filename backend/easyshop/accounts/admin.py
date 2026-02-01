from django.contrib import admin
from core.models import Permission
from .models import RolePermission, UserPermission, User
# Register your models here.

@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
  fields = ('role_name', 'permission')
  list_display = ('role_name', 'permission')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
  fields = ("first_name", "last_name", "username", "email", "role_name", "photo")
  list_display = ("first_name", "last_name", "username", "email", "role_name", "photo")
  