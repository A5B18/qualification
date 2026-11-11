"""Serializers pour arcep."""

from rest_framework import serializers
from django.db.models import Sum
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
    agent_detail = serializers.SerializerMethodField()
    total_hours = serializers.SerializerMethodField()
    entries_count = serializers.SerializerMethodField()

    class Meta:
        model = ARCEPBook
        fields = '__all__'
        read_only_fields = ('id', 'opened_at')

    def get_agent_detail(self, obj) -> dict | None:
        return _user_brief(obj.agent)

    def get_total_hours(self, obj) -> float:
        """Total des heures de toutes les entrees du carnet."""
        result = obj.entries.aggregate(total=Sum('duration_hours'))
        return float(result.get('total') or 0)

    def get_entries_count(self, obj) -> int:
        return obj.entries.count()


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
