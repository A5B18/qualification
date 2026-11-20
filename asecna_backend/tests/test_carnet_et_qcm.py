"""
Deux regles metier ajoutees ensemble, et leurs contrats d'API.

1. Le carnet ARCEP porte l'identite de son titulaire et l'etat de ses
   qualifications. Un releve d'activites anonyme n'est pas opposable : il doit
   nommer l'agent, dire sa profession, son unite, et montrer les echeances a
   tenir.

2. Toute question d'evaluation est un QCM. Le serveur refuse ce qui ne peut
   pas se corriger : une question sans option, une bonne reponse absente des
   propositions, une reponse d'agent hors des options.
"""

import datetime

from apps.agents.models import AgentCertification
from apps.evaluations.models import Answer, ExamSession, Question

from tests.test_api_contract import ApiContractTestCase, make_user


class CarnetARCEPIdentiteTest(ApiContractTestCase):
    """Le carnet ARCEP s'ouvre sur l'identite de son titulaire."""

    def carnet(self, user=None):
        """Premiere ligne de la liste des carnets, vue par un chef d'unite."""
        reponse = self.client_for(user or self.chief).get('/api/v1/arcep/books/')
        self.assertEqual(reponse.status_code, 200, reponse.content)
        return reponse.json()['results'][0]

    def test_le_carnet_nomme_son_titulaire(self):
        identite = self.carnet()['agent_identity']
        self.assertEqual(identite['matricule'], self.agent.matricule)
        self.assertEqual(identite['last_name'], self.agent.last_name)
        self.assertEqual(identite['first_name'], self.agent.first_name)
        self.assertEqual(identite['full_name'], self.agent.full_name)

    def test_le_carnet_porte_la_profession_et_l_unite(self):
        identite = self.carnet()['agent_identity']
        self.assertEqual(identite['profession'], 'Controle')
        self.assertEqual(identite['profession_code'], 'ATC')
        self.assertEqual(identite['unit']['code'], 'DKR')
        self.assertEqual(identite['unit']['unit_type'], 'ACC')

    def test_le_carnet_porte_le_statut_et_les_dates_cles(self):
        identite = self.carnet()['agent_identity']
        self.assertEqual(identite['career_status'], 'QUALIFIED')
        self.assertEqual(identite['career_status_label'], 'Qualifié')
        self.assertEqual(identite['hire_date'], '2024-01-15')
        # L'anciennete se deduit de la date de recrutement.
        self.assertIsNotNone(identite['seniority_years'])
        self.assertGreaterEqual(identite['seniority_years'], 0)

    def test_le_carnet_liste_les_qualifications_avec_leurs_echeances(self):
        today = datetime.date.today()
        AgentCertification.objects.create(
            agent=self.agent, name='Licence ATC', issuing_body='EAMAC',
            issue_date=today - datetime.timedelta(days=365),
            expiry_date=today + datetime.timedelta(days=30),
        )
        carnet = self.carnet()
        libelles = {q['label']: q for q in carnet['qualifications']}

        # La certification expire dans 30 jours : dans la fenetre d'alerte.
        licence = libelles['Licence ATC']
        self.assertEqual(licence['kind'], 'CERTIFICATION')
        self.assertEqual(licence['status'], 'EXPIRING')
        self.assertEqual(licence['days_remaining'], 30)
        self.assertTrue(licence['tracks_due'])

        # Le controle biennal du jeu de donnees est en retard de 5 jours.
        controle = libelles['Qualification']
        self.assertEqual(controle['kind'], 'MAINTENANCE')
        self.assertEqual(controle['status'], 'OVERDUE')

    def test_une_echeance_depassee_place_le_carnet_en_alerte(self):
        resume = self.carnet()['qualifications_summary']
        # Le controle biennal du jeu de donnees est deja en retard.
        self.assertEqual(resume['alert_level'], 'CRITICAL')
        self.assertGreaterEqual(resume['expired'], 1)

    def test_la_prochaine_echeance_ignore_les_controles_deja_passes(self):
        today = datetime.date.today()
        AgentCertification.objects.create(
            agent=self.agent, name='Habilitation électrique',
            issue_date=today, expiry_date=today + datetime.timedelta(days=200),
        )
        resume = self.carnet()['qualifications_summary']
        # Seule la certification a venir est une echeance a tenir : le
        # controle biennal en retard est deja derriere l'agent.
        self.assertEqual(resume['next_due_label'], 'Habilitation électrique')
        self.assertEqual(resume['next_due_in_days'], 200)

    def test_une_certification_sans_expiration_est_sans_echeance(self):
        AgentCertification.objects.create(
            agent=self.agent, name='Diplôme initial',
            issue_date=datetime.date(2020, 6, 1), expiry_date=None,
        )
        ligne = next(q for q in self.carnet()['qualifications']
                     if q['label'] == 'Diplôme initial')
        self.assertEqual(ligne['status'], 'PERMANENT')
        self.assertIsNone(ligne['days_remaining'])
        self.assertFalse(ligne['tracks_due'])

    def test_le_carnet_compte_les_entrees_en_attente_de_visa(self):
        from apps.arcep.models import ARCEPEntry

        # Le jeu de donnees signe la periode [J-30, J] : une entree posterieure
        # n'est couverte par aucune signature.
        ARCEPEntry.objects.create(
            book=self.book, entry_date=datetime.date.today() + datetime.timedelta(days=1),
            activity='Maintenance radar', duration_hours=2,
        )
        carnet = self.carnet()
        self.assertEqual(carnet['pending_signature_count'], 1)
        self.assertEqual(carnet['entries_count'], 2)
        self.assertEqual(carnet['total_hours'], 5.0)

    def test_l_agent_lit_l_en_tete_de_son_propre_carnet(self):
        """Le titulaire doit voir sa propre fiche, pas seulement le chef."""
        carnet = self.carnet(self.agent)
        self.assertEqual(carnet['agent_identity']['matricule'], self.agent.matricule)


class QuestionQCMTest(ApiContractTestCase):
    """La banque de questions n'accepte que des QCM corrigibles."""

    URL = '/api/v1/evaluations/questions/'

    @staticmethod
    def champs_refuses(reponse):
        """
        Champs cites par le refus.

        L'API enveloppe les erreurs de validation dans
        `{'error': {'details': {champ: [...]}}}` (core.exceptions) : c'est la
        qu'il faut lire le champ fautif, pas a la racine.
        """
        return reponse.json()['error']['details']

    def creer(self, **payload):
        donnees = {
            'question_type': 'TECHNICAL',
            'text': 'Quelle est la bande VOR ?',
            'correct_answer': '108 - 117,975 MHz',
            'options': ['108 - 117,975 MHz', '329 - 335 MHz'],
            'points': 10,
        }
        donnees.update(payload)
        return self.client_for(self.evaluator).post(self.URL, donnees, format='json')

    def test_un_qcm_complet_est_accepte(self):
        reponse = self.creer()
        self.assertEqual(reponse.status_code, 201, reponse.content)
        self.assertEqual(reponse.json()['question_kind'], 'MCQ')

    def test_une_question_sans_option_est_refusee(self):
        reponse = self.creer(options=[])
        self.assertEqual(reponse.status_code, 400)
        self.assertIn('options', self.champs_refuses(reponse))

    def test_une_question_a_une_seule_option_est_refusee(self):
        reponse = self.creer(options=['108 - 117,975 MHz'])
        self.assertEqual(reponse.status_code, 400)
        self.assertIn('options', self.champs_refuses(reponse))

    def test_deux_options_identiques_sont_refusees(self):
        reponse = self.creer(options=['Vrai', 'vrai'], correct_answer='Vrai')
        self.assertEqual(reponse.status_code, 400)
        self.assertIn('options', self.champs_refuses(reponse))

    def test_la_bonne_reponse_doit_figurer_parmi_les_options(self):
        reponse = self.creer(correct_answer='960 - 1215 MHz')
        self.assertEqual(reponse.status_code, 400)
        self.assertIn('correct_answer', self.champs_refuses(reponse))

    def test_les_options_vides_du_formulaire_sont_ecartees(self):
        """L'ecran propose quatre champs ; les vides ne vont pas en base."""
        reponse = self.creer(options=['Vrai', 'Faux', '', '   '], correct_answer='Vrai')
        self.assertEqual(reponse.status_code, 201, reponse.content)
        self.assertEqual(reponse.json()['options'], ['Vrai', 'Faux'])

    def test_la_bonne_reponse_prend_l_orthographe_de_l_option(self):
        """Sinon la correction comparerait deux chaines differentes."""
        reponse = self.creer(options=['Vrai', 'Faux'], correct_answer='  vrai ')
        self.assertEqual(reponse.status_code, 201, reponse.content)
        self.assertEqual(reponse.json()['correct_answer'], 'Vrai')

    def test_les_anciens_formats_sont_refuses(self):
        for ancien in ('TF', 'OPEN'):
            with self.subTest(format=ancien):
                reponse = self.creer(question_kind=ancien)
                self.assertEqual(reponse.status_code, 400)
                self.assertIn('question_kind', self.champs_refuses(reponse))

    def test_le_candidat_recoit_les_options_sans_le_corrige(self):
        enonce = self.client_for(self.agent).get(
            f'/api/v1/evaluations/exams/{self.exam.id}/questions/'
        ).json()['results'][0]
        self.assertEqual(enonce['options'], ['A', 'B', 'C', 'D'])
        self.assertNotIn('correct_answer', enonce)


class ReponseQCMTest(ApiContractTestCase):
    """`submit-answer` n'accepte qu'une option de la question posee."""

    def setUp(self):
        self.candidat = make_user('ASE-2024-0301')
        self.client = self.client_for(self.candidat)
        depart = self.client.post(
            f'/api/v1/evaluations/exams/{self.exam.id}/start-session/'
        )
        self.session_id = depart.json()['id']

    def repondre(self, question_id, texte):
        return self.client.post(
            f'/api/v1/evaluations/sessions/{self.session_id}/submit-answer/',
            {'question': question_id, 'response': texte}, format='json',
        )

    def test_une_option_de_la_question_est_acceptee(self):
        reponse = self.repondre(self.question.id, 'B')
        self.assertEqual(reponse.status_code, 200, reponse.content)
        self.assertEqual(reponse.json()['response'], 'B')

    def test_une_reponse_libre_est_refusee(self):
        reponse = self.repondre(self.question.id, 'je ne sais pas')
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(reponse.json()['error']['options'], ['A', 'B', 'C', 'D'])

    def test_la_reponse_est_enregistree_a_l_orthographe_de_l_option(self):
        """Une casse differente ne doit pas creer une reponse incorrigible."""
        self.assertEqual(self.repondre(self.question.id, ' b ').status_code, 200)
        answer = Answer.objects.get(session_id=self.session_id, question=self.question)
        self.assertEqual(answer.response, 'B')

    def test_une_question_hors_examen_est_refusee(self):
        """Sinon la reponse n'entre dans aucun bareme et bloque la correction."""
        hors_examen = Question.objects.create(
            question_type='GENERAL', text='Hors examen',
            correct_answer='X', options=['X', 'Y'], points=5,
        )
        self.assertEqual(self.repondre(hors_examen.id, 'X').status_code, 404)

    def test_une_question_retiree_de_la_banque_est_refusee(self):
        self.question.is_active = False
        self.question.save(update_fields=['is_active'])
        self.assertEqual(self.repondre(self.question.id, 'A').status_code, 404)


class BaremeDesQuestionsRetireesTest(ApiContractTestCase):
    """Le bareme suit les questions reellement presentees."""

    def test_une_question_retiree_sans_reponse_quitte_le_bareme(self):
        """
        Les questions ouvertes ont ete desactivees par la migration 0003 : si
        elles restaient au bareme, le score de toutes les copies baisserait
        sans qu'aucun candidat ait pu y repondre.
        """
        retiree = Question.objects.create(
            question_type='GENERAL', text='Ancienne question ouverte',
            correct_answer='A', options=['A', 'B'], points=10, is_active=False,
        )
        self.exam.questions.add(retiree)

        session = ExamSession.objects.create(
            exam=self.exam, agent=self.evaluator, session_status='CORRECTING',
        )
        Answer.objects.create(
            session=session, question=self.question, response='A',
            evaluator_score=10, is_correct=True,
        )
        # Bareme = la seule question active (10 points), pas 20.
        self.assertEqual(float(session.compute_score_from_items()), 100.0)

    def test_une_question_retiree_mais_repondue_reste_au_bareme(self):
        """Sinon les points obtenus se rapporteraient a un total trop petit."""
        retiree = Question.objects.create(
            question_type='GENERAL', text='Retiree apres coup',
            correct_answer='A', options=['A', 'B'], points=10, is_active=False,
        )
        self.exam.questions.add(retiree)

        session = ExamSession.objects.create(
            exam=self.exam, agent=self.evaluator, session_status='CORRECTING',
        )
        for question, note in ((self.question, 10), (retiree, 5)):
            Answer.objects.create(
                session=session, question=question, response='A',
                evaluator_score=note, is_correct=True,
            )
        # 15 points sur un bareme de 20.
        self.assertEqual(float(session.compute_score_from_items()), 75.0)
