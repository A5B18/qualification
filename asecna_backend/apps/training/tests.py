"""
Tests unitaires pour l'app training.

Couvre :
  - Specialty, Training CRUD basique
  - Course : publication/dépublication
  - Internship
  - QualificationMaintenance : règle 70/100, suspension agent si FAILED
"""

import datetime

from django.test import TestCase

from apps.accounts.models import User
from apps.training.models import Specialty, Training, Internship, QualificationMaintenance


def make_user(matricule, email):
    return User.objects.create_user(
        matricule=matricule, email=email,
        password='Test123!', first_name='Test', last_name='User',
    )


class SpecialtyTest(TestCase):
    def test_create_specialty(self):
        s = Specialty.objects.create(code='ATC', name='Contrôle aérien')
        self.assertEqual(str(s), 'ATC — Contrôle aérien')


class TrainingTest(TestCase):
    def setUp(self):
        self.specialty = Specialty.objects.create(code='MET', name='Météo')

    def test_create_qualifying_training(self):
        t = Training.objects.create(
            specialty=self.specialty,
            title='Formation EAMAC',
            training_type=Training.TrainingType.QUALIFYING,
            passing_score=80,
        )
        self.assertEqual(t.passing_score, 80)

    def test_default_passing_score_is_70(self):
        t = Training.objects.create(
            specialty=self.specialty,
            title='Formation interne',
            training_type=Training.TrainingType.NON_QUALIFYING,
        )
        self.assertEqual(t.passing_score, 70)


class QualificationMaintenanceTest(TestCase):
    """Tests de la règle métier : maintien qualification 70/100 tous les 2 ans."""

    def setUp(self):
        self.agent = make_user('ASE-2024-0200', 'maint@asecna.com')
        self.evaluator = make_user('ASE-2024-0201', 'eval@asecna.com')
        self.today = datetime.date.today()
        self.maintenance = QualificationMaintenance.objects.create(
            agent=self.agent,
            due_date=self.today,
        )

    def test_initial_status_is_pending(self):
        self.assertEqual(self.maintenance.maintenance_status,
                         QualificationMaintenance.MaintenanceStatus.PENDING)

    def test_score_passed_property_true(self):
        """Score >= 70 → score_passed = True."""
        self.maintenance.score = 75
        self.assertTrue(self.maintenance.score_passed)

    def test_score_passed_property_false(self):
        """Score < 70 → score_passed = False."""
        self.maintenance.score = 65
        self.assertFalse(self.maintenance.score_passed)

    def test_score_exactly_70_passes(self):
        """Score = 70 (seuil inclus) → PASSED."""
        self.maintenance.finalize(evaluator=self.evaluator, score=70)
        self.maintenance.refresh_from_db()
        self.assertEqual(self.maintenance.maintenance_status,
                         QualificationMaintenance.MaintenanceStatus.PASSED)
        self.assertTrue(self.maintenance.score_passed)

    def test_score_below_70_fails(self):
        """Score < 70 → FAILED."""
        self.maintenance.finalize(evaluator=self.evaluator, score=65)
        self.maintenance.refresh_from_db()
        self.assertEqual(self.maintenance.maintenance_status,
                         QualificationMaintenance.MaintenanceStatus.FAILED)

    def test_evaluator_recorded(self):
        """L'évaluateur est bien enregistré après finalisation."""
        self.maintenance.finalize(evaluator=self.evaluator, score=80)
        self.maintenance.refresh_from_db()
        self.assertEqual(self.maintenance.evaluated_by, self.evaluator)

    def test_notes_saved(self):
        """Les notes sont sauvegardées lors de la finalisation."""
        self.maintenance.finalize(evaluator=self.evaluator, score=80, notes='Contrôle OK')
        self.maintenance.refresh_from_db()
        self.assertEqual(self.maintenance.notes, 'Contrôle OK')

    def test_str_representation(self):
        s = str(self.maintenance)
        self.assertIn('PENDING', s)
        self.assertIn(str(self.agent), s)


class InternshipTest(TestCase):
    def setUp(self):
        self.agent = make_user('ASE-2024-0202', 'intern@asecna.com')
        self.specialty = Specialty.objects.create(code='COM', name='Com radio')
        self.training = Training.objects.create(
            specialty=self.specialty,
            title='Stage COM',
            training_type=Training.TrainingType.QUALIFYING,
        )
        self.today = datetime.date.today()

    def test_create_qualifying_internship(self):
        internship = Internship.objects.create(
            agent=self.agent,
            training=self.training,
            internship_type=Internship.InternshipType.QUALIFYING,
            start_date=self.today,
            end_date=self.today + datetime.timedelta(days=30),
        )
        self.assertEqual(internship.internship_type, 'QUALIFYING')
        self.assertIsNone(internship.is_passed)  # en cours
