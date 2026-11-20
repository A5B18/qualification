"""Views pour arcep — avec contrôle d'accès strict selon les rôles."""

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsUnitChief

from apps.arcep.models import ARCEPBook, ARCEPEntry, ARCEPSignature
from apps.arcep.serializers import ARCEPBookSerializer, ARCEPEntrySerializer, ARCEPSignatureSerializer


def _sees_all_books(user) -> bool:
    """
    True si l'utilisateur consulte les carnets de toute son unite.

    Le meme predicat etait recopie dans les trois ViewSets de l'app : une
    evolution de la liste des roles encadrants en aurait oublie un.
    """
    return bool(user.is_admin or user.has_any_role('UNIT_CHIEF', 'APPROVER'))


class ARCEPBookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Carnet ARCEP — lecture seule via l'API.
    Création automatique via signal (statut QUALIFIED).
    Seul l'admin peut créer/supprimer via l'interface d'admin.

    Lecture :
      - Agent : uniquement son carnet
      - UNIT_CHIEF / ADMIN : tous les carnets
    """
    serializer_class = ARCEPBookSerializer
    # Jamais consulte a l'execution (get_queryset ci-dessous le remplace) ;
    # present pour que drf-spectacular type le parametre de chemin `id`
    # en entier au lieu de le deduire d'un get_queryset() qui echoue
    # hors requete.
    queryset = ARCEPBook.objects.none()

    def get_queryset(self):
        user = self.request.user
        base = (
            ARCEPBook.objects
            # En-tete d'identite : profession, unite, statut de parcours.
            .select_related(
                'agent',
                'agent__agent_profile',
                'agent__agent_profile__unit',
                'agent__agent_profile__specialty',
            )
            # Qualifications et echeances + etat des visas. Sans ce
            # prechargement, chaque carnet de la liste declenchait une
            # requete par source de qualification et une par entree.
            .prefetch_related(
                'agent__user_roles',
                'agent__certifications',
                'agent__qualification_maintenances__training',
                'agent__internships__training',
                'entries',
                'signatures',
            )
            .annotate(
                total_hours_agg=Sum('entries__duration_hours'),
                entries_count_agg=Count('entries', distinct=True),
            )
        )
        if _sees_all_books(user):
            qs = base.all()
        else:
            qs = base.filter(agent=user)
        # Filtre ?agent=<id> utilise par la fiche detaillee d'un agent
        agent_id = self.request.query_params.get('agent')
        if agent_id:
            qs = qs.filter(agent_id=agent_id)
        # Ordre explicite : sans lui la pagination DRF est instable
        return qs.order_by('-opened_at', 'id')

    def get_permissions(self):
        return [IsAuthenticated()]


class ARCEPEntryViewSet(viewsets.ModelViewSet):
    """
    Entrées du carnet ARCEP.

    Permissions :
      - Lecture : agent (ses propres entrées) + UNIT_CHIEF/ADMIN
      - Création : agent (uniquement dans son propre carnet)
      - Modification/suppression : agent concerné (tant que non validée) ou ADMIN
    """
    serializer_class = ARCEPEntrySerializer
    # Jamais consulte a l'execution (get_queryset ci-dessous le remplace) ;
    # present pour que drf-spectacular type le parametre de chemin `id`
    # en entier au lieu de le deduire d'un get_queryset() qui echoue
    # hors requete.
    queryset = ARCEPEntry.objects.none()

    def get_queryset(self):
        user = self.request.user
        if _sees_all_books(user):
            qs = ARCEPEntry.objects.all().select_related('book', 'book__agent')
        else:
            # Agent : uniquement ses propres entrées
            qs = ARCEPEntry.objects.filter(book__agent=user).select_related('book', 'book__agent')
        # Filtres ?book=<id> / ?agent=<id> : sans eux le frontend affichait
        # toutes les entrées de tous les carnets sous chaque carnet.
        book_id = self.request.query_params.get('book')
        if book_id:
            qs = qs.filter(book_id=book_id)
        agent_id = self.request.query_params.get('agent')
        if agent_id:
            qs = qs.filter(book__agent_id=agent_id)
        return qs.order_by('-entry_date', '-id')

    def get_permissions(self):
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Vérifie que l'agent ne crée une entrée que dans son propre carnet."""
        user = self.request.user
        book = serializer.validated_data.get('book')
        if book and not user.is_admin and book.agent != user:
            raise PermissionDenied("Vous ne pouvez ajouter des entrées que dans votre propre carnet.")
        serializer.save()

    def perform_update(self, serializer):
        """Empêche la modification d'une entrée déjà validée (sauf admin)."""
        user = self.request.user
        instance = self.get_object()
        if not user.is_admin and instance.is_validated:
            raise PermissionDenied("Cette entrée a été signée par le chef d'unité et ne peut plus être modifiée.")
        if not user.is_admin and instance.book.agent != user:
            raise PermissionDenied("Vous ne pouvez modifier que vos propres entrées.")
        serializer.save()


class ARCEPSignatureViewSet(viewsets.ModelViewSet):
    """
    Signatures du carnet ARCEP.

    Règle métier : seul un CHEF_UNITE peut signer.
    Une signature valide toutes les entrées de la période couverte.

    Lecture : agent (ses signatures) + UNIT_CHIEF + ADMIN
    Création/modification : UNIT_CHIEF uniquement
    """
    serializer_class = ARCEPSignatureSerializer
    # Jamais consulte a l'execution (get_queryset ci-dessous le remplace) ;
    # present pour que drf-spectacular type le parametre de chemin `id`
    # en entier au lieu de le deduire d'un get_queryset() qui echoue
    # hors requete.
    queryset = ARCEPSignature.objects.none()

    def get_queryset(self):
        user = self.request.user
        base = ARCEPSignature.objects.select_related('book', 'book__agent', 'unit_chief')
        if _sees_all_books(user):
            qs = base.all()
        else:
            qs = base.filter(book__agent=user)
        book_id = self.request.query_params.get('book')
        if book_id:
            qs = qs.filter(book_id=book_id)
        agent_id = self.request.query_params.get('agent')
        if agent_id:
            qs = qs.filter(book__agent_id=agent_id)
        return qs.order_by('-signed_at', '-id')

    def get_permissions(self):
        # `covered_entries` est une lecture : un agent doit pouvoir consulter
        # les entrées couvertes par la signature de son propre carnet.
        # Elle retombait auparavant sur IsUnitChief et renvoyait donc 403.
        if self.action in ('list', 'retrieve', 'covered_entries'):
            return [IsAuthenticated()]
        # Seul le chef d'unité peut signer
        return [IsAuthenticated(), IsUnitChief()]

    def create(self, request, *args, **kwargs):
        """
        Crée une signature.

        Si la période n'est pas transmise, elle est déduite des entrées du
        carnet qui ne sont pas encore couvertes par une signature — c'est le
        comportement annoncé par l'interface (« la signature couvre toutes les
        entrées non encore signées »), qui n'envoie que `book` et `comment`.
        Le calcul est fait ici, avant la validation, car la période participe à
        une contrainte d'unicité et DRF la rend donc obligatoire.
        """
        data = request.data.copy()
        if not data.get('period_start') or not data.get('period_end'):
            book = ARCEPBook.objects.filter(pk=data.get('book')).first()
            if book is not None:
                start, end = _unsigned_period(book)
            else:
                start = end = timezone.localdate()
            data['period_start'] = data.get('period_start') or start.isoformat()
            data['period_end'] = data.get('period_end') or end.isoformat()

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """Force le unit_chief à l'utilisateur connecté."""
        serializer.save(unit_chief=self.request.user)

    @action(detail=True, methods=['get'], url_path='covered-entries')
    def covered_entries(self, request, pk=None):
        """Liste les entrées couvertes par cette signature."""
        signature = self.get_object()
        entries = signature.book.entries.filter(
            entry_date__gte=signature.period_start,
            entry_date__lte=signature.period_end,
        ).order_by('entry_date')
        serializer = ARCEPEntrySerializer(entries, many=True)
        return Response({'count': entries.count(), 'results': serializer.data})


def _unsigned_period(book):
    """
    Retourne (debut, fin) couvrant les entrees du carnet pas encore signees.

    Une entree est consideree signee si une signature existante englobe sa date.
    Si tout est deja signe, retourne la journee courante (signature a vide).
    """
    signatures = list(book.signatures.values_list('period_start', 'period_end'))

    def already_signed(entry_date):
        return any(start <= entry_date <= end for start, end in signatures)

    dates = [
        d for d in book.entries.values_list('entry_date', flat=True)
        if not already_signed(d)
    ]
    if not dates:
        today = timezone.localdate()
        return today, today
    return min(dates), max(dates)
