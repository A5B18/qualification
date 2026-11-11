"""Serializers pour reports."""

from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    agent_detail = serializers.SerializerMethodField()
    created_by_detail = serializers.SerializerMethodField()
    approved_by_detail = serializers.SerializerMethodField()
    approver_detail = serializers.SerializerMethodField()
    unit_chief_detail = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = '__all__'
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'submitted_at',
            'approved_at', 'created_by', 'approver',
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

    def get_created_by_detail(self, obj) -> dict | None:
        if obj.created_by:
            return {
                'id': obj.created_by.id,
                'first_name': obj.created_by.first_name,
                'last_name': obj.created_by.last_name,
            }
        return None

    def get_approved_by_detail(self, obj) -> dict | None:
        # Le modele Report stocke l'approbateur dans `approver`
        # (il n'existe pas de champ `approved_by` : l'ancienne version
        # levait une AttributeError -> HTTP 500 sur tout /reports/).
        if obj.approver:
            return {
                'id': obj.approver.id,
                'matricule': obj.approver.matricule,
                'first_name': obj.approver.first_name,
                'last_name': obj.approver.last_name,
            }
        return None

    def get_approver_detail(self, obj) -> dict | None:
        return self.get_approved_by_detail(obj)

    def get_unit_chief_detail(self, obj) -> dict | None:
        if obj.unit_chief:
            return {
                'id': obj.unit_chief.id,
                'matricule': obj.unit_chief.matricule,
                'first_name': obj.unit_chief.first_name,
                'last_name': obj.unit_chief.last_name,
            }
        return None
