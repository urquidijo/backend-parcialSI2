# condominio/admin.py
from django.contrib import admin
from .models import Property, PropertyTenant

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("id", "edificio", "numero", "owner", "estado", "area_m2")
    search_fields = ("numero", "owner__email")
    list_filter = ("edificio", "estado")

@admin.register(PropertyTenant)
class PropertyTenantAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "user")
    search_fields = ("property__numero", "user__email")
    list_filter = ("property__edificio",)
