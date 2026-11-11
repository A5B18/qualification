"""Views pour evaluations — correction manuelle par les évaluateurs."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from core.permissions import IsEvaluator, IsUnitChief, IsEvaluatorOrInstructor, IsApproverOrUnitChief
from .models import Question, Exam, ExamSession, Answer
from .serializers import (
    QuestionSerializer, ExamSerializer, ExamSessionSerializer,
    AnswerSerializer, AnswerSubmitSerializer,
)


# =============================================================================
# Questions — banque de questions (EVALUATEUR / INSTRUCTEUR uniquement)
# =============================================================================

class QuestionViewSet(viewsets.ModelViewSet):
    """
    Banque de questions d'évaluation.
    Lecture : tout agent authentifié.
    Création / modification / suppression : EVALUATEUR ou INSTRUCTEUR.
    """
    queryset = (Question.objects.filter(is_active=True)
                .select_related('training', 'created_by')
                .order_by('-created_at', '-id'))
    serializer_class = QuestionSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        # Création, modification, suppression → EVALUATEUR ou INSTRUCTEUR
        return [IsAuthenticated(), IsEvaluatorOrInstructor()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# =============================================================================
# Exams — création/publication des examens
# =============================================================================

class ExamViewSet(viewsets.ModelViewSet):
    """
    Examens. Création réservée aux EVALUATEURS/INSTRUCTEURS.
    Les agents authentifiés peuvent lister et démarrer une session.
    """
    queryset = Exam.objects.all().order_by('-created_at').select_related('training', 'created_by')
    serializer_class = ExamSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'start_session'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsEvaluatorOrInstructor()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='start-session')
    def start_session(self, request, pk=None):
        """Un agent démarre une session d'examen."""
        exam = self.get_object()
        if exam.exam_status != Exam.ExamStatus.PUBLISHED:
            return Response(
                {'error': {'code': 'bad_request', 'message': "L'examen n'est pas publié."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        session, created = ExamSession.objects.get_or_create(
            exam=exam, agent=request.user,
            defaults={'session_status': ExamSession.SessionStatus.IN_PROGRESS},
        )
        return Response(
            ExamSessionSerializer(session).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


# =============================================================================
# ExamSessions — soumission (agent) + correction manuelle (évaluateur) +
#               approbation (chef d'unité)
# =============================================================================

class ExamSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Sessions d'examen.

    Workflow :
      1. Agent → submit-answers  (IN_PROGRESS → SUBMITTED)
      2. Évaluateur → grade-answer (SUBMITTED → CORRECTING, réponse par réponse)
      3. Évaluateur → submit-for-approval (CORRECTING → PENDING_APPROVAL)
      4. Chef d'unité → approve / reject (PENDING_APPROVAL → GRADED | REJECTED)
    """
    serializer_class = ExamSessionSerializer
    # Jamais consulte a l'execution (get_queryset ci-dessous le remplace) ;
    # present pour que drf-spectacular type le parametre de chemin `id`
    # en entier au lieu de le deduire d'un get_queryset() qui echoue
    # hors requete.
    queryset = ExamSession.objects.none()

    def get_queryset(self):
        user = self.request.user
        base = ExamSession.objects.select_related(
            'exam', 'agent', 'graded_by', 'approved_by',
        )
        if user.is_admin or user.has_role('EVALUATOR') or user.has_role('UNIT_CHIEF'):
            qs = base.all()
        else:
            # Agent standard : uniquement ses propres sessions
            qs = base.filter(agent=user)
        agent_id = self.request.query_params.get('agent')
        if agent_id:
            qs = qs.filter(agent_id=agent_id)
        exam_id = self.request.query_params.get('exam')
        if exam_id:
            qs = qs.filter(exam_id=exam_id)
        session_status = self.request.query_params.get('session_status')
        if session_status:
            qs = qs.filter(session_status=session_status)
        # Ordre explicite : sans lui la pagination DRF est instable
        return qs.order_by('-started_at', '-id')

    # ── 1. Agent soumet ses réponses ──────────────────────────────────────────

    @action(detail=True, methods=['post'], url_path='submit-answer')
    def submit_answer(self, request, pk=None):
        """Soumettre une réponse à une question (agent uniquement)."""
        session = self.get_object()
        if session.agent != request.user:
            return Response(
                {'error': {'code': 'forbidden', 'message': 'Vous ne pouvez soumettre que vos propres réponses.'}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if session.session_status != ExamSession.SessionStatus.IN_PROGRESS:
            return Response(
                {'error': {'code': 'bad_request', 'message': 'La session n\'est plus en cours.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = AnswerSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            question = Question.objects.get(pk=serializer.validated_data['question'])
            answer, _ = Answer.objects.update_or_create(
                session=session, question=question,
                defaults={'response': serializer.validated_data['response']},
            )
            return Response(AnswerSerializer(answer).data)
        except Question.DoesNotExist:
            return Response(
                {'error': {'code': 'not_found', 'message': 'Question introuvable.'}},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=['post'], url_path='finalize')
    def finalize(self, request, pk=None):
        """Agent finalise et soumet sa copie → statut SUBMITTED."""
        session = self.get_object()
        if session.agent != request.user:
            return Response({'error': {'code': 'forbidden', 'message': 'Accès refusé.'}},
                            status=status.HTTP_403_FORBIDDEN)
        if session.session_status != ExamSession.SessionStatus.IN_PROGRESS:
            return Response({'error': {'code': 'bad_request', 'message': 'Session déjà soumise ou clôturée.'}},
                            status=status.HTTP_400_BAD_REQUEST)
        session.session_status = ExamSession.SessionStatus.SUBMITTED
        session.submitted_at = timezone.now()
        session.save(update_fields=['session_status', 'submitted_at', 'updated_at'])
        return Response(ExamSessionSerializer(session).data)

    # ── 2. Évaluateur corrige réponse par réponse ────────────────────────────

    @action(detail=True, methods=['post'], url_path='grade-answer',
            permission_classes=[IsAuthenticated, IsEvaluator])
    def grade_answer(self, request, pk=None):
        """
        EVALUATEUR : corrige une réponse spécifique.
        Body : { answer_id, is_correct, evaluator_score, feedback }
        """
        session = self.get_object()
        if session.session_status not in (
            ExamSession.SessionStatus.SUBMITTED,
            ExamSession.SessionStatus.CORRECTING,
            ExamSession.SessionStatus.REJECTED,  # re-correction après rejet
        ):
            return Response(
                {'error': {'code': 'bad_request',
                           'message': 'La session doit être SUBMITTED, CORRECTING ou REJECTED pour être corrigée.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answer_id      = request.data.get('answer_id')
        is_correct     = request.data.get('is_correct')
        evaluator_score = request.data.get('evaluator_score')
        feedback       = request.data.get('feedback', '')

        if answer_id is None or is_correct is None or evaluator_score is None:
            return Response(
                {'error': {'code': 'bad_request',
                           'message': 'Champs requis : answer_id, is_correct, evaluator_score.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            answer = Answer.objects.select_related('question').get(pk=answer_id, session=session)
        except Answer.DoesNotExist:
            return Response({'error': {'code': 'not_found', 'message': 'Réponse introuvable.'}},
                            status=status.HTTP_404_NOT_FOUND)

        # Le score était converti par un float() non protégé : une valeur non
        # numérique (champ laissé vide côté formulaire) provoquait une ValueError
        # non interceptée, donc une 500 au lieu d'une erreur de saisie.
        try:
            score_value = float(evaluator_score)
        except (TypeError, ValueError):
            return Response(
                {'error': {'code': 'bad_request',
                           'message': 'Le score attribué doit être un nombre.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_points = answer.question.points
        if not (0 <= score_value <= max_points):
            return Response(
                {'error': {'code': 'bad_request',
                           'message': f'Le score doit être compris entre 0 et '
                                      f'{max_points} (barème de la question).'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # bool('false') vaut True : on interprète explicitement les valeurs texte
        if isinstance(is_correct, str):
            if is_correct.strip().lower() not in ('true', 'false', '1', '0'):
                return Response(
                    {'error': {'code': 'bad_request',
                               'message': "Le champ is_correct doit être un booléen."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            is_correct_value = is_correct.strip().lower() in ('true', '1')
        else:
            is_correct_value = bool(is_correct)

        answer.apply_correction(
            evaluator=request.user,
            score=score_value,
            is_correct=is_correct_value,
            feedback=feedback,
        )

        # Passer la session en CORRECTING si elle était SUBMITTED
        if session.session_status == ExamSession.SessionStatus.SUBMITTED:
            session.session_status = ExamSession.SessionStatus.CORRECTING
            session.save(update_fields=['session_status', 'updated_at'])

        return Response(AnswerSerializer(answer).data)

    # ── 3. Évaluateur soumet pour approbation ─────────────────────────────────

    @action(detail=True, methods=['post'], url_path='submit-for-approval',
            permission_classes=[IsAuthenticated, IsEvaluator])
    def submit_for_approval(self, request, pk=None):
        """
        EVALUATEUR : soumet la correction au chef d'unité.
        Calcule le score automatiquement à partir des scores par réponse.
        Session → PENDING_APPROVAL.
        """
        session = self.get_object()
        if session.session_status not in (
            ExamSession.SessionStatus.CORRECTING,
            ExamSession.SessionStatus.REJECTED,
        ):
            return Response(
                {'error': {'code': 'bad_request',
                           'message': 'La session doit être CORRECTING ou REJECTED pour soumettre.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérifier que toutes les réponses ont été corrigées
        uncorrected = session.answers.filter(evaluator_score__isnull=True).count()
        if uncorrected > 0:
            return Response(
                {'error': {'code': 'incomplete',
                           'message': f'{uncorrected} réponse(s) n\'ont pas encore été corrigées.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        score = session.compute_score_from_items()
        session.submit_for_approval(evaluator=request.user, score=score)
        return Response(ExamSessionSerializer(session).data)

    # ── 4. Chef d'unité approuve ou rejette ──────────────────────────────────

    @action(detail=True, methods=['post'], url_path='approve',
            permission_classes=[IsAuthenticated, IsApproverOrUnitChief])
    def approve(self, request, pk=None):
        """
        CHEF_UNITE / APPROBATEUR : approuve la correction.
        Le score devient officiel, is_passed est calculé.
        """
        session = self.get_object()
        if session.session_status != ExamSession.SessionStatus.PENDING_APPROVAL:
            return Response(
                {'error': {'code': 'bad_request',
                           'message': 'La session doit être en PENDING_APPROVAL pour être approuvée.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        session.approve(unit_chief=request.user)
        return Response(ExamSessionSerializer(session).data)

    @action(detail=True, methods=['post'], url_path='reject',
            permission_classes=[IsAuthenticated, IsApproverOrUnitChief])
    def reject(self, request, pk=None):
        """
        CHEF_UNITE / APPROBATEUR : rejette la correction.
        L'évaluateur devra recorriger.
        Body : { reason }
        """
        session = self.get_object()
        if session.session_status != ExamSession.SessionStatus.PENDING_APPROVAL:
            return Response(
                {'error': {'code': 'bad_request',
                           'message': 'La session doit être en PENDING_APPROVAL pour être rejetée.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = request.data.get('reason', '')
        if not reason:
            return Response({'error': {'code': 'bad_request', 'message': 'Un motif de rejet est obligatoire.'}},
                            status=status.HTTP_400_BAD_REQUEST)
        session.reject(unit_chief=request.user, reason=reason)
        return Response(ExamSessionSerializer(session).data)
