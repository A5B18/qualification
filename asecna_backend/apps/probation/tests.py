"""
Tests unitaires pour l'app probation.

Couvre :
- ProbationPeriod : création 1ère tentative
- Règle métier : durée 80-100 jours
- Règle métier : impossible de créer 2ème sans 1ère FAILED
- Propriétés is_renewable, is_last_attempt
- Contrainte attempt_number max 2
"""

import datetime
from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.probation.models import ProbationPeriod


def make_user(matricule, email):
    return User.objects.create_user(
        matricule=matricule, email=email,
        password='Test123!', first_name='Test', last_name='User',
    )


class ProbationPeriodCreateTest(TestCase):

    def setUp(self):
        self.agent = make_user('ASE-2024-0100', 'prob@asecna.com')
        self.today = datetime.date.today()
        self.end = self.today + datetime.timedelta(days=91)  # ~3 mois valide

    def test_create_first_attempt(self):
        p = ProbationPeriod.objects.create(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end,
        )
        self.assertEqual(p.attempt_number, 1)
        self.assertEqual(p.probation_status, ProbationPeriod.ProbationStatus.IN_PROGRESS)

    def test_duration_too_short_raises(self):
        """< 80 jours → ValidationError."""
        p = ProbationPeriod(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.today + datetime.timedelta(days=30),  # trop court
        )
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_duration_too_long_raises(self):
        """> 100 jours → ValidationError."""
        p = ProbationPeriod(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.today + datetime.timedelta(days=150),  # trop long
        )
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_cannot_create_second_without_first(self):
        """2ème tentative sans 1ère → ValidationError."""
        p = ProbationPeriod(
            agent=self.agent,
            attempt_number=2,
            start_date=self.today,
            end_date=self.end,
        )
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_cannot_create_second_if_first_passed(self):
        """Si la 1ère est réussie (score OK), la 2ème n'a pas de sens."""
        ProbationPeriod.objects.create(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end,
            probation_status=ProbationPeriod.ProbationStatus.PASSED,
            score=75,  # score valide >= 70
        )
        p = ProbationPeriod(
            agent=self.agent,
            attempt_number=2,
            start_date=self.today + datetime.timedelta(days=100),
            end_date=self.today + datetime.timedelta(days=191),
        )
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_can_create_second_after_first_failed(self):
        """Après un échec de la 1ère tentative, la 2ème est autorisée."""
        first = ProbationPeriod.objects.create(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end,
            probation_status=ProbationPeriod.ProbationStatus.FAILED,
        )
        start2 = self.today + datetime.timedelta(days=30)
        end2 = start2 + datetime.timedelta(days=91)
        second = ProbationPeriod.objects.create(
            agent=self.agent,
            attempt_number=2,
            start_date=start2,
            end_date=end2,
        )
        self.assertEqual(second.attempt_number, 2)


class ProbationPeriodPropertiesTest(TestCase):

    def setUp(self):
        self.agent = make_user('ASE-2024-0101', 'prop@asecna.com')
        self.today = datetime.date.today()
        self.end = self.today + datetime.timedelta(days=91)

    def test_is_renewable_true(self):
        """1ère tentative échouée sans 2ème → est renouvelable."""
        p = ProbationPeriod.objects.create(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end,
            probation_status=ProbationPeriod.ProbationStatus.FAILED,
        )
        self.assertTrue(p.is_renewable)

    def test_is_renewable_false_after_passed(self):
        """1ère réussie (score OK) → pas renouvelable."""
        p = ProbationPeriod.objects.create(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end,
            probation_status=ProbationPeriod.ProbationStatus.PASSED,
            score=80,  # score valide >= 70
        )
        self.assertFalse(p.is_renewable)

    def test_is_last_attempt_for_second(self):
        first = ProbationPeriod.objects.create(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end,
            probation_status=ProbationPeriod.ProbationStatus.FAILED,
        )
        start2 = self.today + datetime.timedelta(days=30)
        second = ProbationPeriod.objects.create(
            agent=self.agent,
            attempt_number=2,
            start_date=start2,
            end_date=start2 + datetime.timedelta(days=91),
        )
        self.assertTrue(second.is_last_attempt)
        self.assertFalse(first.is_last_attempt)

    def test_str_representation(self):
        p = ProbationPeriod.objects.create(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end,
        )
        s = str(p)
        self.assertIn('#1', s)
        self.assertIn('IN_PROGRESS', s)


class ProbationScoreRulesTest(TestCase):
    """Tests des nouvelles règles métier : score 70/100 et évaluation J-14."""

    def setUp(self):
        self.agent = make_user('ASE-2024-0102', 'score@asecna.com')
        self.today = datetime.date.today()
        self.end = self.today + datetime.timedelta(days=91)

    def test_passed_requires_score(self):
        """Statut PASSED sans score → ValidationError."""
        p = ProbationPeriod(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end,
            probation_status=ProbationPeriod.ProbationStatus.PASSED,
            score=None,
        )
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_passed_requires_score_gte_70(self):
        """Score < 70 avec statut PASSED → ValidationError."""
        p = ProbationPeriod(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end,
            probation_status=ProbationPeriod.ProbationStatus.PASSED,
            score=65,
        )
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_score_70_is_valid(self):
        """Score exact 70 → valide (seuil inclus)."""
        p = ProbationPeriod.objects.create(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end,
            probation_status=ProbationPeriod.ProbationStatus.PASSED,
            score=70,
        )
        self.assertTrue(p.score_passed)

    def test_score_passed_property(self):
        """score_passed retourne True/False correctement."""
        p = ProbationPeriod.objects.create(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end,
            score=85,
        )
        self.assertTrue(p.score_passed)

    def test_evaluation_due_date_is_j14(self):
        """evaluation_due_date = end_date - 14 jours."""
        p = ProbationPeriod(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end,
        )
        expected = self.end - datetime.timedelta(days=14)
        self.assertEqual(p.evaluation_due_date, expected)

    def test_evaluation_is_due_when_in_range(self):
        """evaluation_is_due = True quand on est à J-14 ou moins."""
        # Créer une période dont la fin est dans 13 jours (donc J-14 dépassé)
        p = ProbationPeriod(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today - datetime.timedelta(days=80),
            end_date=self.today + datetime.timedelta(days=13),
            probation_status=ProbationPeriod.ProbationStatus.IN_PROGRESS,
        )
        self.assertTrue(p.evaluation_is_due)
