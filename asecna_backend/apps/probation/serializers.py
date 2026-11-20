"""Serializers pour probation."""

from rest_framework import serializers
from .models import ProbationPeriod


class ProbationPeriodSerializer(serializers.ModelSerializer):
    is_last_attempt = serializers.BooleanField(read_only=True)
    is_renewable    = serializers.BooleanField(read_only=True)
    agent_detail    = serializers.SerializerMethodField()
    evaluated_by_detail = serializers.SerializerMethodField()

    class Meta:
        model  = ProbationPeriod
        fields = '__all__'
        # Le resultat d'une periode d'essai s'enregistre par l'action
        # `finalize`, seule a appliquer le seuil de 70/100 et la transition de
        # statut de l'agent (MENTORED ou RETIRED). Un PATCH direct sur
        # `probation_status` contournait ces deux regles.
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'finalized_at',
            'probation_status', 'score', 'evaluated_by', 'actual_end_date',
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

    def get_evaluated_by_detail(self, obj) -> dict | None:
        evaluated_by = getattr(obj, 'evaluated_by', None)
        if evaluated_by:
            return {
                'id': evaluated_by.id,
                'first_name': evaluated_by.first_name,
                'last_name': evaluated_by.last_name,
            }
        return None
