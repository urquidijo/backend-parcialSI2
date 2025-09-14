from django.contrib import admin
from .models import User, Role, Permission


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    pass


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code")


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # 👇 solo mostramos los campos que realmente existen
    list_display = ("id", "email", "first_name", "last_name", "role", "is_superuser")
