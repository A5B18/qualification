"""
Le nombre de requêtes des listes ne doit pas dépendre du nombre de lignes.

Chaque test ci-dessous correspond à un N+1 constaté pendant l'audit. Ils ne
fixent pas un nombre absolu de requêtes — il évoluerait à chaque jointure
légitime ajoutée — mais vérifient que ce nombre reste le même avec une ligne
et avec une dizaine. C'est la propriété qui compte, et c'est elle qui se perd
silencieusement quand un serializer interroge la base par objet.
"""

import datetime

from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import AgentProfile, AgentStatus, UserRole
from apps.agents.models import AgentCertification
from apps.audit.models import AuditLog
from apps.reports.models import Report
from apps.units.models import Unit
from apps.workflows import services as workflows

from tests.test_api_contract import ApiContractTestCase, make_user


class RequetesConstantesTest(ApiContractTestCase):
    """Mesure avant / après ajout de lignes, sur le même utilisateur."""

    def _mesurer(self, client, url):
        with CaptureQueriesContext(connection) as capture:
            reponse = client.get(url)
        self.assertEqual(reponse.status_code, 200, reponse.content)
        return len(capture.captured_queries)

    def _verifier_constance(self, url, ajouter_lignes, user=None):
        """
        Compare le coût d'une liste courte et d'une liste deux fois plus
        longue.

        Les deux mesures portent sur une liste déjà peuplée : Django
        n'émet pas les requêtes de préchargement quand la page est vide, si
        bien qu'une comparaison « zéro ligne / N lignes » signalerait une
        différence qui n'a rien d'un N+1.
        """
        client = self.client_for(user or self.chief)
        ajouter_lignes(0)
        # Premier appel : amorce le cache de rôles de l'instance utilisateur.
        self._mesurer(client, url)
        avant = self._mesurer(client, url)

        ajouter_lignes(1)
        apres = self._mesurer(client, url)
        self.assertEqual(
            apres, avant,
            f"{url} : {avant} requête(s) pour un lot, {apres} pour deux — "
            "le compte doit rester constant.",
        )
        return avant

    def test_annuaire_des_agents(self):
        """
        `get_active_roles()` filtrait en base (`.filter(is_active=True)`), ce
        qui contournait le `prefetch_related('user_roles')` de la vue : une
        requête par agent listé.
        """
        def ajouter(lot):
            for i in range(10 * lot, 10 * lot + 10):
                agent = make_user(f'ASE-2024-07{i:02d}', roles=['EVALUATOR'])
                AgentProfile.objects.create(
                    user=agent, unit=self.unit, status=AgentStatus.NEW,
                    specialty=self.specialty,
                )

        self._verifier_constance('/api/v1/auth/users/', ajouter)

    def test_liste_des_unites(self):
        """Le serializer cherchait le chef et comptait les agents par unité."""
        def ajouter(lot):
            for i in range(10 * lot, 10 * lot + 10):
                Unit.objects.create(
                    code=f'U{i:02d}', name=f'Unité {i}', unit_type='TWR',
                )

        self._verifier_constance('/api/v1/units/', ajouter)

    def test_registre_d_approbation(self):
        """
        La clé générique était résolue ligne par ligne, puis l'agent et
        l'examen de chaque objet. `GenericPrefetch` les charge en lot.
        """
        def ajouter(lot):
            for i in range(10 * lot, 10 * lot + 10):
                rapport = Report.objects.create(
                    report_type='ASSESSMENT', agent=self.agent,
                    created_by=self.chief, title=f'Rapport {i}', content='…',
                )
                workflows.record_submission(rapport, submitted_by=self.chief)

        self._verifier_constance('/api/v1/workflows/', ajouter)

    def test_carnets_arcep(self):
        """L'en-tête du carnet agrège cinq sources par agent."""
        from apps.arcep.models import ARCEPBook

        def ajouter(lot):
            for i in range(10 * lot, 10 * lot + 10):
                agent = make_user(f'ASE-2024-08{i:02d}')
                ARCEPBook.objects.create(agent=agent)
                AgentCertification.objects.create(
                    agent=agent, name=f'Certification {i}',
                    issue_date=datetime.date(2024, 1, 1),
                )

        self._verifier_constance('/api/v1/arcep/books/', ajouter)

    def test_journal_d_audit(self):
        """Le serializer rend l'utilisateur de chaque ligne."""
        def ajouter(lot):
            for i in range(10 * lot, 10 * lot + 10):
                AuditLog.objects.create(
                    user=make_user(f'ASE-2024-09{i:02d}'), action='POST',
                    endpoint=f'/api/v1/x/{i}/', status_code=201,
                )

        self._verifier_constance('/api/v1/audit/logs/', ajouter, user=self.admin)

    def test_les_controles_de_role_ne_coutent_qu_une_requete(self):
        """
        Les vues enchaînent plusieurs contrôles de rôle (permission,
        cloisonnement, règle métier). Ils doivent se partager un seul accès
        à la table `UserRole`.
        """
        decideur = make_user('ASE-2024-0950', roles=['UNIT_CHIEF', 'APPROVER'])
        UserRole.objects.create(user=decideur, role='EVALUATOR')
        client = self.client_for(decideur)
        self._mesurer(client, '/api/v1/reports/')  # amorce

        with CaptureQueriesContext(connection) as capture:
            client.get('/api/v1/reports/')
        requetes_roles = [
            q for q in capture.captured_queries
            if 'accounts_user_role' in q['sql']
        ]
        self.assertLessEqual(
            len(requetes_roles), 1,
            f"{len(requetes_roles)} requêtes de rôles pour un seul appel.",
        )
