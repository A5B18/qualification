"""Admin pour l'app reports."""

from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'agent', 'report_status', 'created_at')
    list_filter = ('report_type', 'report_status')
    search_fields = ('title', 'agent__matricule')
    readonly_fields = ('created_at', 'updated_at', 'submitted_at', 'approved_at')
