"""URLs de l'app accounts — authentification et gestion des utilisateurs."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView,
    LogoutView,
    MeView,
    ChangePasswordView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # Authentification JWT
    path('login/',           CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('logout/',          LogoutView.as_view(),                name='logout'),
    path('token/refresh/',   TokenRefreshView.as_view(),          name='token_refresh'),

    # Profil personnel
    path('me/',              MeView.as_view(),                    name='me'),
    path('change-password/', ChangePasswordView.as_view(),        name='change_password'),

    # CRUD utilisateurs (admin)
    path('', include(router.urls)),
]
