"""Serializers pour workflows."""

from rest_framework import serializers
from .models import ApprovalWorkflow


class ApprovalWorkflowSerializer(serializers.ModelSerializer):
    """Serializer du workflow d'approbation avec champs lisibles."""

    # Noms lisibles des acteurs.
    # `full_name` est une PROPRIETE du modele User (qui derive de
    # AbstractBaseUser) : appeler get_full_name() comme sur AbstractUser
    # levait une AttributeError -> HTTP 500 sur /workflows/ et /workflows/pending/
    # des que la table contenait une ligne.
    submitted_by_name = serializers.SerializerMethodField()
    approver_name     = serializers.SerializerMethodField()
    content_type_label = serializers.SerializerMethodField()

    class Meta:
        model  = ApprovalWorkflow
        fields = '__all__'
        read_only_fields = (
            'id', 'created_at', 'updated_at',
            'submitted_at', 'approved_at', 'rejected_at',
            'submitted_by_name', 'approver_name', 'content_type_label',
        )

    def get_submitted_by_name(self, obj) -> str | None:
        if obj.submitted_by:
            return obj.submitted_by.full_name or obj.submitted_by.matricule
        return None

    def get_approver_name(self, obj) -> str | None:
        if obj.approver:
            return obj.approver.full_name or obj.approver.matricule
        return None

    def get_content_type_label(self, obj) -> str | None:
        return str(obj.content_type) if obj.content_type_id else None
