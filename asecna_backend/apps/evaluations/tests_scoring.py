"""Verifie le calcul du score d'une session d'examen (questions non repondues)."""

import datetime
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.training.models import Specialty, Training
from apps.evaluations.models import Question, Exam, ExamSession, Answer

User = get_user_model()


class ScoreComputationTest(TestCase):
    def setUp(self):
        self.agent = User.objects.create_user(
            matricule='ASE-2030-0001', email='a@asecna.org',
            first_name='A', last_name='B', password='Passw0rd!2024',
        )
        spec = Specialty.objects.create(code='SPX', name='Spec')
        training = Training.objects.create(
            title='T', specialty=spec, duration_days=5, passing_score=70,
        )
        self.exam = Exam.objects.create(
            title='Examen 4 questions', training=training, exam_status='PUBLISHED',
        )
        # 4 questions de 10 points : bareme total = 40
        self.questions = [
            Question.objects.create(
                question_type='TECHNICAL', text=f'Q{i}', correct_answer='x', points=10,
            )
            for i in range(4)
        ]
        self.exam.questions.add(*self.questions)
        self.session = ExamSession.objects.create(
            exam=self.exam, agent=self.agent, session_status='SUBMITTED',
        )

    def test_questions_non_repondues_comptent_pour_zero(self):
        """
        L'agent ne repond qu'a 1 question sur 4 et la reussit.

        Avant correction, le bareme etait celui des seules reponses presentes :
        10/10 -> 100/100. Le bareme correct est celui de l'examen : 10/40 -> 25.
        """
        a = Answer.objects.create(
            session=self.session, question=self.questions[0], response='x',
        )
        a.apply_correction(evaluator=self.agent, score=10, is_correct=True)

        score = self.session.compute_score_from_items()
        self.assertEqual(score, Decimal('25.00'),
                         f'1 bonne reponse sur 4 doit donner 25/100, obtenu {score}')

    def test_toutes_les_reponses_justes_donnent_100(self):
        for q in self.questions:
            a = Answer.objects.create(session=self.session, question=q, response='x')
            a.apply_correction(evaluator=self.agent, score=10, is_correct=True)
        self.assertEqual(self.session.compute_score_from_items(), Decimal('100.00'))

    def test_scores_partiels(self):
        # 10 + 5 + 0 + (non repondue) = 15 / 40 = 37.5
        for q, sc in zip(self.questions[:3], [10, 5, 0]):
            a = Answer.objects.create(session=self.session, question=q, response='x')
            a.apply_correction(evaluator=self.agent, score=sc, is_correct=sc > 0)
        self.assertEqual(self.session.compute_score_from_items(), Decimal('37.50'))

    def test_examen_sans_questions_rattachees(self):
        """Repli sur le bareme des reponses presentes si l'examen est vide."""
        exam = Exam.objects.create(title='Vide', exam_status='PUBLISHED')
        session = ExamSession.objects.create(
            exam=exam, agent=self.agent, session_status='SUBMITTED',
        )
        a = Answer.objects.create(
            session=session, question=self.questions[0], response='x',
        )
        a.apply_correction(evaluator=self.agent, score=7, is_correct=True)
        self.assertEqual(session.compute_score_from_items(), Decimal('70.00'))

    def test_aucune_reponse(self):
        self.assertEqual(self.session.compute_score_from_items(), Decimal('0.00'))

    def test_rejet_remet_is_passed_a_null(self):
        chief = User.objects.create_user(
            matricule='ASE-2030-0002', email='c@asecna.org',
            first_name='C', last_name='D', password='Passw0rd!2024',
        )
        for q in self.questions:
            a = Answer.objects.create(session=self.session, question=q, response='x')
            a.apply_correction(evaluator=self.agent, score=10, is_correct=True)
        self.session.submit_for_approval(
            evaluator=self.agent, score=self.session.compute_score_from_items(),
        )
        self.session.approve(unit_chief=chief)
        self.assertTrue(self.session.is_passed)
        self.session.session_status = ExamSession.SessionStatus.PENDING_APPROVAL
        self.session.save(update_fields=['session_status'])
        self.session.reject(unit_chief=chief, reason='bareme a revoir')
        self.session.refresh_from_db()
        self.assertIsNone(self.session.is_passed)
        self.assertEqual(self.session.session_status, ExamSession.SessionStatus.REJECTED)
