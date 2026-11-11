"""
Tests unitaires pour l'app reports.

Couvre :
- Report : création des 3 types (PROBATION, MENTORING, ASSESSMENT)
- Statut initial DRAFT
- __str__ correct
"""

from django.test import TestCase
from apps.accounts.models import User
from apps.reports.models import Report


def make_user(matricule, email, admin=False):
    kwargs = dict(
        matricule=matricule, email=email,
        password='Test123!', first_name='Test', last_name='User',
    )
    if admin:
        return User.objects.create_superuser(**kwargs)
    return User.objects.create_user(**kwargs)


class ReportCreationTest(TestCase):

    def setUp(self):
        self.agent = make_user('ASE-2024-0040', 'agent40@asecna.com')
        self.author = make_user('ASE-2024-0041', 'author41@asecna.com', admin=True)

    def _create_report(self, report_type):
        return Report.objects.create(
            report_type=report_type,
            agent=self.agent,
            created_by=self.author,
            title=f'Rapport {report_type} — Test Agent',
            content='Corps du rapport de test.',
        )

    def test_create_probation_report(self):
        r = self._create_report(Report.ReportType.PROBATION)
        self.assertEqual(r.report_type, 'PROBATION')
        self.assertEqual(r.report_status, Report.ReportStatus.DRAFT)

    def test_create_mentoring_report(self):
        r = self._create_report(Report.ReportType.MENTORING)
        self.assertEqual(r.report_type, 'MENTORING')
        self.assertEqual(r.report_status, Report.ReportStatus.DRAFT)

    def test_create_assessment_report(self):
        r = self._create_report(Report.ReportType.ASSESSMENT)
        self.assertEqual(r.report_type, 'ASSESSMENT')
        self.assertEqual(r.report_status, Report.ReportStatus.DRAFT)

    def test_report_str(self):
        r = self._create_report(Report.ReportType.PROBATION)
        s = str(r)
        self.assertIn('PROBATION', s)
        self.assertIn('Test Agent', s)

    def test_default_status_is_draft(self):
        r = self._create_report(Report.ReportType.ASSESSMENT)
        self.assertEqual(r.report_status, Report.ReportStatus.DRAFT)

    def test_report_linked_to_agent(self):
        r = self._create_report(Report.ReportType.MENTORING)
        self.assertEqual(r.agent, self.agent)
        self.assertEqual(r.created_by, self.author)


class ReportStatusTransitionTest(TestCase):
    """Vérifie que les transitions de statut fonctionnent via mise à jour directe."""

    def setUp(self):
        self.agent = make_user('ASE-2024-0050', 'agent50@asecna.com')
        self.author = make_user('ASE-2024-0051', 'author51@asecna.com', admin=True)
        self.report = Report.objects.create(
            report_type=Report.ReportType.PROBATION,
            agent=self.agent,
            created_by=self.author,
            title='Rapport final essai',
            content='Contenu.',
        )

    def test_submit_report(self):
        self.report.report_status = Report.ReportStatus.SUBMITTED
        self.report.save()
        self.report.refresh_from_db()
        self.assertEqual(self.report.report_status, 'SUBMITTED')

    def test_approve_report(self):
        self.report.report_status = Report.ReportStatus.APPROVED
        self.report.save()
        self.report.refresh_from_db()
        self.assertEqual(self.report.report_status, 'APPROVED')

    def test_reject_report(self):
        self.report.report_status = Report.ReportStatus.REJECTED
        self.report.save()
        self.report.refresh_from_db()
        self.assertEqual(self.report.report_status, 'REJECTED')
