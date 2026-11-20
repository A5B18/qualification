"""Serializers pour mentoring."""

from rest_framework import serializers
from .models import MentoringRecord


class MentoringRecordSerializer(serializers.ModelSerializer):
    agent_detail     = serializers.SerializerMethodField()
    mentor_detail    = serializers.SerializerMethodField()
    unit_chief_detail = serializers.SerializerMethodField()
    approved_by_detail = serializers.SerializerMethodField()

    class Meta:
        model  = MentoringRecord
        fields = '__all__'
        # Memes raisons que pour les rapports : la machine a etats appartient
        # aux actions `submit` / `approve` / `reject`. Un mentor pouvait sinon
        # approuver sa propre fiche par PATCH, sans passer par le chef d'unite.
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'submitted_at', 'approved_at',
            'mentoring_status', 'unit_chief', 'unit_chief_opinion',
        )

    def get_agent_detail(self, obj) -> dict | None:
        if obj.agent:
            return {
                'id': obj.agent.id,
                'matricule': obj.agent.matricule,
                'first_name': obj.agent.first_name,
                'last_name': obj.agent.last_name,
            }
        return None

    def get_mentor_detail(self, obj) -> dict | None:
        if obj.mentor:
            return {
                'id': obj.mentor.id,
                'first_name': obj.mentor.first_name,
                'last_name': obj.mentor.last_name,
            }
        return None

    def get_unit_chief_detail(self, obj) -> dict | None:
        unit_chief = getattr(obj, 'unit_chief', None)
        if unit_chief:
            return {
                'id': unit_chief.id,
                'first_name': unit_chief.first_name,
                'last_name': unit_chief.last_name,
            }
        return None

    def get_approved_by_detail(self, obj) -> dict | None:
        approved_by = getattr(obj, 'approved_by', None)
        if approved_by:
            return {
                'id': approved_by.id,
                'first_name': approved_by.first_name,
                'last_name': approved_by.last_name,
            }
        return None


class MentoringSubmitSerializer(serializers.Serializer):
    """Soumettre une fiche au chef d'unité."""
    unit_chief = serializers.IntegerField(help_text="ID du chef d'unité")


class MentoringDecisionSerializer(serializers.Serializer):
    """Approuver ou rejeter une fiche."""
    opinion = serializers.CharField(required=False, allow_blank=True, default='')
