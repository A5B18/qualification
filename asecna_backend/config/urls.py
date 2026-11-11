"""
Configuration URL principale — ASECNA Career Management API.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.accounts.admin import MatriculeAuthForm

# Utiliser le formulaire avec le champ 'matricule' pour la connexion admin
admin.site.login_form = MatriculeAuthForm
admin.site.site_header = "ASECNA Career Management"
admin.site.site_title  = "ASECNA Admin"
admin.site.index_title = "Administration"

urlpatterns = [
    # Interface d'administration Django
    path('admin/', admin.site.urls),

    # -------------------------------------------------------------------------
    # API v1
    # -------------------------------------------------------------------------
    path('api/v1/auth/',       include('apps.accounts.urls')),
    path('api/v1/units/',      include('apps.units.urls')),
    path('api/v1/agents/',     include('apps.agents.urls')),
    path('api/v1/probation/',  include('apps.probation.urls')),
    path('api/v1/mentoring/',  include('apps.mentoring.urls')),
    path('api/v1/training/',   include('apps.training.urls')),
    path('api/v1/evaluations/',include('apps.evaluations.urls')),
    path('api/v1/workflows/',  include('apps.workflows.urls')),
    path('api/v1/arcep/',      include('apps.arcep.urls')),
    path('api/v1/reports/',    include('apps.reports.urls')),
    path('api/v1/audit/',      include('apps.audit.urls')),

    # -------------------------------------------------------------------------
    # Documentation OpenAPI / Swagger
    # -------------------------------------------------------------------------
    path('api/schema/',        SpectacularAPIView.as_view(),         name='schema'),
    path('api/docs/',          SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/',         SpectacularRedocView.as_view(url_name='schema'),   name='redoc'),
]

# Fichiers médias en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Debug toolbar si installé
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
