"""Serializers pour arcep."""

import datetime

from rest_framework import serializers
from django.db.models import Sum
from django.utils import timezone

from .identity import agent_identity, agent_qualifications, qualifications_summary
from .models import ARCEPBook, ARCEPEntry, ARCEPSignature


def _user_brief(user):
    """Representation courte d'un utilisateur pour les champs `*_detail`."""
    if not user:
        return None
    return {
        'id': user.id,
        'matricule': user.matricule,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.full_name,
    }


class ARCEPBookSerializer(serializers.ModelSerializer):
    """
    Carnet ARCEP complet : en-tete d'identite, qualifications, releve d'heures.

    Le carnet ne portait que l'identifiant de son titulaire. Or c'est un
    document opposable : a la relecture, un releve d'activites sans le nom, la
    profession, l'unite et l'etat des qualifications de l'agent n'est pas
    exploitable. Trois blocs sont donc joints ici, comme sur la premiere page
    du carnet papier :

      - `agent_identity`         → nom, prenom, matricule, profession, unite,
                                   statut de parcours, dates cles, anciennete
      - `qualifications`         → certifications, controles biennaux et
                                   stages qualifiants, echeance la plus
                                   urgente en tete
      - `qualifications_summary` → compteurs, prochaine echeance, niveau
                                   d'alerte

    Les requetes correspondantes sont prechargees par la vue
    (`ARCEPBookViewSet.get_queryset`) : sans cela la liste des carnets
    declenchait une dizaine de requetes par ligne.
    """

    agent_detail = serializers.SerializerMethodField()
    agent_identity = serializers.SerializerMethodField()
    qualifications = serializers.SerializerMethodField()
    qualifications_summary = serializers.SerializerMethodField()
    total_hours = serializers.SerializerMethodField()
    entries_count = serializers.SerializerMethodField()
    signatures_count = serializers.SerializerMethodField()
    last_signed_on = serializers.SerializerMethodField()
    pending_signature_count = serializers.SerializerMethodField()

    class Meta:
        model = ARCEPBook
        fields = '__all__'
        read_only_fields = ('id', 'opened_at')

    # ── Contexte partage ─────────────────────────────────────────────────────

    def _today(self):
        """Date du jour, calculee une fois par serialisation de la liste."""
        if 'arcep_today' not in self.context:
            self.context['arcep_today'] = timezone.localdate()
        return self.context['arcep_today']

    def _qualifications(self, obj) -> list:
        """Memorise le calcul : le resume et la liste le partagent."""
        cache = self.context.setdefault('arcep_qualifications', {})
        if obj.pk not in cache:
            cache[obj.pk] = agent_qualifications(obj.agent, today=self._today())
        return cache[obj.pk]

    # ── Identite et qualifications ───────────────────────────────────────────

    def get_agent_detail(self, obj) -> dict | None:
        return _user_brief(obj.agent)

    def get_agent_identity(self, obj) -> dict | None:
        return agent_identity(obj.agent, today=self._today())

    def get_qualifications(self, obj) -> list:
        return self._qualifications(obj)

    def get_qualifications_summary(self, obj) -> dict:
        return qualifications_summary(self._qualifications(obj), today=self._today())

    # ── Releve d'activites ───────────────────────────────────────────────────

    def get_total_hours(self, obj) -> float:
        """
        Total des heures de toutes les entrees du carnet.

        On teste la presence de l'annotation, pas sa valeur : `Sum` vaut None
        pour un carnet vide, et se rabattre sur ce None relancait une requete
        d'agregation par carnet sans entree — dix requetes pour dix carnets
        neufs.
        """
        if hasattr(obj, 'total_hours_agg'):
            return float(obj.total_hours_agg or 0)
        total = obj.entries.aggregate(total=Sum('duration_hours')).get('total')
        return float(total or 0)

    def get_entries_count(self, obj) -> int:
        if hasattr(obj, 'entries_count_agg'):
            return int(obj.entries_count_agg or 0)
        return len(obj.entries.all())

    def get_signatures_count(self, obj) -> int:
        return len(obj.signatures.all())

    def get_last_signed_on(self, obj) -> datetime.date | None:
        """
        Fin de la derniere periode visee par le chef d'unite.

        Le type de retour est annote : sans lui, drf-spectacular ne sait pas
        resoudre le champ et le documente en `string` par defaut, avec un
        avertissement a la generation du schema.
        """
        periods = [sig.period_end for sig in obj.signatures.all()]
        return max(periods) if periods else None

    def get_pending_signature_count(self, obj) -> int:
        """
        Entrees qui attendent encore le visa du chef d'unite.

        Information capitale du carnet : une entree non signee n'est pas
        officielle (cf. `ARCEPEntry.is_validated`). Le calcul se fait en
        memoire sur les entrees et signatures prechargees, pour ne pas lancer
        une requete par entree.
        """
        periods = [(sig.period_start, sig.period_end) for sig in obj.signatures.all()]
        return sum(
            1 for entry in obj.entries.all()
            if not any(start <= entry.entry_date <= end for start, end in periods)
        )


class ARCEPEntrySerializer(serializers.ModelSerializer):
    # `is_validated` est une propriete du modele (l'entree est-elle couverte
    # par une signature du chef d'unite ?) : il faut la declarer explicitement
    # pour qu'elle apparaisse dans la reponse.
    is_validated = serializers.BooleanField(read_only=True)
    agent_detail = serializers.SerializerMethodField()

    class Meta:
        model = ARCEPEntry
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_agent_detail(self, obj) -> dict | None:
        return _user_brief(obj.book.agent if obj.book_id else None)


class ARCEPSignatureSerializer(serializers.ModelSerializer):
    # Le signataire est stocke dans `unit_chief` (et non `signed_by`).
    unit_chief_detail = serializers.SerializerMethodField()
    # Conserve pour compatibilite avec le frontend qui lit `signed_by_detail`.
    signed_by_detail = serializers.SerializerMethodField()
    agent_detail = serializers.SerializerMethodField()
    covered_entries_count = serializers.SerializerMethodField()

    class Meta:
        model = ARCEPSignature
        fields = '__all__'
        # `unit_chief` est force a l'utilisateur connecte par la vue.
        # La periode est optionnelle : la vue la calcule si elle est absente.
        read_only_fields = ('id', 'signed_at', 'updated_at', 'unit_chief')
        # `period_start` / `period_end` restent obligatoires au niveau du
        # serializer : ils participent a la contrainte d'unicite
        # `unique_arcep_signature_period`, et DRF impose que les champs d'un
        # UniqueTogetherValidator soient requis. C'est donc la vue qui remplit
        # la periode par defaut AVANT la validation (voir ARCEPSignatureViewSet.create).

    def get_unit_chief_detail(self, obj) -> dict | None:
        return _user_brief(obj.unit_chief)

    def get_signed_by_detail(self, obj) -> dict | None:
        return _user_brief(obj.unit_chief)

    def get_agent_detail(self, obj) -> dict | None:
        return _user_brief(obj.book.agent if obj.book_id else None)

    def get_covered_entries_count(self, obj) -> int:
        """Nombre d'entrees couvertes par la periode signee."""
        return obj.entries_count

    def validate(self, attrs):
        start = attrs.get('period_start')
        end = attrs.get('period_end')
        if start and end and start > end:
            raise serializers.ValidationError(
                {'period_end': "La fin de periode doit etre posterieure au debut."}
            )
        return attrs
