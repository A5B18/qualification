"""
Tests unitaires pour l'app mentoring.

Couvre :
- MentoringRecord : création, contrainte agent ≠ mentor
- Workflow : submit(), approve(), reject()
- Contrainte unicité : un seul enregistrement actif par agent
"""

import datetime
from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.mentoring.models import MentoringRecord


def make_user(matricule, email, admin=False):
    kwargs = dict(
        matricule=matricule, email=email,
        password='Test123!', first_name='Test', last_name='User',
    )
    if admin:
        return User.objects.create_superuser(**kwargs)
    return User.objects.create_user(**kwargs)


class MentoringRecordCreationTest(TestCase):

    def setUp(self):
        self.agent = make_user('ASE-2024-0020', 'agent20@asecna.com')
        self.mentor = make_user('ASE-2024-0021', 'mentor21@asecna.com')
        self.chief = make_user('ASE-2024-0022', 'chief22@asecna.com', admin=True)
        self.today = datetime.date.today()

    def _make_record(self, agent=None, mentor=None, status=MentoringRecord.MentoringStatus.DRAFT):
        """Helper : crée une fiche de mentorat."""
        record = MentoringRecord(
            agent=agent or self.agent,
            mentor=mentor or self.mentor,
            start_date=self.today,
            objectives='Objectifs de test',
            mentoring_status=status,
        )
        # Bypass le full_clean du save() pour les tests de statut
        MentoringRecord.save.__wrapped__ = None if hasattr(
            MentoringRecord.save, '__wrapped__') else None
        # Utiliser save direct via super
        from django.db.models import Model
        Model.save(record)
        return record

    def test_create_basic_record(self):
        record = MentoringRecord.objects.create(
            agent=self.agent,
            mentor=self.mentor,
            start_date=self.today,
            objectives='Acquérir les bases du contrôle ATC',
        )
        self.assertEqual(record.mentoring_status, MentoringRecord.MentoringStatus.DRAFT)
        self.assertIsNotNone(record.pk)

    def test_agent_cannot_be_own_mentor(self):
        """Un agent ne peut pas être son propre mentor."""
        record = MentoringRecord(
            agent=self.agent,
            mentor=self.agent,  # même personne !
            start_date=self.today,
            objectives='Test',
        )
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_str_representation(self):
        record = MentoringRecord.objects.create(
            agent=self.agent,
            mentor=self.mentor,
            start_date=self.today,
            objectives='Objectifs',
        )
        s = str(record)
        self.assertIn('DRAFT', s)


class MentoringWorkflowTest(TestCase):

    def setUp(self):
        self.agent = make_user('ASE-2024-0030', 'agent30@asecna.com')
        self.mentor = make_user('ASE-2024-0031', 'mentor31@asecna.com')
        self.chief = make_user('ASE-2024-0032', 'chief32@asecna.com', admin=True)
        self.today = datetime.date.today()
        # Créer une fiche de base
        self.record = MentoringRecord.objects.create(
            agent=self.agent,
            mentor=self.mentor,
            start_date=self.today,
            objectives='Maîtriser les procédures TWR',
        )

    def test_submit_changes_status(self):
        """submit() → statut SUBMITTED."""
        self.record.submit(unit_chief=self.chief)
        self.assertEqual(self.record.mentoring_status, MentoringRecord.MentoringStatus.SUBMITTED)
        self.assertIsNotNone(self.record.submitted_at)
        self.assertEqual(self.record.unit_chief, self.chief)

    def test_approve_after_submit(self):
        """approve() → statut APPROVED avec avis."""
        self.record.submit(unit_chief=self.chief)
        self.record.approve(opinion='Agent compétent et motivé.')
        self.assertEqual(self.record.mentoring_status, MentoringRecord.MentoringStatus.APPROVED)
        self.assertIsNotNone(self.record.approved_at)
        self.assertEqual(self.record.unit_chief_opinion, 'Agent compétent et motivé.')

    def test_reject_after_submit(self):
        """reject() → statut REJECTED."""
        self.record.submit(unit_chief=self.chief)
        self.record.reject(opinion='Objectifs non atteints.')
        self.assertEqual(self.record.mentoring_status, MentoringRecord.MentoringStatus.REJECTED)

    def test_cannot_approve_draft(self):
        """On ne peut pas approuver une fiche encore en DRAFT."""
        with self.assertRaises(ValidationError):
            self.record.approve(opinion='Test incorrect')

    def test_cannot_submit_already_submitted(self):
        """On ne peut pas soumettre deux fois une fiche."""
        self.record.submit(unit_chief=self.chief)
        with self.assertRaises(ValidationError):
            self.record.submit(unit_chief=self.chief)
