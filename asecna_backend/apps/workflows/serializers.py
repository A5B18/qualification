"""Serializers pour workflows."""

from rest_framework import serializers

from .models import ApprovalWorkflow


# Modules raccordés au registre. La clé est le `model` du ContentType.
# `label` sert d'intitulé, `route` indique au frontend où mène la décision.
MODULE_LABELS = {
    'report': ('Rapport', '/reports'),
    'mentoringrecord': ('Fiche de mentorat', '/mentoring'),
    'examsession': ("Correction d'examen", '/evaluations/sessions'),
}


class ApprovalWorkflowSerializer(serializers.ModelSerializer):
    """Serializer du workflow d'approbation avec champs lisibles."""

    # Noms lisibles des acteurs.
    # `full_name` est une PROPRIETE du modele User (qui derive de
    # AbstractBaseUser) : appeler get_full_name() comme sur AbstractUser
    # levait une AttributeError -> HTTP 500 sur /workflows/ et /workflows/pending/
    # des que la table contenait une ligne.
    submitted_by_name = serializers.SerializerMethodField()
    approver_name     = serializers.SerializerMethodField()
    unit_chief_name   = serializers.SerializerMethodField()
    content_type_label = serializers.SerializerMethodField()

    # Sans ces champs, une ligne de registre n'indiquait ni ce qui etait soumis,
    # ni sur quel agent : l'ecran d'approbation affichait « 2 workflows en
    # attente » sans pouvoir dire de quoi il s'agissait.
    module = serializers.SerializerMethodField()
    module_label = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()

    class Meta:
        model  = ApprovalWorkflow
        fields = '__all__'
        read_only_fields = (
            'id', 'created_at', 'updated_at',
            'submitted_at', 'approved_at', 'rejected_at',
            'submitted_by_name', 'approver_name', 'unit_chief_name',
            'content_type_label', 'module', 'module_label', 'target',
        )

    def get_submitted_by_name(self, obj) -> str | None:
        if obj.submitted_by:
            return obj.submitted_by.full_name or obj.submitted_by.matricule
        return None

    def get_approver_name(self, obj) -> str | None:
        if obj.approver:
            return obj.approver.full_name or obj.approver.matricule
        return None

    def get_unit_chief_name(self, obj) -> str | None:
        if obj.unit_chief:
            return obj.unit_chief.full_name or obj.unit_chief.matricule
        return None

    def get_content_type_label(self, obj) -> str | None:
        return str(obj.content_type) if obj.content_type_id else None

    def get_module(self, obj) -> str | None:
        """Identifiant technique du module d'origine (ex. `report`)."""
        return obj.content_type.model if obj.content_type_id else None

    def get_module_label(self, obj) -> str | None:
        """Intitulé lisible du type d'objet soumis."""
        if not obj.content_type_id:
            return None
        model = obj.content_type.model
        return MODULE_LABELS.get(model, (obj.content_type.name, None))[0]

    def get_target(self, obj) -> dict | None:
        """
        Objet soumis à décision : de quoi l'afficher et y naviguer.

        `content_object` peut être None si l'objet d'origine a été supprimé
        entre-temps — la ligne de registre, elle, subsiste.
        """
        if not obj.content_type_id:
            return None

        target = obj.content_object
        if target is None:
            return {
                'id': obj.object_id,
                'label': 'Objet supprimé',
                'agent': None,
                'route': None,
                'deleted': True,
            }

        model = obj.content_type.model
        route = MODULE_LABELS.get(model, (None, None))[1]

        # Chaque module nomme son objet différemment : un rapport a un titre,
        # une session d'examen porte celui de l'examen, une fiche de mentorat
        # n'a que ses dates.
        if model == 'report':
            label = target.title
        elif model == 'examsession':
            label = target.exam.title if target.exam_id else "Session d'examen"
        elif model == 'mentoringrecord':
            label = f"Mentorat du {target.start_date}"
        else:
            label = str(target)

        agent = getattr(target, 'agent', None)
        return {
            'id': target.pk,
            'label': label,
            'agent': {
                'id': agent.pk,
                'matricule': agent.matricule,
                'full_name': agent.full_name,
            } if agent is not None else None,
            # Le détail d'une correction a son écran propre ; les autres
            # modules renvoient vers leur liste.
            'route': (f'{route}/{target.pk}' if model == 'examsession' and route
                      else route),
            'deleted': False,
        }
