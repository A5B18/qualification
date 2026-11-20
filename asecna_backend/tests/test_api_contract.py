"""
Tests de contrat de l'API — un par role fonctionnel.

Ces tests couvrent ce que les tests par app ne couvraient pas : la traversee
reelle des vues, des permissions et des serializers. Ils ont ete ajoutes apres
avoir constate que plusieurs endpoints renvoyaient HTTP 500 (serializers
referencant des champs inexistants) ou HTTP 403 (permissions retombant sur une
regle plus restrictive que celle documentee) alors que les 110 tests existants,
purement orientes modeles, passaient tous.

Regle : tout endpoint liste par le frontend doit repondre sans erreur serveur,
et chaque role doit acceder aux ecrans de son menu.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserRole, AgentProfile, AgentStatus
from apps.arcep.models import ARCEPBook, ARCEPEntry, ARCEPSignature
from apps.evaluations.models import Question, Exam, ExamSession, Answer
from apps.mentoring.models import MentoringRecord
from apps.probation.models import ProbationPeriod
from apps.reports.models import Report
from apps.training.models import Specialty, Training, QualificationMaintenance
from apps.units.models import Unit

User = get_user_model()

PASSWORD = 'Passw0rd!2024'


def make_user(matricule, roles=(), **kwargs):
    user = User.objects.create_user(
        matricule=matricule,
        email=f'{matricule.lower()}@asecna.org',
        first_name='Test',
        last_name=matricule[-4:],
        password=PASSWORD,
        **kwargs,
    )
    for role in roles:
        UserRole.objects.create(user=user, role=role)
    return user


class ApiContractTestCase(TestCase):
    """Jeu de donnees commun : un utilisateur par role + une donnee par app."""

    @classmethod
    def setUpTestData(cls):
        cls.unit = Unit.objects.create(
            code='DKR', name='Dakar', unit_type='ACC', location='Dakar', country='SN',
        )
        cls.specialty = Specialty.objects.create(code='ATC', name='Controle')
        cls.training = Training.objects.create(
            title='Qualification', specialty=cls.specialty,
            duration_days=10, passing_score=80,
        )

        cls.admin = make_user('ASE-2024-0001', roles=['ADMIN'])
        cls.chief = make_user('ASE-2024-0002', roles=['UNIT_CHIEF'])
        cls.evaluator = make_user('ASE-2024-0003', roles=['EVALUATOR'])
        cls.mentor = make_user('ASE-2024-0004', roles=['MENTOR'])
        cls.instructor = make_user('ASE-2024-0005', roles=['INSTRUCTOR'])
        cls.approver = make_user('ASE-2024-0006', roles=['APPROVER'])
        cls.agent = make_user('ASE-2024-0007')
        cls.superuser = User.objects.create_superuser(
            matricule='ASE-2024-0009', email='su@asecna.org',
            first_name='Super', last_name='User', password=PASSWORD,
        )

        AgentProfile.objects.create(
            user=cls.agent, unit=cls.unit,
            status=AgentStatus.QUALIFIED, specialty=cls.specialty,
            hire_date=datetime.date(2024, 1, 15),
        )

        today = datetime.date.today()
        cls.probation = ProbationPeriod.objects.create(
            agent=cls.agent, attempt_number=1,
            start_date=today - datetime.timedelta(days=80),
            end_date=today + datetime.timedelta(days=10),
        )
        # Le carnet ARCEP est cree automatiquement par signal au passage QUALIFIED
        cls.book = ARCEPBook.objects.get(agent=cls.agent)
        cls.entry = ARCEPEntry.objects.create(
            book=cls.book, entry_date=today, activity='Vol', duration_hours=3,
        )
        cls.signature = ARCEPSignature.objects.create(
            book=cls.book, unit_chief=cls.chief,
            period_start=today - datetime.timedelta(days=30), period_end=today,
        )
        cls.mentoring = MentoringRecord.objects.create(
            agent=cls.agent, mentor=cls.mentor,
            start_date=today - datetime.timedelta(days=10), objectives='Objectifs',
        )
        cls.report = Report.objects.create(
            report_type='PROBATION', agent=cls.agent, created_by=cls.chief,
            title='Rapport', content='Contenu',
        )
        cls.maintenance = QualificationMaintenance.objects.create(
            agent=cls.agent, training=cls.training,
            due_date=today - datetime.timedelta(days=5),
        )
        # Toute question est un QCM : la bonne reponse figure parmi les
        # options, et `submit-answer` n'accepte que l'une d'elles.
        cls.question = Question.objects.create(
            question_type='TECHNICAL', text='Question ?', correct_answer='A',
            options=['A', 'B', 'C', 'D'],
            points=10, created_by=cls.evaluator,
        )
        cls.exam = Exam.objects.create(
            title='Examen', training=cls.training,
            created_by=cls.evaluator, exam_status='PUBLISHED',
        )
        cls.exam.questions.add(cls.question)
        cls.session = ExamSession.objects.create(
            exam=cls.exam, agent=cls.agent, session_status='SUBMITTED',
        )
        cls.answer = Answer.objects.create(
            session=cls.session, question=cls.question, response='A',
        )

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client


class NoServerErrorTest(ApiContractTestCase):
    """Aucun endpoint de lecture ne doit renvoyer une erreur serveur (5xx)."""

    READ_ENDPOINTS = [
        '/api/v1/auth/me/',
        '/api/v1/auth/users/',
        '/api/v1/units/',
        '/api/v1/agents/skills/',
        '/api/v1/agents/certifications/',
        '/api/v1/agents/performances/',
        '/api/v1/probation/',
        '/api/v1/probation/evaluation-due/',
        '/api/v1/mentoring/',
        '/api/v1/training/specialties/',
        '/api/v1/training/trainings/',
        '/api/v1/training/courses/',
        '/api/v1/training/internships/',
        '/api/v1/training/maintenances/',
        '/api/v1/training/maintenances/overdue/',
        '/api/v1/evaluations/questions/',
        '/api/v1/evaluations/exams/',
        '/api/v1/evaluations/sessions/',
        '/api/v1/workflows/',
        '/api/v1/workflows/pending/',
        '/api/v1/arcep/books/',
        '/api/v1/arcep/entries/',
        '/api/v1/arcep/signatures/',
        '/api/v1/reports/',
        '/api/v1/audit/logs/',
        '/api/v1/audit/logins/',
    ]

    def test_aucune_erreur_serveur_pour_aucun_role(self):
        users = {
            'ADMIN': self.admin, 'SUPERUSER': self.superuser,
            'UNIT_CHIEF': self.chief, 'EVALUATOR': self.evaluator,
            'MENTOR': self.mentor, 'INSTRUCTOR': self.instructor,
            'APPROVER': self.approver, 'AGENT': self.agent,
        }
        failures = []
        for role, user in users.items():
            client = self.client_for(user)
            for endpoint in self.READ_ENDPOINTS:
                response = client.get(endpoint)
                if response.status_code >= 500:
                    failures.append(f'{endpoint} [{role}] -> {response.status_code}')
        self.assertEqual(failures, [], 'Erreurs serveur :\n' + '\n'.join(failures))

    def test_entrees_et_signatures_arcep_se_serialisent(self):
        """Regression : ces serializers lisaient des champs inexistants (500)."""
        client = self.client_for(self.admin)

        response = client.get('/api/v1/arcep/entries/')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data['count'], 0)
        self.assertIn('is_validated', response.data['results'][0])

        response = client.get('/api/v1/arcep/signatures/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data['results'][0]['unit_chief_detail'])

        response = client.get(
            f'/api/v1/arcep/signatures/{self.signature.id}/covered-entries/'
        )
        self.assertEqual(response.status_code, 200)

    def test_rapports_se_serialisent(self):
        """Regression : ReportSerializer lisait `approved_by`, inexistant (500)."""
        client = self.client_for(self.chief)
        response = client.get('/api/v1/reports/')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data['count'], 0)


class RoleAccessTest(ApiContractTestCase):
    """Chaque role doit acceder aux endpoints dont son menu depend."""

    def test_evaluateur_accede_aux_alertes_de_suivi(self):
        """Regression : ces deux actions renvoyaient 403 a l'evaluateur."""
        client = self.client_for(self.evaluator)
        self.assertEqual(client.get('/api/v1/probation/evaluation-due/').status_code, 200)
        self.assertEqual(client.get('/api/v1/training/maintenances/overdue/').status_code, 200)

    def test_chef_unite_accede_aux_maintiens_en_retard(self):
        """Regression : l'action retombait sur IsAdministrator -> 403."""
        client = self.client_for(self.chief)
        self.assertEqual(client.get('/api/v1/training/maintenances/overdue/').status_code, 200)

    def test_annuaire_des_agents_ouvert_aux_roles_d_encadrement(self):
        """Regression : /auth/users/ etait admin-only, vidant la page Agents."""
        for user in (self.chief, self.evaluator, self.mentor, self.instructor, self.approver):
            client = self.client_for(user)
            response = client.get('/api/v1/auth/users/')
            self.assertEqual(response.status_code, 200, f'{user.matricule} : 403 sur l annuaire')
            self.assertGreater(response.data['count'], 1)

    def test_agent_simple_ne_voit_que_sa_fiche(self):
        client = self.client_for(self.agent)
        response = client.get('/api/v1/auth/users/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['matricule'], self.agent.matricule)

    def test_ecriture_annuaire_reservee_a_l_admin(self):
        payload = {
            'matricule': 'ASE-2024-0500', 'email': 'x@asecna.org',
            'first_name': 'X', 'last_name': 'Y', 'password': PASSWORD,
        }
        self.assertEqual(
            self.client_for(self.chief).post('/api/v1/auth/users/', payload, format='json').status_code,
            403,
        )
        self.assertIn(
            self.client_for(self.admin).post('/api/v1/auth/users/', payload, format='json').status_code,
            (200, 201),
        )

    def test_audit_reserve_a_l_admin(self):
        self.assertEqual(self.client_for(self.chief).get('/api/v1/audit/logs/').status_code, 403)
        self.assertEqual(self.client_for(self.admin).get('/api/v1/audit/logs/').status_code, 200)


class UserPayloadTest(ApiContractTestCase):
    """Le profil renvoye doit contenir ce dont le frontend a besoin."""

    def test_superutilisateur_identifie_comme_admin(self):
        """
        Regression : un superutilisateur Django n'a aucune ligne UserRole.
        Sans `is_admin` / `is_superuser` dans la reponse, le frontend lui
        affichait le tableau de bord d'un simple agent.
        """
        response = self.client_for(self.superuser).get('/api/v1/auth/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['roles'], [])
        self.assertTrue(response.data['is_admin'])
        self.assertTrue(response.data['is_superuser'])

    def test_me_expose_le_nom_complet_et_le_parcours(self):
        response = self.client_for(self.agent).get('/api/v1/auth/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['full_name'], self.agent.full_name)
        self.assertEqual(response.data['status'], AgentStatus.QUALIFIED)
        self.assertEqual(response.data['unit'], self.unit.id)
        self.assertIsNotNone(response.data['agent_profile'])
        self.assertEqual(response.data['unit_detail']['code'], 'DKR')

    def test_liste_des_agents_porte_identite_et_affectation(self):
        """Regression : la page Agents lit user_detail / unit_detail / hire_date."""
        response = self.client_for(self.chief).get('/api/v1/auth/users/?page_size=100')
        self.assertEqual(response.status_code, 200)
        row = next(r for r in response.data['results'] if r['id'] == self.agent.id)
        self.assertEqual(row['user'], self.agent.id)
        self.assertEqual(row['user_detail']['matricule'], self.agent.matricule)
        self.assertEqual(row['unit_detail']['code'], 'DKR')
        self.assertEqual(str(row['hire_date']), '2024-01-15')
        self.assertEqual(row['status'], AgentStatus.QUALIFIED)

    def test_page_size_est_respecte(self):
        """Regression : ?page_size= etait ignore (liste tronquee a 20)."""
        response = self.client_for(self.admin).get('/api/v1/auth/users/?page_size=2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        self.assertGreater(response.data['count'], 2)


class FilteringTest(ApiContractTestCase):
    """Les filtres ?agent= / ?book= utilises par le frontend doivent agir."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Un second agent avec ses propres donnees, pour verifier le cloisonnement
        cls.other = make_user('ASE-2024-0008')
        AgentProfile.objects.create(
            user=cls.other, unit=cls.unit, status=AgentStatus.PROBATION,
        )
        today = datetime.date.today()
        cls.other_probation = ProbationPeriod.objects.create(
            agent=cls.other, attempt_number=1,
            start_date=today - datetime.timedelta(days=85),
            end_date=today + datetime.timedelta(days=5),
        )

    def test_filtre_agent_sur_probation(self):
        """Regression : ?agent= etait ignore, la fiche agent listait tout le monde."""
        client = self.client_for(self.admin)
        toutes = client.get('/api/v1/probation/')
        self.assertEqual(toutes.data['count'], 2)

        filtrees = client.get(f'/api/v1/probation/?agent={self.agent.id}')
        self.assertEqual(filtrees.data['count'], 1)
        self.assertEqual(filtrees.data['results'][0]['agent'], self.agent.id)

    def test_filtre_agent_sur_mentorat_et_rapports(self):
        client = self.client_for(self.admin)
        self.assertEqual(
            client.get(f'/api/v1/mentoring/?agent={self.other.id}').data['count'], 0,
        )
        self.assertEqual(
            client.get(f'/api/v1/mentoring/?agent={self.agent.id}').data['count'], 1,
        )
        self.assertEqual(
            client.get(f'/api/v1/reports/?agent={self.agent.id}').data['count'], 1,
        )

    def test_filtre_book_sur_entrees_arcep(self):
        """Regression : ?book= etait ignore, chaque carnet montrait tout."""
        client = self.client_for(self.admin)
        response = client.get(f'/api/v1/arcep/entries/?book={self.book.id}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(e['book'] == self.book.id for e in response.data['results']))

    def test_filtre_unit_sur_annuaire(self):
        client = self.client_for(self.admin)
        response = client.get(f'/api/v1/auth/users/?unit={self.unit.id}&page_size=100')
        self.assertEqual(response.status_code, 200)
        matricules = {r['matricule'] for r in response.data['results']}
        self.assertEqual(matricules, {self.agent.matricule, self.other.matricule})


class ValidationErrorTest(ApiContractTestCase):
    """Une saisie invalide doit produire un 400 explicite, jamais un 500."""

    def test_duree_de_probation_invalide_renvoie_400(self):
        """
        Regression : ProbationPeriod.save() appelle full_clean(). La
        ValidationError de Django n'etait pas convertie par DRF et remontait
        donc en HTTP 500 avec un message generique.
        """
        today = datetime.date.today()
        response = self.client_for(self.chief).post('/api/v1/probation/', {
            'agent': self.other_agent_id(), 'attempt_number': 1,
            'start_date': str(today), 'end_date': str(today + datetime.timedelta(days=5)),
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)
        self.assertIn('3 mois', response.data['error']['message'])

    def other_agent_id(self):
        user = make_user('ASE-2024-0300')
        AgentProfile.objects.create(user=user, unit=self.unit)
        return user.id

    def test_score_non_numerique_renvoie_400(self):
        """Regression : float('abc') non protege -> HTTP 500."""
        response = self.client_for(self.evaluator).post(
            f'/api/v1/evaluations/sessions/{self.session.id}/grade-answer/',
            {'answer_id': self.answer.id, 'is_correct': True, 'evaluator_score': 'abc'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_score_hors_bareme_renvoie_400(self):
        response = self.client_for(self.evaluator).post(
            f'/api/v1/evaluations/sessions/{self.session.id}/grade-answer/',
            {'answer_id': self.answer.id, 'is_correct': True, 'evaluator_score': 999},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_score_de_probation_non_numerique_renvoie_400(self):
        response = self.client_for(self.evaluator).post(
            f'/api/v1/probation/{self.probation.id}/finalize/',
            {'score': 'beaucoup'}, format='json',
        )
        self.assertEqual(response.status_code, 400)


class ArcepSignatureFlowTest(ApiContractTestCase):
    """Signature d'un carnet avec le payload reellement envoye par le frontend."""

    def test_signature_sans_periode_la_deduit_des_entrees(self):
        """
        Regression : le frontend envoyait `{ book, notes }`. `notes` n'existe
        pas sur le modele et la periode, obligatoire, manquait -> 400.
        La vue deduit desormais la periode des entrees non signees.
        """
        book = ARCEPBook.objects.create(agent=self.chief)
        today = datetime.date.today()
        ARCEPEntry.objects.create(
            book=book, entry_date=today - datetime.timedelta(days=3),
            activity='Maintenance', duration_hours=4,
        )
        ARCEPEntry.objects.create(
            book=book, entry_date=today, activity='Test radar', duration_hours=2,
        )

        response = self.client_for(self.chief).post('/api/v1/arcep/signatures/', {
            'book': book.id, 'comment': 'Controle periodique',
        }, format='json')

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['period_start'], str(today - datetime.timedelta(days=3)))
        self.assertEqual(response.data['period_end'], str(today))
        self.assertEqual(response.data['covered_entries_count'], 2)
        self.assertEqual(response.data['unit_chief'], self.chief.id)

    def test_periode_inversee_refusee(self):
        today = datetime.date.today()
        response = self.client_for(self.chief).post('/api/v1/arcep/signatures/', {
            'book': self.book.id,
            'period_start': str(today),
            'period_end': str(today - datetime.timedelta(days=10)),
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_signature_reservee_au_chef_d_unite(self):
        response = self.client_for(self.agent).post('/api/v1/arcep/signatures/', {
            'book': self.book.id, 'comment': 'tentative',
        }, format='json')
        self.assertEqual(response.status_code, 403)


class UnitSerializerTest(ApiContractTestCase):
    """Compteur d'agents et chef d'unite exposes par /units/."""

    def test_compteur_agents_non_nul(self):
        """Regression : le serializer lisait `obj.members` -> toujours 0."""
        response = self.client_for(self.admin).get('/api/v1/units/')
        self.assertEqual(response.status_code, 200)
        unit = next(u for u in response.data['results'] if u['id'] == self.unit.id)
        self.assertEqual(unit['agents_count'], 1)

    def test_chef_unite_deduit_du_role(self):
        AgentProfile.objects.create(user=self.chief, unit=self.unit)
        response = self.client_for(self.admin).get('/api/v1/units/')
        unit = next(u for u in response.data['results'] if u['id'] == self.unit.id)
        self.assertIsNotNone(unit['chief_detail'])
        self.assertEqual(unit['chief_detail']['matricule'], self.chief.matricule)


class LoginHistoryTest(TestCase):
    """L'historique des connexions doit etre alimente (il restait vide)."""

    def setUp(self):
        self.user = make_user('ASE-2024-0400', roles=['ADMIN'])

    def test_connexion_reussie_enregistree(self):
        from apps.audit.models import LoginHistory

        client = APIClient()
        response = client.post('/api/v1/auth/login/', {
            'matricule': self.user.matricule, 'password': PASSWORD,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        entry = LoginHistory.objects.filter(matricule_attempted=self.user.matricule).first()
        self.assertIsNotNone(entry, "La connexion reussie n'a pas ete tracee")
        self.assertEqual(entry.result, LoginHistory.LoginResult.SUCCESS)
        self.assertEqual(entry.user, self.user)

    def test_connexion_echouee_enregistree(self):
        from apps.audit.models import LoginHistory

        client = APIClient()
        response = client.post('/api/v1/auth/login/', {
            'matricule': self.user.matricule, 'password': 'mauvais-mot-de-passe',
        }, format='json')
        self.assertEqual(response.status_code, 401)
        entry = LoginHistory.objects.filter(
            matricule_attempted=self.user.matricule,
            result=LoginHistory.LoginResult.FAILURE,
        ).first()
        self.assertIsNotNone(entry, "L'echec de connexion n'a pas ete trace")

    def test_login_renvoie_les_indicateurs_admin(self):
        client = APIClient()
        response = client.post('/api/v1/auth/login/', {
            'matricule': self.user.matricule, 'password': PASSWORD,
        }, format='json')
        self.assertTrue(response.data['user']['is_admin'])
        self.assertIn('is_superuser', response.data['user'])


class QualificationMaintenanceSerializerTest(ApiContractTestCase):
    """
    Regression : `QualificationMaintenanceSerializer` n'existait pas.

    Le `get_serializer_class()` de la vue l'importait dans un
    `try/except ImportError` et retombait donc TOUJOURS sur une classe anonyme
    `_FallbackSerializer`, sans aucun champ `*_detail` : la page Maintien QF
    affichait des lignes sans identite d'agent.
    """

    def test_le_maintien_expose_l_identite_de_l_agent(self):
        response = self.client_for(self.evaluator).get('/api/v1/training/maintenances/')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data['count'], 0)

        row = next(r for r in response.data['results'] if r['id'] == self.maintenance.id)
        self.assertIsNotNone(row['agent_detail'], 'agent_detail absent du maintien')
        self.assertEqual(row['agent_detail']['matricule'], self.agent.matricule)
        self.assertEqual(row['agent_detail']['full_name'], self.agent.full_name)
        self.assertEqual(row['training_detail']['title'], self.training.title)

    def test_echeance_depassee_signalee(self):
        # setUpTestData cree un maintien PENDING avec due_date a J-5
        response = self.client_for(self.evaluator).get('/api/v1/training/maintenances/')
        row = next(r for r in response.data['results'] if r['id'] == self.maintenance.id)
        self.assertTrue(row['is_overdue'])
        self.assertFalse(row['score_passed'])

    def test_le_score_n_est_pas_modifiable_directement(self):
        """Le score passe par finalize(), pas par un PATCH direct."""
        response = self.client_for(self.admin).patch(
            f'/api/v1/training/maintenances/{self.maintenance.id}/',
            {'score': 95}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.maintenance.refresh_from_db()
        self.assertIsNone(self.maintenance.score)

    def test_finalize_echoue_suspend_l_agent(self):
        response = self.client_for(self.evaluator).post(
            f'/api/v1/training/maintenances/{self.maintenance.id}/finalize/',
            {'score': 50, 'notes': 'insuffisant'}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['maintenance_status'], 'FAILED')
        self.agent.agent_profile.refresh_from_db()
        self.assertEqual(self.agent.agent_profile.status, AgentStatus.SUSPENDED)


class LogoutTest(ApiContractTestCase):
    """
    Deconnexion : blacklistage du refresh token.

    La vue n'avait pas de `serializer_class`, ce qui la faisait exclure du
    schema OpenAPI (endpoint absent de Swagger).
    """

    def _tokens(self):
        client = APIClient()
        response = client.post('/api/v1/auth/login/', {
            'matricule': self.agent.matricule, 'password': PASSWORD,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_logout_blackliste_le_refresh(self):
        tokens = self._tokens()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')

        response = client.post('/api/v1/auth/logout/',
                               {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(response.status_code, 200)

        # Le refresh ne doit plus permettre d'obtenir un access token
        refreshed = APIClient().post('/api/v1/auth/token/refresh/',
                                     {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(refreshed.status_code, 401)

    def test_logout_sans_refresh_renvoie_400(self):
        tokens = self._tokens()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = client.post('/api/v1/auth/logout/', {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_logout_avec_refresh_invalide_renvoie_400(self):
        tokens = self._tokens()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = client.post('/api/v1/auth/logout/',
                               {'refresh': 'pas-un-jeton'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_logout_expose_dans_le_schema_openapi(self):
        """Regression : l'endpoint etait silencieusement absent du schema."""
        response = self.client_for(self.admin).get('/api/schema/?format=json')
        self.assertEqual(response.status_code, 200)
        paths = response.data['paths']
        self.assertIn('/api/v1/auth/logout/', paths)
        self.assertIn('post', paths['/api/v1/auth/logout/'])


class WorkflowTest(ApiContractTestCase):
    """
    Workflows d'approbation (GenericForeignKey).

    Regression : le serializer appelait `user.get_full_name()`. Le modele User
    derive d'AbstractBaseUser et expose une PROPRIETE `full_name`, pas cette
    methode : /workflows/ et /workflows/pending/ renvoyaient donc 500 des que
    la table contenait une ligne. Le bug etait invisible tant que la table
    restait vide.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from django.contrib.contenttypes.models import ContentType
        from apps.workflows.models import ApprovalWorkflow

        cls.workflow = ApprovalWorkflow.objects.create(
            content_type=ContentType.objects.get_for_model(Report),
            object_id=cls.report.id,
            submitted_by=cls.chief,
            approver=cls.approver,
            unit_chief=cls.chief,
            workflow_status=ApprovalWorkflow.WorkflowStatus.SUBMITTED,
            submitted_at=timezone.now(),
        )

    def test_liste_des_workflows_se_serialise(self):
        response = self.client_for(self.admin).get('/api/v1/workflows/')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data['count'], 0)
        row = response.data['results'][0]
        self.assertEqual(row['submitted_by_name'], self.chief.full_name)
        self.assertEqual(row['approver_name'], self.approver.full_name)
        self.assertIsNotNone(row['content_type_label'])

    def test_workflows_en_attente(self):
        response = self.client_for(self.approver).get('/api/v1/workflows/pending/')
        self.assertEqual(response.status_code, 200)

    def test_modele_user_expose_l_interface_django(self):
        """get_full_name()/get_short_name() : contrat attendu par Django."""
        self.assertEqual(self.chief.get_full_name(), self.chief.full_name)
        self.assertEqual(self.chief.get_short_name(), self.chief.first_name)


class HtmlPagesTest(TestCase):
    """
    Pages HTML : admin Django, Swagger, ReDoc, schema OpenAPI.

    Ces tests n'etaient pas ecrivables sous Django 4.2 + Python 3.14 : le client
    de test copie le contexte de gabarit a chaque rendu, et `BaseContext.__copy__`
    echouait (`copy(super())` incompatible avec Python 3.14). Django 5.2 corrige
    le probleme ; on verrouille donc la capacite en meme temps que les pages.
    """

    def setUp(self):
        self.admin = make_user('ASE-2024-0600', roles=['ADMIN'], is_staff=True)

    def test_page_de_connexion_admin_se_rend(self):
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, 200)
        # config/urls.py remplace le formulaire d'admin par MatriculeAuthForm :
        # le champ reste nomme `username` mais est libelle et aide pour un
        # matricule ASECNA. On ancre sur l'exemple, sans ambiguite.
        self.assertContains(response, 'ASE-2024-0001')

    def test_admin_accessible_a_un_membre_du_staff(self):
        self.client.force_login(self.admin)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ASECNA')

    def test_schema_openapi_se_genere(self):
        response = self.client.get('/api/schema/')
        self.assertEqual(response.status_code, 200)

    def test_swagger_et_redoc_se_rendent(self):
        for url in ('/api/docs/', '/api/redoc/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_url_inconnue_renvoie_404(self):
        self.assertEqual(self.client.get('/route/inexistante/').status_code, 404)
