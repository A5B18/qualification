"""
Tests unitaires pour l'app audit.

Couvre :
- AuditLog : création manuelle d'une entrée
- LoginHistory : enregistrement succès et échec
- Ordering (le plus récent en premier)
"""

from django.test import TestCase
from apps.accounts.models import User
from apps.audit.models import AuditLog, LoginHistory


def make_user(matricule, email, admin=False):
    kwargs = dict(
        matricule=matricule, email=email,
        password='Test123!', first_name='Test', last_name='User',
    )
    if admin:
        return User.objects.create_superuser(**kwargs)
    return User.objects.create_user(**kwargs)


class AuditLogModelTest(TestCase):

    def setUp(self):
        self.user = make_user('ASE-2024-0070', 'audit@asecna.com', admin=True)

    def test_create_audit_log(self):
        log = AuditLog.objects.create(
            user=self.user,
            action='POST',
            endpoint='/api/v1/agents/',
            status_code=201,
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0',
            request_data={'matricule': 'ASE-2024-0099'},
        )
        self.assertEqual(log.action, 'POST')
        self.assertEqual(log.status_code, 201)
        self.assertEqual(log.user, self.user)

    def test_audit_log_str(self):
        log = AuditLog.objects.create(
            user=self.user,
            action='DELETE',
            endpoint='/api/v1/units/1/',
            status_code=204,
            ip_address='127.0.0.1',
        )
        s = str(log)
        self.assertIn('DELETE', s)
        self.assertIn('/api/v1/units/1/', s)
        self.assertIn('204', s)

    def test_audit_log_without_user(self):
        """Un log peut exister sans user (SET_NULL si user supprimé)."""
        log = AuditLog.objects.create(
            user=None,
            action='GET',
            endpoint='/api/v1/public/',
            status_code=200,
        )
        self.assertIsNone(log.user)

    def test_audit_log_ordering(self):
        """Les logs sont ordonnés du plus récent au plus ancien."""
        AuditLog.objects.create(user=self.user, action='POST',
                                 endpoint='/a/', status_code=201)
        AuditLog.objects.create(user=self.user, action='PUT',
                                 endpoint='/b/', status_code=200)
        logs = AuditLog.objects.all()
        # Le plus récent est en premier
        self.assertEqual(logs[0].action, 'PUT')


class LoginHistoryTest(TestCase):

    def setUp(self):
        self.user = make_user('ASE-2024-0080', 'login@asecna.com')

    def test_login_success(self):
        h = LoginHistory.objects.create(
            user=self.user,
            matricule_attempted='ASE-2024-0080',
            result=LoginHistory.LoginResult.SUCCESS,
            ip_address='192.168.1.1',
        )
        self.assertEqual(h.result, 'SUCCESS')
        self.assertEqual(h.user, self.user)

    def test_login_failure_no_user(self):
        """Un échec de connexion peut ne pas avoir de user associé."""
        h = LoginHistory.objects.create(
            user=None,
            matricule_attempted='ASE-0000-XXXX',
            result=LoginHistory.LoginResult.FAILURE,
            ip_address='10.0.0.1',
        )
        self.assertEqual(h.result, 'FAILURE')
        self.assertIsNone(h.user)

    def test_login_history_str(self):
        h = LoginHistory.objects.create(
            matricule_attempted='ASE-2024-0080',
            result=LoginHistory.LoginResult.SUCCESS,
        )
        s = str(h)
        self.assertIn('SUCCESS', s)
        self.assertIn('ASE-2024-0080', s)
