"""Serializers pour evaluations."""

from django.core.exceptions import ValidationError as DjangoValidationError
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

    def validate(self, attrs):
        """
        Fait respecter les regles du QCM — le seul format accepte.

        L'ecran de composition propose quatre champs d'option dont deux
        restent souvent vides : on les ecarte ici plutot que de refuser la
        saisie. La bonne reponse est ensuite realignee sur l'orthographe
        exacte de l'option retenue, pour que la correction et la preselection
        du bouton radio portent sur la meme chaine.
        """
        current = self.instance

        def value_of(field, default):
            if field in attrs:
                return attrs[field]
            return getattr(current, field, default) if current else default

        kind    = value_of('question_kind', Question.QuestionKind.MCQ)
        options = Question.normalize_options(value_of('options', []))
        correct = (value_of('correct_answer', '') or '').strip()

        probe = Question(question_kind=kind, options=options, correct_answer=correct)
        try:
            probe.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

        # Orthographe canonique : celle de l'option, pas celle de la frappe.
        match = next(
            (opt for opt in options if opt.casefold() == correct.casefold()),
            correct,
        )

        attrs['options'] = options
        attrs['correct_answer'] = match
        attrs['question_kind'] = Question.QuestionKind.MCQ
        return attrs


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
    # Avancement de la correction : sans ces compteurs, l'ecran de correction
    # ne pouvait pas indiquer combien de reponses restaient a corriger, et le
    # bouton « Soumettre » partait vers un 400 « N reponse(s) non corrigees ».
    answers_count = serializers.SerializerMethodField()
    corrected_count = serializers.SerializerMethodField()
    pending_correction_count = serializers.SerializerMethodField()

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

    def get_answers_count(self, obj) -> int:
        return obj.answers.count()

    def get_corrected_count(self, obj) -> int:
        return obj.answers.filter(evaluator_score__isnull=False).count()

    def get_pending_correction_count(self, obj) -> int:
        return obj.answers.filter(evaluator_score__isnull=True).count()

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
        """
        Enonce joint a la reponse.

        Les options du QCM en font partie : elles ne sont pas le corrige, et
        sans elles un agent qui relit sa copie ne voit que sa propre reponse,
        sans les choix qui lui etaient proposes. `correct_answer` reste
        ajoutee par la vue, pour les seuls profils habilites a corriger.
        """
        if obj.question:
            return {
                'id': obj.question.id,
                'text': obj.question.text,
                'question_type': obj.question.question_type,
                'question_kind': obj.question.question_kind,
                'options': obj.question.clean_options,
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


class QuestionPublicSerializer(serializers.ModelSerializer):
    """
    Enonce presente a l'agent pendant la composition.

    Volontairement ampute de `correct_answer` : le serializer complet
    (`QuestionSerializer`, avec `fields = '__all__'`) exposait la bonne reponse
    a quiconque listait les questions, y compris l'agent en train de composer.
    """

    # Les options sont renormalisees a la lecture : une question creee avant
    # la generalisation du QCM peut porter des entrees vides, et l'ecran de
    # composition afficherait alors un bouton radio sans libelle.
    options = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ('id', 'text', 'question_type', 'question_kind',
                  'difficulty', 'options', 'points')

    def get_options(self, obj) -> list:
        return obj.clean_options


class AnswerGradeSerializer(serializers.Serializer):
    """
    Correction d'une reponse par l'evaluateur.

    Declare pour que drf-spectacular documente le corps de `grade-answer`
    (il etait lu directement dans `request.data`, donc absent du schema).
    La validation fine (bornes du bareme, is_correct textuel) reste dans la
    vue, qui doit repondre 400 avec le message metier attendu par le
    frontend.
    """

    answer_id       = serializers.IntegerField()
    is_correct      = serializers.BooleanField()
    evaluator_score = serializers.DecimalField(max_digits=4, decimal_places=2)
    feedback        = serializers.CharField(required=False, allow_blank=True, default='')
