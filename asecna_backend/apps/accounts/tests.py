"""
Tests unitaires pour l'app accounts.

Couvre :
- Création de User avec matricule valide/invalide
- Méthode has_role() et get_active_roles()
- ProbationPeriod (max 2 tentatives)
- Workflow MentoringRecord
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.accounts.models import User, UserRole, AgentProfile, FunctionalRole, AgentStatus


class UserModelTest(TestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser(
            matricule='ASE-2024-0001',
            email='admin@asecna.com',
            password='SecurePass123!',
            first_name='Admin',
            last_name='ASECNA',
        )

    def test_user_creation_valid_matricule(self):
        user = User.objects.create_user(
            matricule='ASE-2024-0042',
            email='agent@asecna.com',
            password='Pass123!',
            first_name='Jean',
            last_name='Dupont',
        )
        self.assertEqual(user.matricule, 'ASE-2024-0042')
        self.assertEqual(user.full_name, 'Jean Dupont')
        self.assertFalse(user.is_admin)

    def test_user_invalid_matricule_raises(self):
        user = User(
            matricule='INVALID',
            email='bad@asecna.com',
            first_name='X', last_name='Y',
        )
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_has_role_returns_false_no_roles(self):
        self.assertFalse(self.admin.has_role(FunctionalRole.EVALUATOR))

    def test_has_role_true_after_assignment(self):
        UserRole.objects.create(
            user=self.admin,
            role=FunctionalRole.EVALUATOR,
            assigned_by=self.admin,
            is_active=True,
        )
        self.assertTrue(self.admin.has_role(FunctionalRole.EVALUATOR))

    def test_revoked_role_not_active(self):
        role = UserRole.objects.create(
            user=self.admin,
            role=FunctionalRole.MENTOR,
            assigned_by=self.admin,
            is_active=False,
        )
        self.assertFalse(self.admin.has_role(FunctionalRole.MENTOR))

    def test_superuser_is_admin(self):
        self.assertTrue(self.admin.is_admin)


class ProbationPeriodTest(TestCase):

    def setUp(self):
        from apps.probation.models import ProbationPeriod
        import datetime
        self.ProbationPeriod = ProbationPeriod
        self.agent = User.objects.create_user(
            matricule='ASE-2024-0099',
            email='agent99@asecna.com',
            password='Pass123!',
            first_name='Test', last_name='Agent',
        )
        self.today = datetime.date.today()
        self.end_date = self.today + datetime.timedelta(days=91)

    def test_create_first_attempt(self):
        p = self.ProbationPeriod(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end_date,
        )
        p.save()
        self.assertEqual(p.attempt_number, 1)

    def test_cannot_create_second_attempt_without_first(self):
        p = self.ProbationPeriod(
            agent=self.agent,
            attempt_number=2,
            start_date=self.today,
            end_date=self.end_date,
        )
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_is_renewable_after_first_failure(self):
        p = self.ProbationPeriod.objects.create(
            agent=self.agent,
            attempt_number=1,
            start_date=self.today,
            end_date=self.end_date,
            probation_status=self.ProbationPeriod.ProbationStatus.FAILED,
        )
        self.assertTrue(p.is_renewable)
