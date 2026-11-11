"""Admin pour l'app audit."""

from django.contrib import admin
from .models import AuditLog, LoginHistory


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'endpoint', 'status_code', 'ip_address', 'timestamp')
    list_filter = ('action', 'status_code')
    search_fields = ('user__matricule', 'endpoint')
    readonly_fields = ('timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('matricule_attempted', 'result', 'ip_address', 'timestamp')
    list_filter = ('result',)
    readonly_fields = ('timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
