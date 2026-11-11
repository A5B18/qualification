"""Admin interface pour l'app accounts."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import User, UserRole, AgentProfile


class MatriculeAuthForm(AuthenticationForm):
    """Formulaire de connexion admin utilisisant le matricule."""
    username = forms.CharField(
        label=_('Matricule'),
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'placeholder': 'ex : ASE-2024-0001',
        }),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display    = ('matricule', 'full_name', 'email', 'is_active', 'is_staff', 'date_joined')
    list_filter     = ('is_active', 'is_staff', 'is_superuser')
    search_fields   = ('matricule', 'email', 'first_name', 'last_name')
    ordering        = ('matricule',)

    # Indique à Django admin d'utiliser 'matricule' au lieu de 'username'
    USERNAME_FIELD  = 'matricule'

    fieldsets = (
        (None, {'fields': ('matricule', 'password')}),
        (_('Informations personnelles'), {'fields': ('first_name', 'last_name', 'email', 'phone', 'photo')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Dates'), {'fields': ('date_joined', 'last_login')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('matricule', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    readonly_fields = ('date_joined', 'last_login')


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display  = ('user', 'role', 'is_active', 'assigned_by', 'assigned_at', 'revoked_at')
    list_filter   = ('role', 'is_active')
    search_fields = ('user__matricule', 'user__email')
    readonly_fields = ('assigned_at',)


@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'status', 'unit', 'specialty', 'hire_date')
    list_filter   = ('status',)
    search_fields = ('user__matricule', 'user__email')
