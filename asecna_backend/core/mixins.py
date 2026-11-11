"""
Mixins DRF réutilisables.
"""

from rest_framework.response import Response
from rest_framework import status


class SoftDeleteMixin:
    """
    Surcharge destroy() pour effectuer un soft delete (is_active=False)
    au lieu de supprimer physiquement l'objet.
    Le modèle doit posséder un champ BooleanField `is_active`.
    """

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuditMixin:
    """
    Injecte automatiquement `created_by` et `updated_by`
    depuis request.user lors de la sauvegarde.
    Le modèle doit posséder les champs ForeignKey correspondants.
    """

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
