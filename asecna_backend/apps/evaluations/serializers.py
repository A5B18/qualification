"""Serializers pour evaluations."""

from rest_framework import serializers
from .models import Question, Exam, ExamSession, Answer


class QuestionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by')

    def get_created_by_name(self, obj) -> str | None:
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return None


class ExamSerializer(serializers.ModelSerializer):
    training_detail = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    questions_count = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by')

    def get_training_detail(self, obj) -> dict | None:
        if obj.training:
            return {'id': obj.training.id, 'title': obj.training.title}
        return None

    def get_created_by_name(self, obj) -> str | None:
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return None

    def get_questions_count(self, obj) -> int:
        return obj.questions.count()


class ExamSessionSerializer(serializers.ModelSerializer):
    exam_detail = serializers.SerializerMethodField()
    agent_detail = serializers.SerializerMethodField()
    graded_by_detail = serializers.SerializerMethodField()
    approved_by_detail = serializers.SerializerMethodField()

    class Meta:
        model = ExamSession
        fields = '__all__'
        read_only_fields = (
            'id', 'started_at', 'submitted_at', 'graded_at',
            'approved_at', 'score', 'is_passed', 'created_at', 'updated_at',
        )

    def get_exam_detail(self, obj) -> dict | None:
        if obj.exam:
            return {'id': obj.exam.id, 'title': obj.exam.title, 'passing_score': obj.exam.passing_score}
        return None

    def get_agent_detail(self, obj) -> dict | None:
        if obj.agent:
            return {
                'id': obj.agent.id,
                'matricule': obj.agent.matricule,
                'first_name': obj.agent.first_name,
                'last_name': obj.agent.last_name,
            }
        return None

    def get_graded_by_detail(self, obj) -> dict | None:
        if obj.graded_by:
            return {'id': obj.graded_by.id, 'first_name': obj.graded_by.first_name, 'last_name': obj.graded_by.last_name}
        return None

    def get_approved_by_detail(self, obj) -> dict | None:
        if obj.approved_by:
            return {'id': obj.approved_by.id, 'first_name': obj.approved_by.first_name, 'last_name': obj.approved_by.last_name}
        return None


class AnswerSerializer(serializers.ModelSerializer):
    question_detail = serializers.SerializerMethodField()
    corrected_by_detail = serializers.SerializerMethodField()

    class Meta:
        model = Answer
        fields = '__all__'
        read_only_fields = ('id', 'answered_at', 'corrected_at')

    def get_question_detail(self, obj) -> dict | None:
        if obj.question:
            return {
                'id': obj.question.id,
                'text': obj.question.text,
                'question_type': obj.question.question_type,
                'points': obj.question.points,
            }
        return None

    def get_corrected_by_detail(self, obj) -> dict | None:
        if obj.corrected_by:
            return {'id': obj.corrected_by.id, 'first_name': obj.corrected_by.first_name, 'last_name': obj.corrected_by.last_name}
        return None


class AnswerSubmitSerializer(serializers.Serializer):
    """Soumettre une réponse lors d'une session d'examen."""
    question = serializers.IntegerField()
    response = serializers.CharField()
