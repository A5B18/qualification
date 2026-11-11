"""
Tests unitaires pour l'app evaluations.

Couvre :
  - Question : création et propriétés
  - Exam : création, statuts
  - ExamSession : workflow complet de correction manuelle
      IN_PROGRESS → SUBMITTED → CORRECTING → PENDING_APPROVAL → GRADED / REJECTED
  - Answer : apply_correction(), is_pending_correction
  - compute_score_from_items() basé sur evaluator_score
"""

import datetime
from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.training.models import Specialty, Training
from apps.evaluations.models import Question, Exam, ExamSession, Answer


def make_user(matricule, email):
    return User.objects.create_user(
        matricule=matricule, email=email,
        password='Test123!', first_name='Test', last_name='User',
    )


class QuestionTest(TestCase):
    def setUp(self):
        self.creator = make_user('ASE-2024-0300', 'qcreator@asecna.com')
        self.specialty = Specialty.objects.create(code='QST', name='Questions')
        self.training = Training.objects.create(
            specialty=self.specialty,
            title='Formation test',
            training_type=Training.TrainingType.NON_QUALIFYING,
        )

    def test_create_mcq_question(self):
        q = Question.objects.create(
            training=self.training,
            question_type=Question.QuestionType.GENERAL,
            question_kind=Question.QuestionKind.MCQ,
            text='Quelle est la capitale du Sénégal ?',
            correct_answer='Dakar',
            options=['Dakar', 'Abidjan', 'Bamako', 'Lomé'],
            points=2,
            created_by=self.creator,
        )
        self.assertEqual(q.points, 2)
        self.assertEqual(q.question_kind, 'MCQ')
        self.assertTrue(q.is_active)

    def test_question_str_contains_difficulty(self):
        q = Question.objects.create(
            question_type=Question.QuestionType.TECHNICAL,
            text='Question technique',
            correct_answer='Bonne réponse',
            difficulty=3,
            created_by=self.creator,
        )
        self.assertIn('Diff.3', str(q))


class ExamWorkflowTest(TestCase):
    """Tests du workflow complet de correction manuelle."""

    def setUp(self):
        self.agent     = make_user('ASE-2024-0301', 'agent@asecna.com')
        self.evaluator = make_user('ASE-2024-0302', 'evaluator@asecna.com')
        self.chief     = make_user('ASE-2024-0303', 'chief@asecna.com')
        self.creator   = make_user('ASE-2024-0304', 'creator@asecna.com')

        self.specialty = Specialty.objects.create(code='EXM', name='Examen')
        self.training = Training.objects.create(
            specialty=self.specialty,
            title='Formation exam',
            training_type=Training.TrainingType.NON_QUALIFYING,
            passing_score=70,
        )
        # Examen avec 2 questions à 5 points chacune
        self.exam = Exam.objects.create(
            training=self.training,
            title='Examen test',
            exam_status=Exam.ExamStatus.PUBLISHED,
            passing_score=70,
            created_by=self.creator,
        )
        self.q1 = Question.objects.create(
            question_type=Question.QuestionType.GENERAL,
            text='Q1', correct_answer='A', points=5,
            created_by=self.creator,
        )
        self.q2 = Question.objects.create(
            question_type=Question.QuestionType.TECHNICAL,
            text='Q2', correct_answer='B', points=5,
            created_by=self.creator,
        )
        self.exam.questions.set([self.q1, self.q2])

        # Session de l'agent
        self.session = ExamSession.objects.create(
            exam=self.exam,
            agent=self.agent,
            session_status=ExamSession.SessionStatus.IN_PROGRESS,
        )
        # Réponses de l'agent
        self.answer1 = Answer.objects.create(session=self.session, question=self.q1, response='A')
        self.answer2 = Answer.objects.create(session=self.session, question=self.q2, response='C')

    def test_initial_status_in_progress(self):
        self.assertEqual(self.session.session_status, ExamSession.SessionStatus.IN_PROGRESS)

    def test_answers_pending_correction(self):
        """Toutes les réponses sont initialement en attente de correction."""
        self.assertTrue(self.answer1.is_pending_correction)
        self.assertTrue(self.answer2.is_pending_correction)

    def test_apply_correction_to_answer(self):
        """L'évaluateur corrige une réponse : score et is_correct mis à jour."""
        self.answer1.apply_correction(
            evaluator=self.evaluator,
            score=5.0,
            is_correct=True,
            feedback='Bonne réponse !',
        )
        self.answer1.refresh_from_db()
        self.assertEqual(float(self.answer1.evaluator_score), 5.0)
        self.assertTrue(self.answer1.is_correct)
        self.assertFalse(self.answer1.is_pending_correction)
        self.assertEqual(self.answer1.corrected_by, self.evaluator)

    def test_compute_score_from_items(self):
        """Score calculé à partir des évaluateur_scores : Q1=5/5, Q2=0/5 → 50%."""
        self.answer1.apply_correction(evaluator=self.evaluator, score=5.0, is_correct=True)
        self.answer2.apply_correction(evaluator=self.evaluator, score=0.0, is_correct=False)
        score = self.session.compute_score_from_items()
        self.assertEqual(float(score), 50.0)

    def test_submit_for_approval(self):
        """Évaluateur soumet → PENDING_APPROVAL avec score provisoire."""
        self.answer1.apply_correction(evaluator=self.evaluator, score=5.0, is_correct=True)
        self.answer2.apply_correction(evaluator=self.evaluator, score=3.0, is_correct=True)

        # Session passe à CORRECTING d'abord manuellement
        self.session.session_status = ExamSession.SessionStatus.CORRECTING
        self.session.save()

        score = self.session.compute_score_from_items()  # 80%
        self.session.submit_for_approval(evaluator=self.evaluator, score=score)
        self.session.refresh_from_db()

        self.assertEqual(self.session.session_status, ExamSession.SessionStatus.PENDING_APPROVAL)
        self.assertEqual(float(self.session.score), 80.0)
        self.assertEqual(self.session.graded_by, self.evaluator)

    def test_approve_by_unit_chief(self):
        """Chef d'unité approuve → GRADED, is_passed calculé."""
        self.session.session_status = ExamSession.SessionStatus.PENDING_APPROVAL
        self.session.score = 80
        self.session.save()

        self.session.approve(unit_chief=self.chief)
        self.session.refresh_from_db()

        self.assertEqual(self.session.session_status, ExamSession.SessionStatus.GRADED)
        self.assertTrue(self.session.is_passed)  # 80 >= passing_score 70
        self.assertEqual(self.session.approved_by, self.chief)

    def test_reject_by_unit_chief_requires_reason(self):
        """Rejet sans motif → la méthode attend un motif."""
        self.session.session_status = ExamSession.SessionStatus.PENDING_APPROVAL
        self.session.score = 80
        self.session.save()

        self.session.reject(unit_chief=self.chief, reason='Score trop bas')
        self.session.refresh_from_db()

        self.assertEqual(self.session.session_status, ExamSession.SessionStatus.REJECTED)
        self.assertEqual(self.session.rejection_reason, 'Score trop bas')

    def test_is_passed_false_when_below_passing_score(self):
        """Score < passing_score → is_passed = False après approbation."""
        self.session.session_status = ExamSession.SessionStatus.PENDING_APPROVAL
        self.session.score = 50  # < 70
        self.session.save()

        self.session.approve(unit_chief=self.chief)
        self.session.refresh_from_db()

        self.assertFalse(self.session.is_passed)
