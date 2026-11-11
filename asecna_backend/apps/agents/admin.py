"""Admin pour l'app agents."""

from django.contrib import admin
from .models import AgentSkill, AgentCertification, PerformanceIndicator


@admin.register(AgentSkill)
class AgentSkillAdmin(admin.ModelAdmin):
    list_display = ('agent', 'name', 'level', 'acquired_at')
    list_filter = ('level',)
    search_fields = ('agent__matricule', 'name')


@admin.register(AgentCertification)
class AgentCertificationAdmin(admin.ModelAdmin):
    list_display = ('agent', 'name', 'issuing_body', 'issue_date', 'expiry_date')
    search_fields = ('agent__matricule', 'name')


@admin.register(PerformanceIndicator)
class PerformanceIndicatorAdmin(admin.ModelAdmin):
    list_display = ('agent', 'year', 'score', 'evaluator', 'created_at')
    list_filter = ('year',)
    search_fields = ('agent__matricule',)
