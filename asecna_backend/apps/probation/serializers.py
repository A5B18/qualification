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
        read_only_fields = ('id', 'created_at', 'updated_at', 'finalized_at')

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
