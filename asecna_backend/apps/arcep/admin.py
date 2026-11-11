"""Admin pour l'app arcep."""

from django.contrib import admin
from .models import ARCEPBook, ARCEPEntry, ARCEPSignature


@admin.register(ARCEPBook)
class ARCEPBookAdmin(admin.ModelAdmin):
    list_display = ('agent', 'opened_at', 'is_active')
    list_filter = ('is_active',)


@admin.register(ARCEPEntry)
class ARCEPEntryAdmin(admin.ModelAdmin):
    list_display = ('book', 'entry_date', 'duration_hours')
    list_filter = ('entry_date',)
    search_fields = ('book__agent__matricule',)


@admin.register(ARCEPSignature)
class ARCEPSignatureAdmin(admin.ModelAdmin):
    list_display = ('book', 'unit_chief', 'period_start', 'period_end', 'signed_at')
