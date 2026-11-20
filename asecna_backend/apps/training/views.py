"""Views pour training — spécialités, formations, cours, stages, maintien qualification."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from core.permissions import (
    IsInstructor, IsAdministrator, IsEvaluator, IsApproverOrUnitChief,
    IsEvaluatorOrUnitChiefOrApprover,
)
from core.mixins import SoftDeleteMixin
from .models import Specialty, Training, Course, Internship, QualificationMaintenance
from .serializers import (
    SpecialtySerializer, TrainingSerializer, CourseSerializer,
    InternshipSerializer, QualificationMaintenanceSerializer,
)


class SpecialtyViewSet(SoftDeleteMixin, viewsets.ModelViewSet):
    """
    Spécialités — gérées par l'admin uniquement, consultables par tous.

    La suppression est logique (`is_active=False`). `SoftDeleteMixin` était
    importé par ce module sans être branché : un DELETE effaçait réellement la
    ligne, et les profils d'agents qui la référencaient perdaient leur
    spécialité (FK en SET_NULL) sans trace de ce qu'elle était.
    """
    queryset = Specialty.objects.filter(is_active=True).order_by('code')
    serializer_class = SpecialtySerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            # `DEFAULT_PERMISSION_CLASSES` impose déjà l'authentification.
            return super().get_permissions()
        return [IsAdministrator()]


class TrainingViewSet(SoftDeleteMixin, viewsets.ModelViewSet):
    """
    Formations (qualifiantes EAMAC, e-learning, ateliers).
    Consultation libre ; création/modification réservée à l'admin.

    Suppression logique : une formation supprimée reste référencée par les
    examens, les stages et les contrôles de maintien déjà passés.
    """
    queryset = Training.objects.filter(is_active=True).order_by('title')
    serializer_class = TrainingSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return super().get_permissions()
        return [IsAdministrator()]


class CourseViewSet(viewsets.ModelViewSet):
    """
    Cours e-learning.
    Lecture : tout agent (cours publiés uniquement).
    Création/modification : INSTRUCTEUR propriétaire du cours.
    """
    serializer_class = CourseSerializer
    # Jamais consulte a l'execution (get_queryset ci-dessous le remplace) ;
    # present pour que drf-spectacular type le parametre de chemin `id`
    # en entier au lieu de le deduire d'un get_queryset() qui echoue
    # hors requete.
    queryset = Course.objects.none()

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.has_role('INSTRUCTOR'):
            # L'instructeur voit ses propres cours publiés et non publiés
            if user.has_role('INSTRUCTOR') and not user.is_admin:
                qs = Course.objects.filter(instructor=user)
            else:
                qs = Course.objects.all()
        else:
            # Autres agents : uniquement les cours publiés
            qs = Course.objects.filter(is_published=True)

        qs = qs.select_related('training', 'instructor')
        training_id = self.request.query_params.get('training')
        if training_id:
            qs = qs.filter(training_id=training_id)
        is_published = self.request.query_params.get('is_published')
        if is_published in ('true', 'True', '1'):
            qs = qs.filter(is_published=True)
        elif is_published in ('false', 'False', '0'):
            qs = qs.filter(is_published=False)
        return qs.order_by('training', 'order', 'id')

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsInstructor()]

    def perform_create(self, serializer):
        """Force l'instructeur à être l'utilisateur connecté."""
        serializer.save(instructor=self.request.user)

    def perform_update(self, serializer):
        """Un instructeur ne peut modifier que ses propres cours."""
        # `serializer.instance` est l'objet deja charge par la vue :
        # `self.get_object()` relancait une requete et refaisait les controles
        # d'objet pour rien.
        if not self._owns(serializer.instance):
            raise PermissionDenied("Vous ne pouvez modifier que vos propres cours.")
        serializer.save()

    def _owns(self, course) -> bool:
        """True si l'utilisateur courant peut agir sur ce cours."""
        user = self.request.user
        return bool(user.is_admin or course.instructor_id == user.pk)

    @action(detail=True, methods=['post'], url_path='publish',
            permission_classes=[IsAuthenticated, IsInstructor])
    def publish(self, request, pk=None):
        """Publier un cours (instructeur propriétaire uniquement)."""
        return self._set_published(True)

    @action(detail=True, methods=['post'], url_path='unpublish',
            permission_classes=[IsAuthenticated, IsInstructor])
    def unpublish(self, request, pk=None):
        """Dépublier un cours (instructeur propriétaire uniquement)."""
        return self._set_published(False)

    def _set_published(self, published: bool) -> Response:
        """Publication et depublication ne differaient que par un booleen."""
        course = self.get_object()
        if not self._owns(course):
            return Response({'error': {'code': 'forbidden', 'message': 'Accès refusé.'}},
                            status=status.HTTP_403_FORBIDDEN)
        course.is_published = published
        course.save(update_fields=['is_published'])
        return Response(self.get_serializer(course).data)


class InternshipViewSet(viewsets.ModelViewSet):
    """
    Stages (qualifiants ou non qualifiants).
    Lecture : agent (les siens) + UNIT_CHIEF + ADMIN.
    Création/modification : ADMIN uniquement.
    """
    serializer_class = InternshipSerializer
    # Jamais consulte a l'execution (get_queryset ci-dessous le remplace) ;
    # present pour que drf-spectacular type le parametre de chemin `id`
    # en entier au lieu de le deduire d'un get_queryset() qui echoue
    # hors requete.
    queryset = Internship.objects.none()

    def get_queryset(self):
        user = self.request.user
        base = Internship.objects.select_related('agent', 'training')
        if user.is_admin or user.has_role('UNIT_CHIEF'):
            qs = base.all()
        else:
            qs = base.filter(agent=user)
        agent_id = self.request.query_params.get('agent')
        if agent_id:
            qs = qs.filter(agent_id=agent_id)
        return qs.order_by('-start_date', '-id')

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdministrator()]


class QualificationMaintenanceViewSet(viewsets.ModelViewSet):
    """
    Maintien de qualification (tous les 2 ans, score minimum 70/100).

    Workflow :
      1. Admin crée la session de maintien avec due_date
      2. EVALUATEUR finalise avec le score → PASSED ou FAILED
         - FAILED → agent passe automatiquement à SUSPENDED
      3. UNIT_CHIEF peut dispenser (WAIVED)

    Actions :
      POST .../finalize/ → EVALUATEUR saisit le score
      POST .../waive/    → UNIT_CHIEF dispense l'agent
      GET  .../overdue/  → sessions en retard (due_date < aujourd'hui + PENDING)
    """
    serializer_class = QualificationMaintenanceSerializer
    # Jamais utilisé à l'exécution (get_queryset ci-dessous prend le relais),
    # mais permet à drf-spectacular de typer correctement le paramètre `id`
    # du chemin : sans cet attribut, il appelait get_queryset() hors requête,
    # l'appel échouait, et le schéma déclarait `id` comme une chaîne.
    queryset = QualificationMaintenance.objects.none()

    def get_queryset(self):
        user = self.request.user
        base = QualificationMaintenance.objects.select_related('agent', 'training', 'evaluated_by')
        if user.is_admin or user.has_any_role('UNIT_CHIEF', 'APPROVER', 'EVALUATOR'):
            qs = base.all()
        else:
            qs = base.filter(agent=user)
        agent_id = self.request.query_params.get('agent')
        if agent_id:
            qs = qs.filter(agent_id=agent_id)
        maintenance_status = self.request.query_params.get('maintenance_status')
        if maintenance_status:
            qs = qs.filter(maintenance_status=maintenance_status)
        return qs.order_by('-due_date', '-id')

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        if self.action in ('finalize',):
            return [IsAuthenticated(), IsEvaluator()]
        if self.action in ('waive',):
            return [IsAuthenticated(), IsApproverOrUnitChief()]
        if self.action == 'overdue':
            # Liste des retards : évaluateurs, chefs d'unité et approbateurs.
            # Avant, cette action retombait sur IsAdministrator et renvoyait donc
            # 403 aux EVALUATEURS et aux UNIT_CHIEF que la vue autorise pourtant.
            return [IsAuthenticated(), IsEvaluatorOrUnitChiefOrApprover()]
        return [IsAuthenticated(), IsAdministrator()]

    @action(detail=True, methods=['post'], url_path='finalize')
    def finalize(self, request, pk=None):
        """
        EVALUATEUR : enregistre le résultat du contrôle de maintien.
        Body : { score, notes }
        Règle : score >= 70 → PASSED ; score < 70 → FAILED + agent SUSPENDED.
        """
        maintenance = self.get_object()
        if maintenance.maintenance_status not in (
            QualificationMaintenance.MaintenanceStatus.PENDING,
        ):
            return Response(
                {'error': {'code': 'bad_request',
                           'message': 'Seuls les contrôles en attente peuvent être finalisés.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        score = request.data.get('score')
        if score is None:
            return Response(
                {'error': {'code': 'bad_request', 'message': 'Le score est obligatoire.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            score = float(score)
        except (TypeError, ValueError):
            return Response(
                {'error': {'code': 'bad_request', 'message': 'Le score doit être un nombre.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (0 <= score <= 100):
            return Response(
                {'error': {'code': 'bad_request', 'message': 'Score entre 0 et 100.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        notes = request.data.get('notes', '')
        maintenance.finalize(evaluator=request.user, score=score, notes=notes)
        return Response(self.get_serializer(maintenance).data)

    @action(detail=True, methods=['post'], url_path='waive',
            permission_classes=[IsAuthenticated, IsApproverOrUnitChief])
    def waive(self, request, pk=None):
        """UNIT_CHIEF : dispense l'agent du contrôle (cas exceptionnel)."""
        maintenance = self.get_object()
        if maintenance.maintenance_status != QualificationMaintenance.MaintenanceStatus.PENDING:
            return Response(
                {'error': {'code': 'bad_request', 'message': 'Seuls les contrôles en attente peuvent être dispensés.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        maintenance.maintenance_status = QualificationMaintenance.MaintenanceStatus.WAIVED
        maintenance.notes = request.data.get('notes', 'Dispensé par le chef d\'unité.')
        maintenance.evaluated_by = request.user
        maintenance.evaluated_at = timezone.now()
        maintenance.save(update_fields=[
            'maintenance_status', 'notes', 'evaluated_by', 'evaluated_at', 'updated_at',
        ])
        return Response(self.get_serializer(maintenance).data)

    @action(detail=False, methods=['get'], url_path='overdue')
    def overdue(self, request):
        """
        Contrôles de maintien en retard (échéance dépassée, statut PENDING).

        L'habilitation est portée par `get_permissions`
        (`IsEvaluatorOrUnitChiefOrApprover`). Le contrôle de rôle qui figurait
        aussi dans le corps de la vue excluait les APPROBATEURS, pourtant
        admis par la classe de permission : la porte était ouverte puis
        refermée deux lignes plus loin.
        """
        overdue_qs = QualificationMaintenance.objects.filter(
            maintenance_status=QualificationMaintenance.MaintenanceStatus.PENDING,
            due_date__lt=timezone.localdate(),
        ).select_related('agent', 'training', 'evaluated_by').order_by('due_date')

        serializer = self.get_serializer(overdue_qs, many=True)
        # `len()` sur la liste serialisee : `overdue_qs.count()` relancait une
        # requete COUNT sur un queryset deja parcouru.
        return Response({'count': len(serializer.data), 'results': serializer.data})
