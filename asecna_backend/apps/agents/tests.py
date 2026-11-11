"""
Tests unitaires pour l'app agents.

Couvre :
- AgentSkill : création, niveaux
- AgentCertification : dates, organisme
- PerformanceIndicator : unicité agent+année
"""

import datetime
from django.test import TestCase
from django.db import IntegrityError

from apps.accounts.models import User
from apps.agents.models import AgentSkill, AgentCertification, PerformanceIndicator


def make_user(matricule, email, admin=False):
    kwargs = dict(
        matricule=matricule, email=email,
        password='Test123!', first_name='Test', last_name='User',
    )
    if admin:
        return User.objects.create_superuser(**kwargs)
    return User.objects.create_user(**kwargs)


class AgentSkillTest(TestCase):

    def setUp(self):
        self.agent = make_user('ASE-2024-0090', 'skill@asecna.com')
        self.today = datetime.date.today()

    def test_create_skill(self):
        skill = AgentSkill.objects.create(
            agent=self.agent,
            name='Phraséologie OACI',
            level=3,
            acquired_at=self.today,
        )
        self.assertEqual(skill.name, 'Phraséologie OACI')
        self.assertEqual(skill.level, 3)

    def test_skill_default_level(self):
        skill = AgentSkill.objects.create(
            agent=self.agent,
            name='Radar primaire',
        )
        self.assertEqual(skill.level, 1)

    def test_skill_str(self):
        skill = AgentSkill.objects.create(
            agent=self.agent, name='Coordination TWR/APP', level=4
        )
        s = str(skill)
        self.assertIn('Coordination TWR/APP', s)
        self.assertIn('4', s)

    def test_multiple_skills_per_agent(self):
        AgentSkill.objects.create(agent=self.agent, name='Skill A', level=2)
        AgentSkill.objects.create(agent=self.agent, name='Skill B', level=5)
        self.assertEqual(self.agent.skills.count(), 2)


class AgentCertificationTest(TestCase):

    def setUp(self):
        self.agent = make_user('ASE-2024-0091', 'cert@asecna.com')
        self.today = datetime.date.today()

    def test_create_certification(self):
        cert = AgentCertification.objects.create(
            agent=self.agent,
            name='Licence de contrôleur aérien catégorie TWR',
            issuing_body='ASECNA / EAMAC',
            issue_date=self.today,
            expiry_date=self.today + datetime.timedelta(days=365 * 2),
        )
        self.assertEqual(cert.name, 'Licence de contrôleur aérien catégorie TWR')
        self.assertIsNotNone(cert.expiry_date)

    def test_certification_without_expiry(self):
        """Certaines certifications n'expirent jamais."""
        cert = AgentCertification.objects.create(
            agent=self.agent,
            name='Certificat de formation sécurité',
            issue_date=self.today,
        )
        self.assertIsNone(cert.expiry_date)

    def test_certification_str(self):
        cert = AgentCertification.objects.create(
            agent=self.agent,
            name='Cert Test',
            issue_date=self.today,
        )
        s = str(cert)
        self.assertIn('Cert Test', s)


class PerformanceIndicatorTest(TestCase):

    def setUp(self):
        self.agent = make_user('ASE-2024-0092', 'perf@asecna.com')
        self.evaluator = make_user('ASE-2024-0093', 'eval@asecna.com', admin=True)

    def test_create_performance_indicator(self):
        pi = PerformanceIndicator.objects.create(
            agent=self.agent,
            year=2024,
            score=87.50,
            evaluator=self.evaluator,
            comments='Très bonne performance annuelle.',
        )
        self.assertEqual(pi.year, 2024)
        self.assertEqual(float(pi.score), 87.5)

    def test_unique_performance_per_agent_year(self):
        """Un seul indicateur par agent et par année."""
        PerformanceIndicator.objects.create(
            agent=self.agent, year=2023, score=75.00, evaluator=self.evaluator
        )
        with self.assertRaises(IntegrityError):
            PerformanceIndicator.objects.create(
                agent=self.agent, year=2023, score=80.00, evaluator=self.evaluator
            )

    def test_performance_str(self):
        pi = PerformanceIndicator.objects.create(
            agent=self.agent, year=2025, score=92.00, evaluator=self.evaluator
        )
        s = str(pi)
        self.assertIn('2025', s)
        self.assertIn('92', s)
