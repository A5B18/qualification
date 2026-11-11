"""Serializers pour l'app units."""

from rest_framework import serializers
from .models import Unit


class UnitSerializer(serializers.ModelSerializer):
    chief_detail = serializers.SerializerMethodField()
    agents_count = serializers.SerializerMethodField()

    class Meta:
        model  = Unit
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_chief_detail(self, obj) -> dict | None:
        """
        Chef de l'unite : le modele Unit n'a pas de champ `chief`, on le deduit
        de l'agent affecte a l'unite qui porte le role UNIT_CHIEF.
        """
        chief_profile = obj.agents.filter(
            user__user_roles__role='UNIT_CHIEF',
            user__user_roles__is_active=True,
            user__is_active=True,
        ).select_related('user').first()
        if not chief_profile:
            return None
        chief = chief_profile.user
        return {
            'id': chief.id,
            'first_name': chief.first_name,
            'last_name': chief.last_name,
            'full_name': chief.full_name,
            'matricule': chief.matricule,
        }

    def get_agents_count(self, obj) -> int:
        """
        Nombre d'agents affectes a cette unite.

        AgentProfile.unit expose le related_name `agents` : l'ancienne version
        interrogeait `obj.members`, inexistant, et l'exception etant avalee
        le compteur affichait toujours 0.
        """
        return obj.agents.count()
