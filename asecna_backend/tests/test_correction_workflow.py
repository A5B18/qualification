"""
Tests du workflow de correction tel qu'il est reellement parcouru par
l'interface, et des filtres que les ecrans de detail exigent.

Pourquoi ce fichier : le workflow en 4 etapes etait couvert cote modeles, mais
aucun test ne verifiait qu'un evaluateur pouvait le derouler *via l'API*. Il ne
le pouvait pas : `grade-answer` attend un `answer_id` et aucun endpoint ne
listait les reponses d'une session. La session restait donc bloquee en
SUBMITTED des que l'on sortait du shell Django.

Les tests ci-dessous suivent le parcours exact des ecrans :
  copie -> correction reponse par reponse -> soumission -> approbation.
"""

import datetime

from django.core import mail
from django.test import override_settings

from apps.agents.models import AgentSkill, AgentCertification, PerformanceIndicator
from apps.evaluations.models import Question, Exam, Answer
from apps.training.models import Course

from .test_api_contract import ApiContractTestCase, make_user


class SessionAnswersEndpointTest(ApiContractTestCase):
    """GET /evaluations/sessions/{id}/answers/ — la copie de l'agent."""

    def test_evaluateur_recoit_la_copie_avec_le_corrige(self):
        response = self.client_for(self.evaluator).get(
            f'/api/v1/evaluations/sessions/{self.session.id}/answers/'
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['count'], 1)
        detail = body['results'][0]['question_detail']
        self.assertEqual(detail['correct_answer'], 'A',
                         "L'evaluateur doit voir la reponse attendue pour noter.")
        self.assertEqual(body['pending_correction'], 1)

    def test_agent_relit_sa_copie_sans_le_corrige(self):
        response = self.client_for(self.agent).get(
            f'/api/v1/evaluations/sessions/{self.session.id}/answers/'
        )
        self.assertEqual(response.status_code, 200)
        detail = response.json()['results'][0]['question_detail']
        self.assertNotIn(
            'correct_answer', detail,
            "Un agent qui relit sa copie ne doit pas y decouvrir le corrige.",
        )

    def test_un_agent_ne_lit_pas_la_copie_d_un_autre(self):
        autre = make_user('ASE-2024-0077')
        response = self.client_for(autre).get(
            f'/api/v1/evaluations/sessions/{self.session.id}/answers/'
        )
        self.assertEqual(response.status_code, 404,
                         'Cloisonnement : la session appartient a un autre agent.')

    def test_les_questions_sans_reponse_sont_signalees(self):
        """
        Elles comptent pour 0 dans le score : l'ecran de correction doit les
        montrer, sinon l'evaluateur croit avoir tout corrige.
        """
        oubliee = Question.objects.create(
            question_type='GENERAL', text='Jamais traitee', correct_answer='B', points=5,
        )
        self.exam.questions.add(oubliee)

        body = self.client_for(self.evaluator).get(
            f'/api/v1/evaluations/sessions/{self.session.id}/answers/'
        ).json()
        self.assertEqual([q['text'] for q in body['unanswered']], ['Jamais traitee'])


class CorrectionWorkflowThroughApiTest(ApiContractTestCase):
    """Le parcours complet, dans l'ordre ou les ecrans l'enchainent."""

    def test_de_submitted_a_graded_en_passant_par_l_api(self):
        evaluateur = self.client_for(self.evaluator)
        chef = self.client_for(self.chief)
        url = f'/api/v1/evaluations/sessions/{self.session.id}'

        # 1. L'evaluateur lit la copie pour recuperer l'identifiant de reponse
        copie = evaluateur.get(f'{url}/answers/').json()
        answer_id = copie['results'][0]['id']

        # 2. Il corrige — la session doit basculer en CORRECTING
        grade = evaluateur.post(f'{url}/grade-answer/', {
            'answer_id': answer_id, 'is_correct': True,
            'evaluator_score': 8, 'feedback': 'Correct mais incomplet.',
        }, format='json')
        self.assertEqual(grade.status_code, 200, grade.content)
        self.session.refresh_from_db()
        self.assertEqual(self.session.session_status, 'CORRECTING')

        # 3. Soumission au chef — le score est calcule sur le bareme complet
        soumission = evaluateur.post(f'{url}/submit-for-approval/')
        self.assertEqual(soumission.status_code, 200, soumission.content)
        self.assertEqual(soumission.json()['session_status'], 'PENDING_APPROVAL')
        self.assertEqual(float(soumission.json()['score']), 80.0,
                         '8 points sur un bareme de 10 -> 80/100')

        # 4. Approbation du chef : le score devient officiel
        approbation = chef.post(f'{url}/approve/')
        self.assertEqual(approbation.status_code, 200, approbation.content)
        body = approbation.json()
        self.assertEqual(body['session_status'], 'GRADED')
        self.assertTrue(body['is_passed'], 'Seuil de l\'examen : 70')

    def test_les_compteurs_de_correction_suivent_l_avancement(self):
        """
        Le bouton « Soumettre » ne doit s'afficher que lorsque tout est
        corrige : l'ecran a besoin de ces compteurs pour le savoir.
        """
        seconde = Question.objects.create(
            question_type='GENERAL', text='Q2', correct_answer='B', points=10,
        )
        self.exam.questions.add(seconde)
        Answer.objects.create(session=self.session, question=seconde, response='B')

        evaluateur = self.client_for(self.evaluator)
        avant = evaluateur.get(
            f'/api/v1/evaluations/sessions/{self.session.id}/'
        ).json()
        self.assertEqual(avant['answers_count'], 2)
        self.assertEqual(avant['corrected_count'], 0)
        self.assertEqual(avant['pending_correction_count'], 2)

        evaluateur.post(
            f'/api/v1/evaluations/sessions/{self.session.id}/grade-answer/',
            {'answer_id': self.answer.id, 'is_correct': True, 'evaluator_score': 10},
            format='json',
        )
        apres = evaluateur.get(
            f'/api/v1/evaluations/sessions/{self.session.id}/'
        ).json()
        self.assertEqual(apres['corrected_count'], 1)
        self.assertEqual(apres['pending_correction_count'], 1)

    def test_soumettre_une_correction_incomplete_est_refuse(self):
        seconde = Question.objects.create(
            question_type='GENERAL', text='Q2', correct_answer='B', points=10,
        )
        self.exam.questions.add(seconde)
        Answer.objects.create(session=self.session, question=seconde, response='B')

        evaluateur = self.client_for(self.evaluator)
        evaluateur.post(
            f'/api/v1/evaluations/sessions/{self.session.id}/grade-answer/',
            {'answer_id': self.answer.id, 'is_correct': True, 'evaluator_score': 10},
            format='json',
        )
        refus = evaluateur.post(
            f'/api/v1/evaluations/sessions/{self.session.id}/submit-for-approval/'
        )
        self.assertEqual(refus.status_code, 400)
        self.assertIn('1 réponse', refus.json()['error']['message'])


class AgentComposesExamTest(ApiContractTestCase):
    """L'agent passe l'epreuve : demarrer, repondre, rendre sa copie."""

    def test_parcours_de_composition(self):
        agent = make_user('ASE-2024-0078')
        client = self.client_for(agent)

        # Les enonces, sans le corrige
        questions = client.get(
            f'/api/v1/evaluations/exams/{self.exam.id}/questions/'
        )
        self.assertEqual(questions.status_code, 200)
        enonce = questions.json()['results'][0]
        self.assertNotIn('correct_answer', enonce,
                         'Le corrige ne doit jamais partir vers le candidat.')

        # Demarrage de la session
        depart = client.post(f'/api/v1/evaluations/exams/{self.exam.id}/start-session/')
        self.assertIn(depart.status_code, (200, 201), depart.content)
        session_id = depart.json()['id']

        # Reponse puis remise de copie
        reponse = client.post(
            f'/api/v1/evaluations/sessions/{session_id}/submit-answer/',
            {'question': enonce['id'], 'response': 'A'}, format='json',
        )
        self.assertEqual(reponse.status_code, 200, reponse.content)

        remise = client.post(f'/api/v1/evaluations/sessions/{session_id}/finalize/')
        self.assertEqual(remise.status_code, 200, remise.content)
        self.assertEqual(remise.json()['session_status'], 'SUBMITTED')

    def test_l_evaluateur_voit_le_corrige_dans_les_enonces(self):
        questions = self.client_for(self.evaluator).get(
            f'/api/v1/evaluations/exams/{self.exam.id}/questions/'
        ).json()
        self.assertEqual(questions['results'][0]['correct_answer'], 'A')


class ExamPublicationTest(ApiContractTestCase):
    """Publication d'un examen depuis l'ecran de composition."""

    def test_un_examen_sans_question_ne_peut_pas_etre_publie(self):
        vide = Exam.objects.create(
            title='Vide', training=self.training, created_by=self.evaluator,
            exam_status='DRAFT',
        )
        refus = self.client_for(self.evaluator).post(
            f'/api/v1/evaluations/exams/{vide.id}/publish/'
        )
        self.assertEqual(refus.status_code, 400)
        vide.refresh_from_db()
        self.assertEqual(vide.exam_status, 'DRAFT')

    def test_publier_puis_depublier(self):
        brouillon = Exam.objects.create(
            title='Brouillon', training=self.training, created_by=self.evaluator,
            exam_status='DRAFT',
        )
        brouillon.questions.add(self.question)
        evaluateur = self.client_for(self.evaluator)

        publie = evaluateur.post(f'/api/v1/evaluations/exams/{brouillon.id}/publish/')
        self.assertEqual(publie.status_code, 200, publie.content)
        self.assertEqual(publie.json()['exam_status'], 'PUBLISHED')

        retire = evaluateur.post(f'/api/v1/evaluations/exams/{brouillon.id}/unpublish/')
        self.assertEqual(retire.json()['exam_status'], 'DRAFT')

    def test_un_agent_ne_publie_pas(self):
        self.assertEqual(
            self.client_for(self.agent).post(
                f'/api/v1/evaluations/exams/{self.exam.id}/publish/'
            ).status_code,
            403,
        )


class AgentDetailFiltersTest(ApiContractTestCase):
    """
    `?agent=` sur les competences, certifications et performances.

    Sans ce filtre, les onglets de la fiche agent recevaient la table entiere
    et devaient trier dans le navigateur — avec une pagination qui tronquait
    avant le tri.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.autre = make_user('ASE-2024-0079')
        for agent, nom in ((cls.agent, 'Phraseologie'), (cls.autre, 'Radar')):
            AgentSkill.objects.create(agent=agent, name=nom, level=3)
            AgentCertification.objects.create(
                agent=agent, name=f'Cert {nom}',
                issue_date=datetime.date(2024, 1, 1),
            )
            PerformanceIndicator.objects.create(
                agent=agent, year=2024, score=80, evaluator=cls.evaluator,
            )

    def test_filtre_par_agent_sur_les_trois_ressources(self):
        client = self.client_for(self.admin)
        for ressource, attendu in (
            ('skills', 'Phraseologie'),
            ('certifications', 'Cert Phraseologie'),
        ):
            response = client.get(f'/api/v1/agents/{ressource}/?agent={self.agent.id}')
            self.assertEqual(response.status_code, 200)
            noms = [item['name'] for item in response.json()['results']]
            self.assertEqual(noms, [attendu],
                             f'{ressource} doit se limiter a l\'agent demande.')

        perf = client.get(f'/api/v1/agents/performances/?agent={self.agent.id}')
        self.assertEqual(perf.json()['count'], 1)

    def test_sans_filtre_l_admin_voit_tout(self):
        response = self.client_for(self.admin).get('/api/v1/agents/skills/')
        self.assertEqual(response.json()['count'], 2)


class CourseFiltersTest(ApiContractTestCase):
    """Onglet « Cours » : filtres par formation et par etat de publication."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.publie = Course.objects.create(
            training=cls.training, instructor=cls.instructor,
            title='Cours publie', content='...', is_published=True,
        )
        cls.brouillon = Course.objects.create(
            training=cls.training, instructor=cls.instructor,
            title='Cours brouillon', content='...', is_published=False,
        )

    def test_un_agent_ne_voit_que_les_cours_publies(self):
        response = self.client_for(self.agent).get('/api/v1/training/courses/')
        titres = [c['title'] for c in response.json()['results']]
        self.assertEqual(titres, ['Cours publie'])

    def test_filtre_is_published_pour_l_instructeur(self):
        client = self.client_for(self.instructor)
        brouillons = client.get('/api/v1/training/courses/?is_published=false').json()
        self.assertEqual([c['title'] for c in brouillons['results']], ['Cours brouillon'])

    def test_filtre_par_formation(self):
        response = self.client_for(self.admin).get(
            f'/api/v1/training/courses/?training={self.training.id}'
        )
        self.assertEqual(response.json()['count'], 2)

    def test_publier_et_depublier_un_cours(self):
        client = self.client_for(self.instructor)
        publie = client.post(f'/api/v1/training/courses/{self.brouillon.id}/publish/')
        self.assertEqual(publie.status_code, 200, publie.content)
        self.assertTrue(publie.json()['is_published'])

        retire = client.post(f'/api/v1/training/courses/{self.brouillon.id}/unpublish/')
        self.assertFalse(retire.json()['is_published'])


class ResetPasswordDeliveryTest(ApiContractTestCase):
    """
    Le mot de passe temporaire ne doit plus transiter systematiquement dans la
    reponse HTTP : il s'y retrouvait journalise, mis en cache et conserve dans
    l'historique Swagger.
    """

    def test_le_mot_de_passe_part_par_courriel_et_pas_dans_la_reponse(self):
        mail.outbox = []
        response = self.client_for(self.admin).post(
            f'/api/v1/auth/users/{self.agent.id}/reset-password/'
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['delivered_by_email'])
        self.assertNotIn('temp_password', body)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.agent.email, mail.outbox[0].to)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_repli_si_le_courriel_ne_peut_pas_etre_achemine(self):
        """
        En developpement (backend console) personne ne lit la sortie standard :
        l'administrateur doit pouvoir transmettre le mot de passe a la main.
        """
        response = self.client_for(self.admin).post(
            f'/api/v1/auth/users/{self.agent.id}/reset-password/'
        )
        body = response.json()
        self.assertFalse(body['delivered_by_email'])
        self.assertIn('temp_password', body)

    def test_le_nouveau_mot_de_passe_fonctionne(self):
        self.client_for(self.admin).post(
            f'/api/v1/auth/users/{self.agent.id}/reset-password/'
        )
        self.agent.refresh_from_db()
        self.assertFalse(self.agent.check_password('Passw0rd!2024'),
                         "L'ancien mot de passe ne doit plus ouvrir le compte.")

    def test_un_chef_d_unite_ne_reinitialise_pas(self):
        self.assertEqual(
            self.client_for(self.chief).post(
                f'/api/v1/auth/users/{self.agent.id}/reset-password/'
            ).status_code,
            403,
        )


class QuestionBankFiltersTest(ApiContractTestCase):
    """Banque de questions : filtres de l'ecran de composition d'examen."""

    def test_filtre_par_examen(self):
        hors_examen = Question.objects.create(
            question_type='GENERAL', text='Hors examen', correct_answer='Z', points=5,
        )
        response = self.client_for(self.evaluator).get(
            f'/api/v1/evaluations/questions/?exam={self.exam.id}'
        )
        textes = [q['text'] for q in response.json()['results']]
        self.assertIn('Question ?', textes)
        self.assertNotIn(hors_examen.text, textes)

    def test_recherche_plein_texte(self):
        Question.objects.create(
            question_type='GENERAL', text='Separation radar minimale',
            correct_answer='5NM', points=5,
        )
        response = self.client_for(self.evaluator).get(
            '/api/v1/evaluations/questions/?search=radar'
        )
        self.assertEqual(response.json()['count'], 1)

    def test_un_agent_ne_cree_pas_de_question(self):
        self.assertEqual(
            self.client_for(self.agent).post('/api/v1/evaluations/questions/', {
                'question_type': 'GENERAL', 'text': 'T', 'correct_answer': 'A', 'points': 1,
            }, format='json').status_code,
            403,
        )
