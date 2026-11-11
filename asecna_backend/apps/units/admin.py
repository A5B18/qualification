"""Admin pour l'app units."""

from django.contrib import admin
from .models import Unit


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'unit_type', 'location', 'country', 'is_active')
    list_filter   = ('unit_type', 'is_active', 'country')
    search_fields = ('code', 'name', 'location')
    ordering      = ('code',)
