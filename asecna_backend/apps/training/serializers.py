"""Serializers pour training."""

from rest_framework import serializers
from .models import (
    Specialty, Training, Course, Internship, QualificationMaintenance,
)


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = '__all__'


class TrainingSerializer(serializers.ModelSerializer):
    specialty_detail = serializers.SerializerMethodField()
    created_by_detail = serializers.SerializerMethodField()

    class Meta:
        model = Training
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by')

    def get_specialty_detail(self, obj) -> dict | None:
        if obj.specialty:
            return {'id': obj.specialty.id, 'code': obj.specialty.code, 'name': obj.specialty.name}
        return None

    def get_created_by_detail(self, obj) -> dict | None:
        created_by = getattr(obj, 'created_by', None)
        if created_by:
            return {'id': created_by.id, 'first_name': created_by.first_name, 'last_name': created_by.last_name}
        return None


class CourseSerializer(serializers.ModelSerializer):
    training_detail = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_training_detail(self, obj) -> dict | None:
        if obj.training:
            return {'id': obj.training.id, 'title': obj.training.title}
        return None


class InternshipSerializer(serializers.ModelSerializer):
    agent_detail    = serializers.SerializerMethodField()
    training_detail = serializers.SerializerMethodField()

    class Meta:
        model = Internship
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

    def get_agent_detail(self, obj) -> dict | None:
        if obj.agent:
            return {
                'id': obj.agent.id,
                'matricule': obj.agent.matricule,
                'first_name': obj.agent.first_name,
                'last_name': obj.agent.last_name,
            }
        return None

    def get_training_detail(self, obj) -> dict | None:
        if obj.training:
            return {
                'id': obj.training.id,
                'title': obj.training.title,
                'duration_days': obj.training.duration_days,
            }
        return None


class QualificationMaintenanceSerializer(serializers.ModelSerializer):
    """
    Contrôle de maintien de qualification (tous les 2 ans, minimum 70/100).

    Ce serializer était jusqu'ici absent du module : le `get_serializer_class()`
    de `QualificationMaintenanceViewSet` tentait de l'importer dans un
    `try/except ImportError` et retombait donc **systématiquement** sur une
    classe anonyme `_FallbackSerializer`. Conséquences : aucun champ `*_detail`
    exposé (la page Maintien QF affichait des lignes sans identité d'agent) et
    un schéma OpenAPI incorrect (deux composants nommés « _Fallback »).
    """

    agent_detail        = serializers.SerializerMethodField()
    training_detail     = serializers.SerializerMethodField()
    evaluated_by_detail = serializers.SerializerMethodField()
    score_passed        = serializers.BooleanField(read_only=True)
    is_overdue          = serializers.SerializerMethodField()

    class Meta:
        model  = QualificationMaintenance
        fields = '__all__'
        # Le score, l'évaluateur et l'horodatage sont posés par finalize()/waive()
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'evaluated_at', 'evaluated_by',
            'score', 'maintenance_status',
        )

    def get_agent_detail(self, obj) -> dict | None:
        if obj.agent_id and obj.agent:
            return {
                'id': obj.agent.id,
                'matricule': obj.agent.matricule,
                'first_name': obj.agent.first_name,
                'last_name': obj.agent.last_name,
                'full_name': obj.agent.full_name,
            }
        return None

    def get_training_detail(self, obj) -> dict | None:
        if obj.training_id and obj.training:
            return {
                'id': obj.training.id,
                'title': obj.training.title,
                'passing_score': obj.training.passing_score,
            }
        return None

    def get_evaluated_by_detail(self, obj) -> dict | None:
        if obj.evaluated_by_id and obj.evaluated_by:
            return {
                'id': obj.evaluated_by.id,
                'matricule': obj.evaluated_by.matricule,
                'first_name': obj.evaluated_by.first_name,
                'last_name': obj.evaluated_by.last_name,
            }
        return None

    def get_is_overdue(self, obj) -> bool:
        """True si l'échéance est dépassée et le contrôle toujours en attente."""
        import datetime
        return (
            obj.maintenance_status == QualificationMaintenance.MaintenanceStatus.PENDING
            and obj.due_date is not None
            and obj.due_date < datetime.date.today()
        )
