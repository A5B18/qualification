"""Admin pour l'app probation."""

from django.contrib import admin
from .models import ProbationPeriod


@admin.register(ProbationPeriod)
class ProbationPeriodAdmin(admin.ModelAdmin):
    list_display  = ('agent', 'attempt_number', 'start_date', 'end_date', 'probation_status')
    list_filter   = ('probation_status', 'attempt_number')
    search_fields = ('agent__matricule', 'agent__email')
    readonly_fields = ('created_at', 'updated_at')
