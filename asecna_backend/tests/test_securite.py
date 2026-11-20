"""
Contrôles de sécurité et d'habilitation — tests de non-régression.

Chaque test correspond à une faille constatée pendant l'audit. Ils échouent
tous sur le code d'avant : ils décrivent ce que le serveur doit refuser, pas
seulement ce qu'il doit accepter.
"""

import datetime
from unittest.mock import patch

from django.core.cache import cache
from rest_framework.test import APIClient

from core.throttling import LoginRateThrottle

from apps.agents.models import AgentCertification
from apps.audit.models import AuditLog
from apps.mentoring.models import MentoringRecord
from apps.reports.models import Report

from tests.test_api_contract import ApiContractTestCase, PASSWORD, make_user


class WorkflowNeContournePasTest(ApiContractTestCase):
    """
    Les statuts de workflow ne se changent que par les actions dédiées.

    Ils étaient ouverts en écriture par les serializers (`fields = '__all__'`
    sans les lister en lecture seule) : un simple PATCH suffisait à sauter
    l'approbation, les contrôles de rôle et l'inscription au registre.
    """

    def test_un_agent_ne_fait_pas_approuver_son_propre_rapport(self):
        reponse = self.client_for(self.agent).patch(
            f'/api/v1/reports/{self.report.id}/',
            {'report_status': 'APPROVED'}, format='json',
        )
        # L'agent n'est de toute façon pas habilité à écrire un rapport.
        self.assertEqual(reponse.status_code, 403, reponse.content)
        self.report.refresh_from_db()
        self.assertEqual(self.report.report_status, Report.ReportStatus.DRAFT)

    def test_meme_un_chef_passe_par_l_action_d_approbation(self):
        """Le champ est ignoré : seule `approve/` fait la transition."""
        reponse = self.client_for(self.chief).patch(
            f'/api/v1/reports/{self.report.id}/',
            {'report_status': 'APPROVED', 'content': 'Contenu révisé'},
            format='json',
        )
        self.assertEqual(reponse.status_code, 200, reponse.content)
        self.report.refresh_from_db()
        self.assertEqual(self.report.report_status, Report.ReportStatus.DRAFT)
        self.assertEqual(self.report.content, 'Contenu révisé')

    def test_un_mentor_ne_fait_pas_approuver_sa_propre_fiche(self):
        reponse = self.client_for(self.mentor).patch(
            f'/api/v1/mentoring/{self.mentoring.id}/',
            {'mentoring_status': 'APPROVED'}, format='json',
        )
        self.assertEqual(reponse.status_code, 200, reponse.content)
        self.mentoring.refresh_from_db()
        self.assertEqual(
            self.mentoring.mentoring_status,
            MentoringRecord.MentoringStatus.DRAFT,
        )

    def test_le_score_d_une_periode_d_essai_passe_par_finalize(self):
        """
        `finalize` applique le seuil de 70/100 et fait évoluer le parcours de
        l'agent. Un PATCH direct enregistrait un résultat sans rien de tout
        cela.
        """
        reponse = self.client_for(self.chief).patch(
            f'/api/v1/probation/{self.probation.id}/',
            {'probation_status': 'PASSED', 'score': 95}, format='json',
        )
        self.assertEqual(reponse.status_code, 200, reponse.content)
        self.probation.refresh_from_db()
        self.assertEqual(self.probation.probation_status, 'IN_PROGRESS')
        self.assertIsNone(self.probation.score)


class RedactionDesRapportsTest(ApiContractTestCase):
    """La rédaction d'un rapport est réservée aux encadrants."""

    PAYLOAD = {
        'report_type': 'ASSESSMENT', 'title': 'Bilan', 'content': 'Texte',
    }

    def test_un_agent_ne_cree_pas_de_rapport(self):
        """
        L'interface ne proposait le bouton qu'aux encadrants, mais l'API
        acceptait n'importe quel compte authentifié : la règle n'existait que
        dans le navigateur.
        """
        reponse = self.client_for(self.agent).post(
            '/api/v1/reports/', {**self.PAYLOAD, 'agent': self.agent.id}, format='json',
        )
        self.assertEqual(reponse.status_code, 403, reponse.content)

    def test_un_chef_d_unite_cree_un_rapport(self):
        reponse = self.client_for(self.chief).post(
            '/api/v1/reports/', {**self.PAYLOAD, 'agent': self.agent.id}, format='json',
        )
        self.assertEqual(reponse.status_code, 201, reponse.content)

    def test_un_rapport_soumis_n_est_plus_modifiable(self):
        chef = self.client_for(self.chief)
        self.assertEqual(
            chef.post(f'/api/v1/reports/{self.report.id}/submit/').status_code, 200,
        )
        reponse = chef.patch(
            f'/api/v1/reports/{self.report.id}/', {'content': 'Réécrit'}, format='json',
        )
        self.assertEqual(reponse.status_code, 403, reponse.content)


class CloisonnementDuDossierAgentTest(ApiContractTestCase):
    """Un dossier d'agent ne se modifie que par son titulaire ou l'admin."""

    def setUp(self):
        self.certification = AgentCertification.objects.create(
            agent=self.agent, name='Licence ATC',
            issue_date=datetime.date(2024, 1, 10),
        )

    def test_un_chef_ne_supprime_pas_la_certification_d_un_agent(self):
        """
        La suppression n'était pas contrôlée alors que la modification
        l'était : un chef d'unité, qui voit toutes les certifications,
        pouvait en effacer une sans pouvoir la corriger.
        """
        reponse = self.client_for(self.chief).delete(
            f'/api/v1/agents/certifications/{self.certification.id}/'
        )
        self.assertEqual(reponse.status_code, 403, reponse.content)
        self.assertTrue(
            AgentCertification.objects.filter(pk=self.certification.pk).exists()
        )

    def test_le_titulaire_supprime_la_sienne(self):
        reponse = self.client_for(self.agent).delete(
            f'/api/v1/agents/certifications/{self.certification.id}/'
        )
        self.assertEqual(reponse.status_code, 204, reponse.content)


class EcransDeSuiviTest(ApiContractTestCase):
    """
    Les écrans de suivi acceptent bien les trois rôles annoncés.

    La classe de permission autorisait les APPROBATEURS, puis un contrôle de
    rôle écrit dans le corps de la vue leur renvoyait 403 : deux règles pour
    une même porte, et elles se contredisaient.
    """

    def test_l_approbateur_consulte_les_evaluations_dues(self):
        reponse = self.client_for(self.approver).get('/api/v1/probation/evaluation-due/')
        self.assertEqual(reponse.status_code, 200, reponse.content)

    def test_l_approbateur_consulte_les_controles_en_retard(self):
        reponse = self.client_for(self.approver).get('/api/v1/training/maintenances/overdue/')
        self.assertEqual(reponse.status_code, 200, reponse.content)

    def test_un_agent_ordinaire_reste_refuse(self):
        self.assertEqual(
            self.client_for(self.agent).get('/api/v1/probation/evaluation-due/').status_code,
            403,
        )


class MotDePasseTest(ApiContractTestCase):
    """
    L'API applique AUTH_PASSWORD_VALIDATORS.

    Les quatre validateurs étaient configurés mais jamais exécutés : seule une
    longueur de 8 caractères était vérifiée, si bien que « 12345678 » passait.
    """

    def test_un_mot_de_passe_courant_est_refuse_a_la_creation(self):
        reponse = self.client_for(self.admin).post('/api/v1/auth/users/', {
            'matricule': 'ASE-2024-0500', 'email': 'nouveau@asecna.org',
            'first_name': 'Nou', 'last_name': 'Veau', 'password': 'password123',
        }, format='json')
        self.assertEqual(reponse.status_code, 400, reponse.content)

    def test_un_mot_de_passe_entierement_numerique_est_refuse(self):
        reponse = self.client_for(self.admin).post('/api/v1/auth/users/', {
            'matricule': 'ASE-2024-0501', 'email': 'num@asecna.org',
            'first_name': 'Num', 'last_name': 'Erique', 'password': '95831746',
        }, format='json')
        self.assertEqual(reponse.status_code, 400, reponse.content)

    def test_un_mot_de_passe_solide_est_accepte(self):
        reponse = self.client_for(self.admin).post('/api/v1/auth/users/', {
            'matricule': 'ASE-2024-0502', 'email': 'ok@asecna.org',
            'first_name': 'Bon', 'last_name': 'Compte', 'password': 'Tr4versee-Oblique',
        }, format='json')
        self.assertEqual(reponse.status_code, 201, reponse.content)

    def test_le_changement_de_mot_de_passe_est_valide_aussi(self):
        reponse = self.client_for(self.agent).put('/api/v1/auth/change-password/', {
            'old_password': PASSWORD, 'new_password': 'motdepasse',
        }, format='json')
        self.assertEqual(reponse.status_code, 400, reponse.content)


class JournalDAuditTest(ApiContractTestCase):
    """Le journal d'audit ne doit contenir aucun secret réutilisable."""

    def test_le_refresh_token_n_est_pas_conserve(self):
        """
        `POST /auth/logout/` transporte un refresh token. Le journal ne
        masquait que les mots de passe : la table d'audit conservait donc des
        jetons valides, lisibles par tout administrateur.
        """
        client = APIClient()
        jetons = client.post('/api/v1/auth/login/', {
            'matricule': self.agent.matricule, 'password': PASSWORD,
        }, format='json').data

        client.credentials(HTTP_AUTHORIZATION=f'Bearer {jetons["access"]}')
        client.post('/api/v1/auth/logout/', {'refresh': jetons['refresh']}, format='json')

        trace = AuditLog.objects.filter(endpoint='/api/v1/auth/logout/').first()
        self.assertIsNotNone(trace, "La déconnexion n'a pas été tracée.")
        self.assertEqual(trace.request_data.get('refresh'), '[masqué]')
        self.assertNotIn(jetons['refresh'], str(trace.request_data))


class QuotaDeConnexionTest(ApiContractTestCase):
    """
    L'authentification est limitée en débit.

    `LoginHistory` enregistrait chaque échec sans jamais le freiner : la trace
    documentait une attaque par force brute sans la gêner.

    Le quota est désactivé dans les settings de test (la suite enchaîne des
    dizaines d'authentifications) et rétabli ici. `override_settings` ne
    suffirait pas : `SimpleRateThrottle.THROTTLE_RATES` est lu une seule fois,
    à l'import du module DRF. C'est donc l'attribut de classe qu'il faut
    remplacer.
    """

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_les_tentatives_repetees_sont_bloquees(self):
        cible = make_user('ASE-2024-0600')
        client = APIClient()
        with patch.object(LoginRateThrottle, 'THROTTLE_RATES', {'login': '3/min'}):
            codes = [
                client.post('/api/v1/auth/login/', {
                    'matricule': cible.matricule, 'password': f'essai-{i}',
                }, format='json').status_code
                for i in range(5)
            ]
        self.assertEqual(codes[:3], [401, 401, 401], codes)
        self.assertEqual(codes[3:], [429, 429], f"Le quota n'a pas bloqué : {codes}")

    def test_une_connexion_valide_passe_quand_le_quota_est_libre(self):
        """Le quota ne doit pas gêner un usage normal."""
        client = APIClient()
        with patch.object(LoginRateThrottle, 'THROTTLE_RATES', {'login': '3/min'}):
            reponse = client.post('/api/v1/auth/login/', {
                'matricule': self.agent.matricule, 'password': PASSWORD,
            }, format='json')
        self.assertEqual(reponse.status_code, 200, reponse.content)
