"""Admin pour l'app mentoring."""

from django.contrib import admin
from .models import MentoringRecord


@admin.register(MentoringRecord)
class MentoringRecordAdmin(admin.ModelAdmin):
    list_display  = ('agent', 'mentor', 'mentoring_status', 'start_date', 'submitted_at')
    list_filter   = ('mentoring_status',)
    search_fields = ('agent__matricule', 'mentor__matricule')
    readonly_fields = ('created_at', 'updated_at', 'submitted_at', 'approved_at')
