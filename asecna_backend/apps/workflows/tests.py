"""
Tests unitaires pour l'app workflows.

Couvre :
- ApprovalWorkflow : création avec GenericForeignKey
- Transitions de statut DRAFT → SUBMITTED → APPROVED / REJECTED
- __str__
"""

import datetime
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import User
from apps.reports.models import Report
from apps.workflows.models import ApprovalWorkflow


def make_user(matricule, email, admin=False):
    kwargs = dict(
        matricule=matricule, email=email,
        password='Test123!', first_name='Test', last_name='User',
    )
    if admin:
        return User.objects.create_superuser(**kwargs)
    return User.objects.create_user(**kwargs)


class ApprovalWorkflowTest(TestCase):

    def setUp(self):
        self.agent = make_user('ASE-2024-0200', 'wf_agent@asecna.com')
        self.approver = make_user('ASE-2024-0201', 'wf_approver@asecna.com', admin=True)
        self.chief = make_user('ASE-2024-0202', 'wf_chief@asecna.com', admin=True)
        # Objet cible du workflow : un rapport
        self.report = Report.objects.create(
            report_type=Report.ReportType.PROBATION,
            agent=self.agent,
            created_by=self.approver,
            title='Rapport de fin d\'essai',
            content='Contenu du rapport.',
        )
        self.content_type = ContentType.objects.get_for_model(Report)

    def _make_workflow(self):
        return ApprovalWorkflow.objects.create(
            content_type=self.content_type,
            object_id=self.report.pk,
            submitted_by=self.agent,
        )

    def test_create_workflow_draft(self):
        wf = self._make_workflow()
        self.assertEqual(wf.workflow_status, ApprovalWorkflow.WorkflowStatus.DRAFT)
        self.assertIsNotNone(wf.pk)

    def test_workflow_content_object(self):
        """Le GenericForeignKey doit pointer vers le bon rapport."""
        wf = self._make_workflow()
        self.assertEqual(wf.content_object, self.report)

    def test_workflow_submit(self):
        wf = self._make_workflow()
        wf.workflow_status = ApprovalWorkflow.WorkflowStatus.SUBMITTED
        wf.save()
        wf.refresh_from_db()
        self.assertEqual(wf.workflow_status, 'SUBMITTED')

    def test_workflow_approve(self):
        from django.utils import timezone
        wf = self._make_workflow()
        wf.workflow_status = ApprovalWorkflow.WorkflowStatus.APPROVED
        wf.approver = self.approver
        wf.approver_comment = 'Dossier complet, approuvé.'
        wf.approved_at = timezone.now()
        wf.save()
        wf.refresh_from_db()
        self.assertEqual(wf.workflow_status, 'APPROVED')
        self.assertEqual(wf.approver, self.approver)
        self.assertEqual(wf.approver_comment, 'Dossier complet, approuvé.')

    def test_workflow_reject(self):
        from django.utils import timezone
        wf = self._make_workflow()
        wf.workflow_status = ApprovalWorkflow.WorkflowStatus.REJECTED
        wf.approver_comment = 'Documents manquants.'
        wf.rejected_at = timezone.now()
        wf.save()
        wf.refresh_from_db()
        self.assertEqual(wf.workflow_status, 'REJECTED')

    def test_workflow_str(self):
        wf = self._make_workflow()
        s = str(wf)
        self.assertIn('DRAFT', s)

    def test_workflow_with_unit_chief(self):
        wf = self._make_workflow()
        wf.unit_chief = self.chief
        wf.unit_chief_comment = 'Validé par le chef d\'unité.'
        wf.save()
        wf.refresh_from_db()
        self.assertEqual(wf.unit_chief, self.chief)

    def test_multiple_workflows_for_same_object(self):
        """Plusieurs workflows peuvent être attachés au même objet."""
        wf1 = self._make_workflow()
        wf2 = ApprovalWorkflow.objects.create(
            content_type=self.content_type,
            object_id=self.report.pk,
            submitted_by=self.approver,
        )
        self.assertNotEqual(wf1.pk, wf2.pk)
