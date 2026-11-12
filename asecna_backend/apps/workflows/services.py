"""
Raccordement des modules métier au registre d'approbation.

Pourquoi ce module existe
-------------------------
`ApprovalWorkflow` annonçait « Utilisé par : corrections d'examen, rapports,
fiches mentorat », mais rien ne l'alimentait en dehors de `seed_demo` : chaque
module portait son propre champ de statut et le registre restait vide. L'écran
« workflows en attente » de l'approbateur ne montrait donc que des lignes
fabriquées par le jeu de démonstration.

Le partage des rôles retenu
---------------------------
Chaque module **garde** sa machine à états : `report_status`,
`mentoring_status`, `session_status` restent la source de vérité de leur propre
cycle. Les réécrire pour qu'ils dépendent d'`ApprovalWorkflow` reviendrait à
refondre trois modules qui fonctionnent et sont couverts par des tests.

`ApprovalWorkflow` devient le **registre transversal** : une ligne par objet
soumis à décision, quel que soit son module. C'est ce qui permet à un
approbateur de voir en un seul endroit tout ce qui l'attend — un rapport, une
fiche de mentorat et une correction d'examen dans la même liste — et de retracer
qui a décidé quoi, et quand.

Invariant
---------
Un objet métier n'a qu'une ligne de registre (contrainte d'unicité sur
`content_type` + `object_id`). Les fonctions ci-dessous sont donc idempotentes :
rejouer une soumission met la ligne à jour, elle n'en crée pas une seconde.

Les écritures doivent être appelées dans la même transaction que la transition
métier qu'elles enregistrent — sinon le registre peut diverger de l'état réel.
Les vues concernées ouvrent un `transaction.atomic()` autour des deux.
"""

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import ApprovalWorkflow


def _ledger_for(obj):
    """Retourne (ou crée) la ligne de registre de cet objet métier."""
    content_type = ContentType.objects.get_for_model(obj.__class__)
    workflow, _created = ApprovalWorkflow.objects.get_or_create(
        content_type=content_type,
        object_id=obj.pk,
    )
    return workflow


def record_submission(obj, submitted_by, unit_chief=None, approver=None):
    """
    Enregistre qu'un objet a été soumis à décision.

    Appelée à la soumission d'un rapport, d'une fiche de mentorat ou d'une
    correction d'examen. `unit_chief` / `approver` restent facultatifs : tous
    les modules ne désignent pas leur décideur à l'avance.
    """
    workflow = _ledger_for(obj)
    workflow.workflow_status = ApprovalWorkflow.WorkflowStatus.SUBMITTED
    workflow.submitted_by = submitted_by
    workflow.submitted_at = timezone.now()
    if unit_chief is not None:
        workflow.unit_chief = unit_chief
    if approver is not None:
        workflow.approver = approver
    # Une resoumission après rejet repart d'une ardoise propre.
    workflow.approved_at = None
    workflow.rejected_at = None
    workflow.save(update_fields=[
        'workflow_status', 'submitted_by', 'submitted_at',
        'unit_chief', 'approver', 'approved_at', 'rejected_at', 'updated_at',
    ])
    return workflow


def record_approval(obj, approver, comment='', as_unit_chief=False):
    """
    Enregistre une décision favorable.

    `as_unit_chief` range le commentaire dans `unit_chief_comment` plutôt que
    dans `approver_comment` : les deux avis coexistent sur le modèle, et une
    fiche de mentorat est validée par le chef d'unité là où un rapport l'est par
    l'approbateur.
    """
    workflow = _ledger_for(obj)
    workflow.workflow_status = ApprovalWorkflow.WorkflowStatus.APPROVED
    workflow.approved_at = timezone.now()
    workflow.rejected_at = None
    if as_unit_chief:
        workflow.unit_chief = approver
        if comment:
            workflow.unit_chief_comment = comment
    else:
        workflow.approver = approver
        if comment:
            workflow.approver_comment = comment
    workflow.save(update_fields=[
        'workflow_status', 'approved_at', 'rejected_at',
        'approver', 'unit_chief', 'approver_comment', 'unit_chief_comment',
        'updated_at',
    ])
    return workflow


def record_rejection(obj, approver, reason='', as_unit_chief=False):
    """Enregistre une décision défavorable et son motif."""
    workflow = _ledger_for(obj)
    workflow.workflow_status = ApprovalWorkflow.WorkflowStatus.REJECTED
    workflow.rejected_at = timezone.now()
    workflow.approved_at = None
    if as_unit_chief:
        workflow.unit_chief = approver
        if reason:
            workflow.unit_chief_comment = reason
    else:
        workflow.approver = approver
        if reason:
            workflow.approver_comment = reason
    workflow.save(update_fields=[
        'workflow_status', 'rejected_at', 'approved_at',
        'approver', 'unit_chief', 'approver_comment', 'unit_chief_comment',
        'updated_at',
    ])
    return workflow


def discard(obj):
    """
    Retire la ligne de registre d'un objet qui n'est plus soumis à décision
    (retour en brouillon, suppression). Sans effet s'il n'y en a pas.
    """
    content_type = ContentType.objects.get_for_model(obj.__class__)
    ApprovalWorkflow.objects.filter(
        content_type=content_type, object_id=obj.pk,
    ).delete()
