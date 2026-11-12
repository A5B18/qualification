"""
Registre d'approbation transversal (`apps.workflows`).

Avant cette intégration, `ApprovalWorkflow` n'était alimenté que par
`seed_demo` : aucun module ne l'écrivait, et la liste « en attente » de
l'approbateur ne reflétait rien de réel.

Les tests ci-dessous vérifient que les trois modules décisionnaires y
inscrivent bien leurs transitions, que l'invariant « une ligne par objet »
tient, et que le registre est cloisonné.
"""

from django.contrib.contenttypes.models import ContentType

from apps.evaluations.models import ExamSession
from apps.mentoring.models import MentoringRecord
from apps.reports.models import Report
from apps.workflows.models import ApprovalWorkflow

from .test_api_contract import ApiContractTestCase, make_user


def ledger_for(obj):
    """Ligne de registre d'un objet métier, ou None."""
    return ApprovalWorkflow.objects.filter(
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_id=obj.pk,
    ).first()


class ReportLedgerTest(ApiContractTestCase):
    """Un rapport décidé laisse une trace au registre."""

    def test_la_soumission_inscrit_le_rapport_au_registre(self):
        self.assertIsNone(ledger_for(self.report),
                          "Un brouillon n'a rien à faire au registre.")

        response = self.client_for(self.chief).post(
            f'/api/v1/reports/{self.report.id}/submit/'
        )
        self.assertEqual(response.status_code, 200, response.content)

        entry = ledger_for(self.report)
        self.assertIsNotNone(entry, 'La soumission doit créer la ligne.')
        self.assertEqual(entry.workflow_status, 'SUBMITTED')
        self.assertEqual(entry.submitted_by, self.chief)
        self.assertIsNotNone(entry.submitted_at)

    def test_l_approbation_est_enregistree_avec_son_avis(self):
        approbateur = self.client_for(self.approver)
        self.client_for(self.chief).post(f'/api/v1/reports/{self.report.id}/submit/')

        response = approbateur.post(
            f'/api/v1/reports/{self.report.id}/approve/',
            {'opinion': 'Avis favorable.'}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)

        entry = ledger_for(self.report)
        self.assertEqual(entry.workflow_status, 'APPROVED')
        self.assertEqual(entry.approver, self.approver)
        self.assertEqual(entry.approver_comment, 'Avis favorable.')
        self.assertIsNotNone(entry.approved_at)

    def test_le_rejet_est_enregistre_avec_son_motif(self):
        self.client_for(self.chief).post(f'/api/v1/reports/{self.report.id}/submit/')
        self.client_for(self.approver).post(
            f'/api/v1/reports/{self.report.id}/reject/',
            {'opinion': 'Conclusion absente.'}, format='json',
        )
        entry = ledger_for(self.report)
        self.assertEqual(entry.workflow_status, 'REJECTED')
        self.assertEqual(entry.approver_comment, 'Conclusion absente.')
        self.assertIsNotNone(entry.rejected_at)
        self.assertIsNone(entry.approved_at)

    def test_un_objet_n_a_qu_une_ligne_de_registre(self):
        """
        L'invariant est garanti en base par `unique_workflow_per_object` ;
        rejouer une soumission met la ligne à jour au lieu d'en empiler une.
        """
        chef = self.client_for(self.chief)
        chef.post(f'/api/v1/reports/{self.report.id}/submit/')
        self.client_for(self.approver).post(
            f'/api/v1/reports/{self.report.id}/reject/',
            {'opinion': 'À reprendre.'}, format='json',
        )
        # Le rapport repart en soumission après correction
        self.report.refresh_from_db()
        self.report.report_status = Report.ReportStatus.DRAFT
        self.report.save(update_fields=['report_status'])
        chef.post(f'/api/v1/reports/{self.report.id}/submit/')

        content_type = ContentType.objects.get_for_model(Report)
        self.assertEqual(
            ApprovalWorkflow.objects.filter(
                content_type=content_type, object_id=self.report.id,
            ).count(),
            1,
        )
        entry = ledger_for(self.report)
        self.assertEqual(entry.workflow_status, 'SUBMITTED')
        self.assertIsNone(entry.rejected_at,
                          'Une resoumission repart d’une ardoise propre.')


class MentoringLedgerTest(ApiContractTestCase):
    """Une fiche de mentorat est décidée par le chef d'unité."""

    def test_soumission_puis_approbation(self):
        mentor = self.client_for(self.mentor)
        response = mentor.post(
            f'/api/v1/mentoring/{self.mentoring.id}/submit/',
            {'unit_chief': self.chief.id}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)

        entry = ledger_for(self.mentoring)
        self.assertEqual(entry.workflow_status, 'SUBMITTED')
        self.assertEqual(entry.submitted_by, self.mentor)
        self.assertEqual(entry.unit_chief, self.chief,
                         "Le décideur est connu dès la soumission.")

        self.client_for(self.chief).post(
            f'/api/v1/mentoring/{self.mentoring.id}/approve/',
            {'opinion': 'Parcours satisfaisant.'}, format='json',
        )
        entry.refresh_from_db()
        self.assertEqual(entry.workflow_status, 'APPROVED')
        # L'avis du chef se range dans son propre champ, pas dans celui de
        # l'approbateur.
        self.assertEqual(entry.unit_chief_comment, 'Parcours satisfaisant.')
        self.assertEqual(entry.approver_comment, '')

    def test_rejet_enregistre(self):
        self.client_for(self.mentor).post(
            f'/api/v1/mentoring/{self.mentoring.id}/submit/',
            {'unit_chief': self.chief.id}, format='json',
        )
        self.client_for(self.chief).post(
            f'/api/v1/mentoring/{self.mentoring.id}/reject/',
            {'opinion': 'Objectifs trop vagues.'}, format='json',
        )
        entry = ledger_for(self.mentoring)
        self.assertEqual(entry.workflow_status, 'REJECTED')
        self.assertEqual(entry.unit_chief_comment, 'Objectifs trop vagues.')


class ExamCorrectionLedgerTest(ApiContractTestCase):
    """La correction d'examen passe elle aussi par le registre."""

    def _corriger_entierement(self):
        evaluateur = self.client_for(self.evaluator)
        evaluateur.post(
            f'/api/v1/evaluations/sessions/{self.session.id}/grade-answer/',
            {'answer_id': self.answer.id, 'is_correct': True, 'evaluator_score': 10},
            format='json',
        )
        return evaluateur

    def test_la_soumission_au_chef_inscrit_la_session(self):
        evaluateur = self._corriger_entierement()
        response = evaluateur.post(
            f'/api/v1/evaluations/sessions/{self.session.id}/submit-for-approval/'
        )
        self.assertEqual(response.status_code, 200, response.content)

        entry = ledger_for(self.session)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.workflow_status, 'SUBMITTED')
        self.assertEqual(entry.submitted_by, self.evaluator)

    def test_l_approbation_du_chef_cloture_la_ligne(self):
        evaluateur = self._corriger_entierement()
        evaluateur.post(
            f'/api/v1/evaluations/sessions/{self.session.id}/submit-for-approval/'
        )
        self.client_for(self.chief).post(
            f'/api/v1/evaluations/sessions/{self.session.id}/approve/'
        )
        entry = ledger_for(self.session)
        self.assertEqual(entry.workflow_status, 'APPROVED')
        self.assertEqual(entry.unit_chief, self.chief)

    def test_le_rejet_conserve_le_motif(self):
        evaluateur = self._corriger_entierement()
        evaluateur.post(
            f'/api/v1/evaluations/sessions/{self.session.id}/submit-for-approval/'
        )
        self.client_for(self.chief).post(
            f'/api/v1/evaluations/sessions/{self.session.id}/reject/',
            {'reason': 'Barème mal appliqué.'}, format='json',
        )
        entry = ledger_for(self.session)
        self.assertEqual(entry.workflow_status, 'REJECTED')
        self.assertEqual(entry.unit_chief_comment, 'Barème mal appliqué.')


class LedgerApiTest(ApiContractTestCase):
    """Ce que l'écran d'approbation lit réellement."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Un rapport et une fiche de mentorat en attente, via l'API
        cls.autre_rapport = Report.objects.create(
            report_type='ASSESSMENT', agent=cls.agent, created_by=cls.chief,
            title='Bilan semestriel', content='Contenu',
        )

    def _soumettre_les_deux(self):
        chef = self.client_for(self.chief)
        chef.post(f'/api/v1/reports/{self.report.id}/submit/')
        chef.post(f'/api/v1/reports/{self.autre_rapport.id}/submit/')
        self.client_for(self.mentor).post(
            f'/api/v1/mentoring/{self.mentoring.id}/submit/',
            {'unit_chief': self.chief.id}, format='json',
        )

    def test_la_liste_en_attente_couvre_plusieurs_modules(self):
        self._soumettre_les_deux()
        response = self.client_for(self.approver).get('/api/v1/workflows/pending/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['count'], 3)
        modules = {item['module'] for item in body['results']}
        self.assertEqual(modules, {'report', 'mentoringrecord'})

    def test_chaque_ligne_dit_ce_qui_est_soumis_et_sur_qui(self):
        """
        Sans ces champs, l'écran annonçait « N workflows en attente » sans
        pouvoir nommer un seul d'entre eux.
        """
        self._soumettre_les_deux()
        body = self.client_for(self.approver).get('/api/v1/workflows/pending/').json()
        rapport = next(i for i in body['results']
                       if i['module'] == 'report' and i['target']['label'] == 'Rapport')

        self.assertEqual(rapport['module_label'], 'Rapport')
        self.assertEqual(rapport['target']['id'], self.report.id)
        self.assertEqual(rapport['target']['agent']['matricule'], self.agent.matricule)
        self.assertEqual(rapport['target']['route'], '/reports')
        self.assertFalse(rapport['target']['deleted'])

    def test_une_correction_renvoie_vers_son_ecran(self):
        evaluateur = self.client_for(self.evaluator)
        evaluateur.post(
            f'/api/v1/evaluations/sessions/{self.session.id}/grade-answer/',
            {'answer_id': self.answer.id, 'is_correct': True, 'evaluator_score': 10},
            format='json',
        )
        evaluateur.post(
            f'/api/v1/evaluations/sessions/{self.session.id}/submit-for-approval/'
        )
        body = self.client_for(self.chief).get(
            '/api/v1/workflows/pending/?module=examsession'
        ).json()
        self.assertEqual(body['count'], 1)
        self.assertEqual(body['results'][0]['target']['route'],
                         f'/evaluations/sessions/{self.session.id}')

    def test_filtre_par_module(self):
        self._soumettre_les_deux()
        body = self.client_for(self.approver).get(
            '/api/v1/workflows/?module=mentoringrecord'
        ).json()
        self.assertEqual(body['count'], 1)
        self.assertEqual(body['results'][0]['module'], 'mentoringrecord')

    def test_un_agent_ne_voit_que_ses_propres_soumissions(self):
        """
        Le registre servait toute la table à n'importe quel utilisateur
        authentifié : un agent y lisait les soumissions de ses collègues.
        """
        self._soumettre_les_deux()
        body = self.client_for(self.agent).get('/api/v1/workflows/').json()
        self.assertEqual(body['count'], 0,
                         "L'agent n'a rien soumis : il ne doit rien voir.")

        body_chef = self.client_for(self.chief).get('/api/v1/workflows/').json()
        self.assertEqual(body_chef['count'], 3)

    def test_un_agent_ne_peut_pas_approuver(self):
        self._soumettre_les_deux()
        entry = ledger_for(self.report)
        self.assertEqual(
            self.client_for(self.agent).post(
                f'/api/v1/workflows/{entry.id}/approve/'
            ).status_code,
            403,
        )

    def test_la_ligne_survit_a_la_suppression_de_l_objet(self):
        """
        Le registre est une trace : il ne disparaît pas avec l'objet. Il doit
        le signaler plutôt que de faire échouer la sérialisation.
        """
        self._soumettre_les_deux()
        rapport_id = self.autre_rapport.id
        self.autre_rapport.delete()

        body = self.client_for(self.approver).get('/api/v1/workflows/').json()
        orpheline = next(
            (i for i in body['results']
             if i['module'] == 'report' and i['object_id'] == rapport_id),
            None,
        )
        self.assertIsNotNone(orpheline)
        self.assertTrue(orpheline['target']['deleted'])
        self.assertEqual(orpheline['target']['label'], 'Objet supprimé')


class SeedLedgerConsistencyTest(ApiContractTestCase):
    """Le registre doit refléter l'état réel, pas un sous-ensemble arbitraire."""

    def test_aucun_brouillon_au_registre(self):
        self.client_for(self.chief).post(f'/api/v1/reports/{self.report.id}/submit/')
        for entry in ApprovalWorkflow.objects.all():
            target = entry.content_object
            if isinstance(target, Report):
                self.assertNotEqual(target.report_status, 'DRAFT')
            elif isinstance(target, MentoringRecord):
                self.assertNotEqual(target.mentoring_status, 'DRAFT')
            elif isinstance(target, ExamSession):
                self.assertIn(target.session_status,
                              ('PENDING_APPROVAL', 'GRADED', 'REJECTED'))
