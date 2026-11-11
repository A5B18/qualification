"""Serializers pour agents."""

from rest_framework import serializers
from .models import AgentSkill, AgentCertification, PerformanceIndicator


class AgentSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentSkill
        fields = '__all__'
        read_only_fields = ('id',)


class AgentCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentCertification
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class PerformanceIndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceIndicator
        fields = '__all__'
        read_only_fields = ('id', 'created_at')
