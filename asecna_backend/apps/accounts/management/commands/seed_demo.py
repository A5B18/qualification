"""
Jeu de données de démonstration couvrant TOUTES les fonctionnalités.

    python manage.py seed_demo --settings=config.settings.development
    python manage.py seed_demo --reset --settings=config.settings.development

Objectif : qu'aucun écran de l'application ne soit vide et que chaque état de
chaque workflow soit représenté, afin de pouvoir dérouler le guide de tests
(GUIDE_DE_TESTS.md) de bout en bout sans rien saisir à la main.

La commande est idempotente : elle peut être relancée sans créer de doublons.
`--reset` purge au préalable les données métier (les comptes et le référentiel
sont conservés, puis remis à jour).
"""

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AgentProfile, AgentStatus, FunctionalRole, UserRole
from apps.agents.models import AgentCertification, AgentSkill, PerformanceIndicator
from apps.arcep.models import ARCEPBook, ARCEPEntry, ARCEPSignature
from apps.evaluations.models import Answer, Exam, ExamSession, Question
from apps.mentoring.models import MentoringRecord
from apps.probation.models import ProbationPeriod
from apps.reports.models import Report
from apps.training.models import (
    Course, Internship, QualificationMaintenance, Specialty, Training,
)
from apps.units.models import Unit
from apps.workflows.models import ApprovalWorkflow

User = get_user_model()

TODAY = datetime.date.today()
PWD_ADMIN = 'Admin2024'
PWD_CHEF = 'Chef@2024!'
PWD_MENTOR = 'Mentor@2024!'
PWD_EVAL = 'Eval@2024!'
PWD_INSTR = 'Instr@2024!'
PWD_APPRO = 'Appro@2024!'
PWD_AGENT = 'Agent@2024!'


def d(days):
    """Date relative à aujourd'hui."""
    return TODAY + datetime.timedelta(days=days)


class Command(BaseCommand):
    help = "Crée un jeu de données de démonstration couvrant toutes les fonctionnalités."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help="Purge les données métier avant de recréer le jeu de démonstration.",
        )

    # ------------------------------------------------------------------ helpers

    def ok(self, msg):
        self.stdout.write(self.style.SUCCESS(f'  {msg}'))

    def info(self, msg):
        self.stdout.write(f'  {msg}')

    def section(self, title):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(f'=> {title}'))

    def user(self, matricule, first, last, password, roles=(), **kwargs):
        """Crée ou met à jour un compte, et garantit son mot de passe."""
        obj, created = User.objects.get_or_create(
            matricule=matricule,
            defaults={
                'email': f'{matricule.lower()}@asecna.sn',
                'first_name': first,
                'last_name': last,
                **kwargs,
            },
        )
        obj.first_name, obj.last_name = first, last
        for key, value in kwargs.items():
            setattr(obj, key, value)
        # Le mot de passe est repose a chaque execution : le guide de tests
        # garantit ainsi des identifiants fonctionnels.
        obj.set_password(password)
        obj.save()
        for role in roles:
            UserRole.objects.get_or_create(
                user=obj, role=role, is_active=True,
                defaults={'notes': 'Attribué par seed_demo'},
            )
        return obj

    def profile(self, user, status, unit=None, specialty=None, **kwargs):
        obj, _ = AgentProfile.objects.get_or_create(user=user)
        obj.status = status
        obj.unit = unit
        obj.specialty = specialty
        for key, value in kwargs.items():
            setattr(obj, key, value)
        obj.save()  # declenche le signal de creation du carnet ARCEP si QUALIFIED
        return obj

    # --------------------------------------------------------------------- main

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            self.section('Purge des données métier')
            for model in (
                Answer, ExamSession, Exam, Question,
                ARCEPSignature, ARCEPEntry, ARCEPBook,
                QualificationMaintenance, Internship, Course,
                MentoringRecord, ProbationPeriod, Report, ApprovalWorkflow,
                AgentSkill, AgentCertification, PerformanceIndicator,
            ):
                n = model.objects.all().delete()[0]
                if n:
                    self.info(f'{model.__name__} : {n} ligne(s) supprimée(s)')

        self.section('Référentiel : unités et spécialités')
        units = self.seed_units()
        specialties = self.seed_specialties()

        self.section('Comptes et rôles')
        people = self.seed_people(units, specialties)

        self.section('Formations, cours et stages')
        trainings = self.seed_trainings(specialties, people)

        self.section("Périodes d'essai (tous les cas de figure)")
        self.seed_probation(people)

        self.section('Fiches de mentorat (tous les statuts)')
        self.seed_mentoring(people)

        self.section('Carnets ARCEP (entrées signées et non signées)')
        self.seed_arcep(people)

        self.section('Évaluations : questions, examens, sessions, corrections')
        self.seed_evaluations(trainings, people)

        self.section('Maintien de qualification (tous les statuts)')
        self.seed_maintenance(trainings, people)

        self.section('Rapports (3 types x 4 statuts)')
        self.seed_reports(people)

        self.section("Workflows d'approbation")
        self.seed_workflows(people)

        self.section('Compétences, certifications et performances')
        self.seed_agent_extras(people)

        self.print_summary()

    # ------------------------------------------------------------------ données

    def seed_units(self):
        data = [
            ('MIRE-CNS', 'Communication, Navigation, Surveillance', 'COM', 'Dakar'),
            ('MIRE-RSI-MTO', 'Réseaux, Systèmes Informatiques et Météo', 'MET', 'Dakar'),
            ('MIRE-QIP', 'Qualité, Ingénierie et Projets', 'ADMIN', 'Dakar'),
            ('MIRE-ELB', 'Énergie et Logistique Bâtiment', 'OTHER', 'Dakar'),
            ('TWR-DKR', 'Tour de contrôle de Dakar', 'TWR', 'Dakar'),
        ]
        units = {}
        for code, name, kind, location in data:
            obj, created = Unit.objects.get_or_create(
                code=code,
                defaults={'name': name, 'unit_type': kind,
                          'location': location, 'country': 'Sénégal'},
            )
            units[code] = obj
            if created:
                self.ok(f'Unité {code}')
        self.info(f'{len(units)} unités disponibles')
        return units

    def seed_specialties(self):
        """
        Spécialités du référentiel officiel (fixtures/initial_data.json).

        On ne crée volontairement AUCUN code supplémentaire : inventer des
        codes proches (CNS, RSI, MTO...) dupliquerait les spécialités
        existantes (MTO ferait doublon avec MET, par exemple).
        """
        data = [
            ('ATC', 'Contrôle de la circulation aérienne'),
            ('MET', 'Météorologie aéronautique'),
            ('COM', 'Télécommunications aéronautiques'),
            ('ELEC', 'Électronique et maintenance'),
            ('INFO', 'Informatique aéronautique'),
        ]
        out = {}
        for code, name in data:
            obj, created = Specialty.objects.get_or_create(
                code=code, defaults={'name': name},
            )
            out[code] = obj
            if created:
                self.ok(f'Spécialité {code}')
        self.info(f'{len(out)} spécialités disponibles')
        return out

    def seed_people(self, units, specialties):
        p = {}

        # --- Encadrement -----------------------------------------------------
        p['admin'] = self.user('ASE-2024-0001', 'Directeur', 'GENERAL', PWD_ADMIN,
                               roles=[FunctionalRole.ADMIN],
                               is_staff=True, is_superuser=True)
        p['chef_cns'] = self.user('ASE-2024-0010', 'Amadou', 'DIALLO', PWD_CHEF,
                                  roles=[FunctionalRole.UNIT_CHIEF])
        p['chef_rsi'] = self.user('ASE-2024-0011', 'Ousmane', 'NDIAYE', PWD_CHEF,
                                  roles=[FunctionalRole.UNIT_CHIEF])
        p['chef_qip'] = self.user('ASE-2024-0012', 'Fatou', 'SARR', PWD_CHEF,
                                  roles=[FunctionalRole.UNIT_CHIEF])
        p['chef_elb'] = self.user('ASE-2024-0013', 'Ibrahima', 'FALL', PWD_CHEF,
                                  roles=[FunctionalRole.UNIT_CHIEF])
        p['mentor'] = self.user('ASE-2024-0020', 'Moussa', 'TRAORE', PWD_MENTOR,
                                roles=[FunctionalRole.MENTOR])
        p['mentor2'] = self.user('ASE-2024-0021', 'Aminata', 'CISSE', PWD_MENTOR,
                                 roles=[FunctionalRole.MENTOR])
        p['evaluateur'] = self.user('ASE-2024-0030', 'Kofi', 'MENSAH', PWD_EVAL,
                                    roles=[FunctionalRole.EVALUATOR])
        p['instructeur'] = self.user('ASE-2024-0040', 'Awa', 'SECK', PWD_INSTR,
                                     roles=[FunctionalRole.INSTRUCTOR])
        p['approbateur'] = self.user('ASE-2024-0050', 'Cheikh', 'BA', PWD_APPRO,
                                     roles=[FunctionalRole.APPROVER])
        # Cumul de roles : vérifie qu'un agent peut porter deux casquettes
        p['eval_mentor'] = self.user('ASE-2024-0031', 'Mariama', 'KANE', PWD_EVAL,
                                     roles=[FunctionalRole.EVALUATOR,
                                            FunctionalRole.MENTOR])

        self.profile(p['chef_cns'], AgentStatus.QUALIFIED, units['MIRE-CNS'],
                     specialties['COM'], hire_date=d(-4000),
                     qualification_date=d(-3600))
        self.profile(p['chef_rsi'], AgentStatus.QUALIFIED, units['MIRE-RSI-MTO'],
                     specialties['INFO'], hire_date=d(-3800))
        self.profile(p['chef_qip'], AgentStatus.QUALIFIED, units['MIRE-QIP'],
                     specialties['ATC'], hire_date=d(-3700))
        self.profile(p['chef_elb'], AgentStatus.QUALIFIED, units['MIRE-ELB'],
                     specialties['ELEC'], hire_date=d(-3500))
        self.profile(p['mentor'], AgentStatus.QUALIFIED, units['MIRE-CNS'],
                     specialties['COM'], hire_date=d(-3000))
        self.profile(p['mentor2'], AgentStatus.QUALIFIED, units['MIRE-RSI-MTO'],
                     specialties['INFO'], hire_date=d(-2900))
        self.profile(p['evaluateur'], AgentStatus.QUALIFIED, units['MIRE-QIP'],
                     specialties['ATC'], hire_date=d(-2800))
        self.profile(p['eval_mentor'], AgentStatus.QUALIFIED, units['MIRE-CNS'],
                     specialties['COM'], hire_date=d(-2700))
        self.profile(p['instructeur'], AgentStatus.QUALIFIED, units['MIRE-RSI-MTO'],
                     specialties['INFO'], hire_date=d(-2600))
        self.profile(p['approbateur'], AgentStatus.QUALIFIED, units['MIRE-QIP'],
                     specialties['ATC'], hire_date=d(-2500))

        # --- Agents : un par statut de parcours ------------------------------
        # (le graphique du tableau de bord ADMIN affiche les 7 statuts)
        agents = [
            ('nouveau', 'ASE-2024-0100', 'Seydou', 'KEITA',
             AgentStatus.NEW, 'MIRE-CNS', 'COM', -20, None),
            ('probation', 'ASE-2024-0101', 'Khadija', 'MBAYE',
             AgentStatus.PROBATION, 'MIRE-RSI-MTO', 'INFO', -85, None),
            ('mentore', 'ASE-2024-0102', 'Lamine', 'GUEYE',
             AgentStatus.MENTORED, 'MIRE-QIP', 'ATC', -200, None),
            ('stagiaire', 'ASE-2024-0103', 'Ndeye', 'DIOP',
             AgentStatus.TRAINEE, 'MIRE-ELB', 'ELEC', -400, None),
            ('qualifie', 'ASE-2024-0104', 'Babacar', 'SOW',
             AgentStatus.QUALIFIED, 'MIRE-CNS', 'COM', -900, -500),
            ('qualifie2', 'ASE-2024-0105', 'Rokhaya', 'THIAM',
             AgentStatus.QUALIFIED, 'MIRE-RSI-MTO', 'MET', -1100, -800),
            ('suspendu', 'ASE-2024-0106', 'Malick', 'SY',
             AgentStatus.SUSPENDED, 'MIRE-QIP', 'ATC', -1500, -1200),
            ('retraite', 'ASE-2024-0107', 'Aissatou', 'BARRY',
             AgentStatus.RETIRED, 'MIRE-ELB', 'ELEC', -9000, -8000),
            # Agents dédiés aux scénarios de période d'essai
            ('prob_j14', 'ASE-2024-0110', 'Oumar', 'CAMARA',
             AgentStatus.PROBATION, 'MIRE-CNS', 'COM', -80, None),
            ('prob_reussie', 'ASE-2024-0111', 'Sokhna', 'LO',
             AgentStatus.MENTORED, 'MIRE-RSI-MTO', 'INFO', -150, None),
            ('prob_2e', 'ASE-2024-0112', 'Alioune', 'DIAGNE',
             AgentStatus.PROBATION, 'MIRE-QIP', 'ATC', -200, None),
            ('prob_echec', 'ASE-2024-0113', 'Bineta', 'NIANG',
             AgentStatus.RETIRED, 'MIRE-ELB', 'ELEC', -300, None),
        ]
        for key, mat, first, last, status, unit, spec, hire, qualif in agents:
            u = self.user(mat, first, last, PWD_AGENT, roles=[FunctionalRole.AGENT])
            self.profile(
                u, status, units[unit], specialties[spec],
                hire_date=d(hire),
                qualification_date=d(qualif) if qualif else None,
            )
            p[key] = u

        self.ok(f'{User.objects.count()} comptes, '
                f'{AgentProfile.objects.count()} profils agents')
        statuses = {s: AgentProfile.objects.filter(status=s).count()
                    for s, _ in AgentStatus.choices}
        self.info('Répartition des statuts : '
                  + ', '.join(f'{k}={v}' for k, v in statuses.items() if v))
        return p

    def seed_trainings(self, specialties, people):
        t = {}
        data = [
            ('qualif_cns', 'Qualification initiale CNS (EAMAC)', 'COM',
             Training.TrainingType.QUALIFYING, 120, 80),
            ('qualif_rsi', 'Qualification initiale RSI (EAMAC)', 'INFO',
             Training.TrainingType.QUALIFYING, 120, 80),
            ('maintien_cns', 'Maintien de compétences CNS', 'COM',
             Training.TrainingType.NON_QUALIFYING, 10, 70),
            ('elearning_secu', 'E-learning : sécurité aéronautique', 'ATC',
             Training.TrainingType.ELEARNING, 5, 70),
            ('atelier_meteo', 'Atelier météorologie aéronautique', 'MET',
             Training.TrainingType.WORKSHOP, 3, 70),
        ]
        for key, title, spec, kind, days, score in data:
            obj, created = Training.objects.get_or_create(
                title=title,
                defaults={'specialty': specialties[spec], 'training_type': kind,
                          'duration_days': days, 'passing_score': score,
                          'description': f'Formation {kind} — seuil de réussite {score}/100.'},
            )
            # Re-rattachement idempotent : si la formation existait deja avec une
            # autre specialite, on la realigne sur le referentiel.
            if obj.specialty_id != specialties[spec].id:
                obj.specialty = specialties[spec]
                obj.save(update_fields=['specialty'])
            t[key] = obj
            if created:
                self.ok(f'Formation « {title} »')

        # Cours e-learning : publiés et brouillon
        cours = [
            ('Module 1 — Principes de sécurité', 1, True),
            ('Module 2 — Gestion des incidents', 2, True),
            ('Module 3 — Facteurs humains', 3, True),
            ('Module 4 — Brouillon non publié', 4, False),
        ]
        for title, order, published in cours:
            obj, created = Course.objects.get_or_create(
                training=t['elearning_secu'], title=title,
                defaults={'instructor': people['instructeur'],
                          'content': f'Contenu pédagogique du {title}.',
                          'order': order, 'is_published': published},
            )
            if created:
                self.ok(f'Cours « {title} » ({"publié" if published else "brouillon"})')

        # Stages : en cours, réussi, échoué, qualifiant et non qualifiant
        stages = [
            ('stagiaire', 'qualif_rsi', Internship.InternshipType.QUALIFYING,
             'EAMAC Niamey', -60, 60, None),
            ('qualifie', 'qualif_cns', Internship.InternshipType.QUALIFYING,
             'EAMAC Niamey', -800, -680, True),
            ('mentore', 'atelier_meteo', Internship.InternshipType.NON_QUALIFYING,
             'ASECNA Dakar', -30, -27, True),
            ('suspendu', 'qualif_cns', Internship.InternshipType.QUALIFYING,
             'EAMAC Niamey', -1300, -1180, False),
        ]
        for who, training, kind, place, start, end, passed in stages:
            obj, created = Internship.objects.get_or_create(
                agent=people[who], training=t[training], start_date=d(start),
                defaults={'internship_type': kind, 'location': place,
                          'end_date': d(end), 'is_passed': passed,
                          'report': 'Rapport de stage renseigné.' if passed is not None else ''},
            )
            if created:
                etat = 'en cours' if passed is None else ('réussi' if passed else 'échoué')
                self.ok(f'Stage {people[who].matricule} ({etat})')
        return t

    def seed_probation(self, p):
        """
        Chaque règle métier est illustrée :
          - alerte J-14
          - réussite (>= 70/100)
          - 2e tentative après échec
          - 2e échec -> agent non retenu
        """
        def make(agent, attempt, start, end, status, score=None, comment=''):
            obj = ProbationPeriod.objects.filter(
                agent=agent, attempt_number=attempt,
            ).first()
            if obj:
                return obj
            obj = ProbationPeriod(
                agent=agent, attempt_number=attempt,
                start_date=d(start), end_date=d(end),
                probation_status=status,
                score=Decimal(str(score)) if score is not None else None,
                unit_chief_comment=comment,
            )
            if status != ProbationPeriod.ProbationStatus.IN_PROGRESS:
                obj.actual_end_date = d(end)
                obj.evaluated_by = p['evaluateur']
            obj.save()
            return obj

        # 1. En cours, échéance dans 10 jours -> declenche l'alerte J-14
        make(p['prob_j14'], 1, -80, 10, ProbationPeriod.ProbationStatus.IN_PROGRESS)
        self.ok(f"{p['prob_j14'].matricule} : en cours, échéance J+10 (alerte J-14)")

        # 2. En cours, échéance lointaine -> pas d'alerte
        make(p['probation'], 1, -20, 70, ProbationPeriod.ProbationStatus.IN_PROGRESS)
        self.ok(f"{p['probation'].matricule} : en cours, échéance J+70")

        # 3. Réussie avec 85/100
        make(p['prob_reussie'], 1, -150, -60,
             ProbationPeriod.ProbationStatus.PASSED, 85,
             "Très bonne intégration, aptitudes confirmées.")
        self.ok(f"{p['prob_reussie'].matricule} : réussie (85/100)")

        # 4. 1re tentative échouée puis 2e en cours
        make(p['prob_2e'], 1, -200, -110,
             ProbationPeriod.ProbationStatus.FAILED, 55,
             "Résultats insuffisants, une seconde tentative est accordée.")
        make(p['prob_2e'], 2, -85, 5, ProbationPeriod.ProbationStatus.IN_PROGRESS)
        self.ok(f"{p['prob_2e'].matricule} : 1re échouée (55/100), 2e en cours (J+5)")

        # 5. Deux échecs -> agent non retenu
        make(p['prob_echec'], 1, -300, -210,
             ProbationPeriod.ProbationStatus.FAILED, 48, "Échec de la 1re tentative.")
        make(p['prob_echec'], 2, -200, -110,
             ProbationPeriod.ProbationStatus.FAILED, 61,
             "Échec de la 2e et dernière tentative — agent non retenu.")
        self.ok(f"{p['prob_echec'].matricule} : 2 échecs (48 puis 61/100)")

    def seed_mentoring(self, p):
        data = [
            ('mentore', 'mentor', 'chef_qip', MentoringRecord.MentoringStatus.DRAFT,
             "Prise en main des équipements CNS.", '', ''),
            ('probation', 'mentor2', 'chef_rsi', MentoringRecord.MentoringStatus.SUBMITTED,
             "Autonomie sur la supervision réseau.",
             "Progression régulière, bonne implication.", ''),
            ('prob_reussie', 'mentor', 'chef_rsi', MentoringRecord.MentoringStatus.APPROVED,
             "Maîtrise des procédures d'exploitation.",
             "Objectifs atteints.", "Avis favorable du chef d'unité."),
            ('stagiaire', 'mentor2', 'chef_elb', MentoringRecord.MentoringStatus.REJECTED,
             "Habilitation énergie et groupes électrogènes.",
             "Observations incomplètes.",
             "Fiche à compléter : objectifs non mesurables."),
            ('qualifie', 'mentor', 'chef_cns', MentoringRecord.MentoringStatus.COMPLETED,
             "Mentorat de fin de parcours.",
             "Agent pleinement opérationnel.", "Mentorat clôturé."),
        ]
        for agent, mentor, chief, status, obj_text, observ, chief_op in data:
            rec, created = MentoringRecord.objects.get_or_create(
                agent=p[agent], mentor=p[mentor],
                defaults={
                    'unit_chief': p[chief],
                    'start_date': d(-120),
                    'end_date': d(-10) if status in (
                        MentoringRecord.MentoringStatus.COMPLETED,
                        MentoringRecord.MentoringStatus.APPROVED,
                    ) else None,
                    'objectives': obj_text,
                    'mentor_observations': observ,
                    'mentor_opinion': "Avis du mentor renseigné." if observ else '',
                    'unit_chief_opinion': chief_op,
                    'mentoring_status': status,
                    'submitted_at': timezone.now() if status != MentoringRecord.MentoringStatus.DRAFT else None,
                    'approved_at': timezone.now() if status in (
                        MentoringRecord.MentoringStatus.APPROVED,
                        MentoringRecord.MentoringStatus.COMPLETED,
                    ) else None,
                },
            )
            if created:
                self.ok(f'Mentorat {p[agent].matricule} [{status}]')

    def seed_arcep(self, p):
        """
        Carnets ARCEP : des entrées couvertes par une signature (is_validated
        vrai) et d'autres non encore signées (is_validated faux).
        """
        activites = [
            "Maintenance préventive VOR/DME",
            "Test de la chaîne radar secondaire",
            "Contrôle des alimentations sans coupure",
            "Supervision du réseau AFTN",
            "Étalonnage des capteurs météo",
            "Intervention sur balise NDB",
        ]
        # Regle metier : le carnet est ouvert des que l'agent est QUALIFIED.
        # Le signal ne se declenche qu'au CHANGEMENT de statut : on garantit donc
        # ici que tout agent deja qualifie possede bien son carnet.
        for profile in AgentProfile.objects.filter(
            status=AgentStatus.QUALIFIED,
        ).select_related('user'):
            ARCEPBook.objects.get_or_create(agent=profile.user)
        self.ok(f'{ARCEPBook.objects.count()} carnets ouverts '
                f'(un par agent qualifié)')

        # Entrees et signatures detaillees sur un echantillon
        for key in ('qualifie', 'qualifie2', 'chef_cns', 'suspendu'):
            agent = p[key]
            book, _ = ARCEPBook.objects.get_or_create(agent=agent)

            # Entrées anciennes -> seront couvertes par la signature
            for i, offset in enumerate((-50, -45, -40)):
                ARCEPEntry.objects.get_or_create(
                    book=book, entry_date=d(offset),
                    defaults={'activity': activites[i % len(activites)],
                              'duration_hours': Decimal('4.5'),
                              'notes': 'Intervention conforme aux procédures.'},
                )
            # Entrées récentes -> non encore signées
            for i, offset in enumerate((-5, -2)):
                ARCEPEntry.objects.get_or_create(
                    book=book, entry_date=d(offset),
                    defaults={'activity': activites[(i + 3) % len(activites)],
                              'duration_hours': Decimal('3.0'),
                              'notes': 'En attente de visa du chef d\'unité.'},
                )

            # Une signature couvrant uniquement la période ancienne
            ARCEPSignature.objects.get_or_create(
                book=book, period_start=d(-60), period_end=d(-30),
                defaults={'unit_chief': p['chef_cns'],
                          'comment': 'Visa périodique du chef d\'unité.'},
            )
            self.ok(f'Carnet ARCEP {agent.matricule} : 5 entrées, 1 période signée')

    def seed_evaluations(self, trainings, p):
        """
        Couvre le workflow de correction en 4 étapes, avec une session dans
        CHAQUE état : IN_PROGRESS, SUBMITTED, CORRECTING, PENDING_APPROVAL,
        GRADED et REJECTED.
        """
        questions = []
        catalogue = [
            (Question.QuestionType.GENERAL, Question.QuestionKind.MCQ, 1,
             "Que signifie le sigle ASECNA ?",
             "Agence pour la Sécurité de la Navigation Aérienne",
             ["Agence pour la Sécurité de la Navigation Aérienne",
              "Association des Contrôleurs Aériens",
              "Autorité de Surveillance Aérienne", "Aucune de ces réponses"], 10),
            (Question.QuestionType.TECHNICAL, Question.QuestionKind.MCQ, 3,
             "Quelle est la bande de fréquence d'un VOR ?",
             "108 - 117,975 MHz",
             ["108 - 117,975 MHz", "329 - 335 MHz", "960 - 1215 MHz", "2700 - 2900 MHz"], 10),
            (Question.QuestionType.TECHNICAL, Question.QuestionKind.TF, 2,
             "Un ILS comprend un localizer et un glide path.", "Vrai",
             ["Vrai", "Faux"], 10),
            (Question.QuestionType.UNIT_SPECIFIC, Question.QuestionKind.OPEN, 4,
             "Décrivez la procédure de bascule sur l'alimentation de secours.",
             "Vérification du groupe, bascule onduleur, contrôle des départs, consignation.",
             [], 10),
            (Question.QuestionType.GENERAL, Question.QuestionKind.TF, 1,
             "Le carnet ARCEP doit être visé par le chef d'unité.", "Vrai",
             ["Vrai", "Faux"], 10),
            (Question.QuestionType.TECHNICAL, Question.QuestionKind.OPEN, 5,
             "Expliquez le rôle du radar secondaire (SSR) dans la surveillance.",
             "Interrogation des transpondeurs, identification et altitude des aéronefs.",
             [], 10),
        ]
        for qtype, kind, diff, text, answer, options, points in catalogue:
            q, created = Question.objects.get_or_create(
                text=text,
                defaults={'question_type': qtype, 'question_kind': kind,
                          'difficulty': diff, 'correct_answer': answer,
                          'options': options, 'points': points,
                          'training': trainings['qualif_cns'],
                          'created_by': p['evaluateur']},
            )
            questions.append(q)
        self.ok(f'{len(questions)} questions (3 types, 3 formats, difficultés 1 à 5)')

        exams = {}
        for key, title, status in (
            ('publie', 'Examen de qualification CNS — session en cours', Exam.ExamStatus.PUBLISHED),
            ('brouillon', 'Examen RSI — brouillon', Exam.ExamStatus.DRAFT),
            ('ferme', 'Examen CNS — session clôturée', Exam.ExamStatus.CLOSED),
        ):
            e, created = Exam.objects.get_or_create(
                title=title,
                defaults={'training': trainings['qualif_cns'],
                          'created_by': p['evaluateur'],
                          'duration_minutes': 90, 'passing_score': 70,
                          'exam_status': status},
            )
            if created:
                e.questions.set(questions[:4] if key != 'brouillon' else questions)
            exams[key] = e
            self.ok(f'Examen « {title} » [{status}]')

        # Une session par état du workflow
        scenarios = [
            ('nouveau', ExamSession.SessionStatus.IN_PROGRESS, 0, None),
            ('probation', ExamSession.SessionStatus.SUBMITTED, 0, None),
            ('mentore', ExamSession.SessionStatus.CORRECTING, 2, None),
            ('stagiaire', ExamSession.SessionStatus.PENDING_APPROVAL, 4, Decimal('75.00')),
            ('qualifie', ExamSession.SessionStatus.GRADED, 4, Decimal('82.50')),
            ('suspendu', ExamSession.SessionStatus.REJECTED, 4, Decimal('68.00')),
        ]
        exam = exams['publie']
        exam_questions = list(exam.questions.all())
        for who, status, n_corrected, score in scenarios:
            agent = p[who]
            session = ExamSession.objects.filter(exam=exam, agent=agent).first()
            if session is None:
                session = ExamSession.objects.create(
                    exam=exam, agent=agent, session_status=status, score=score,
                )
            session.session_status = status
            session.score = score
            if status != ExamSession.SessionStatus.IN_PROGRESS:
                session.submitted_at = timezone.now()
            if status in (ExamSession.SessionStatus.PENDING_APPROVAL,
                          ExamSession.SessionStatus.GRADED,
                          ExamSession.SessionStatus.REJECTED):
                session.graded_by = p['evaluateur']
                session.graded_at = timezone.now()
            if status == ExamSession.SessionStatus.GRADED:
                session.approved_by = p['chef_cns']
                session.approved_at = timezone.now()
                session.is_passed = score is not None and score >= exam.passing_score
            if status == ExamSession.SessionStatus.REJECTED:
                session.approved_by = p['chef_cns']
                session.rejection_reason = (
                    "Barème non respecté sur la question ouverte : à recorriger."
                )
            session.save()

            # Réponses de l'agent, dont `n_corrected` déjà corrigées
            if status != ExamSession.SessionStatus.IN_PROGRESS:
                for idx, q in enumerate(exam_questions):
                    ans, _ = Answer.objects.get_or_create(
                        session=session, question=q,
                        defaults={'response': q.correct_answer if idx % 3 else 'Réponse partielle.'},
                    )
                    if idx < n_corrected:
                        points = Decimal('10.00') if idx % 3 else Decimal('6.00')
                        ans.evaluator_score = points
                        ans.is_correct = points >= Decimal('7.00')
                        ans.feedback = ('Réponse conforme.' if points >= 7
                                        else 'Réponse incomplète, points partiels.')
                        ans.corrected_by = p['evaluateur']
                        ans.corrected_at = timezone.now()
                        ans.save()
            self.ok(f'Session {agent.matricule} [{status}]'
                    + (f' score {score}' if score else ''))

    def seed_maintenance(self, trainings, p):
        data = [
            ('qualifie', QualificationMaintenance.MaintenanceStatus.PENDING, 25, None,
             "Contrôle biennal programmé."),
            ('qualifie2', QualificationMaintenance.MaintenanceStatus.PENDING, -20, None,
             "ÉCHÉANCE DÉPASSÉE — contrôle à planifier d'urgence."),
            ('chef_cns', QualificationMaintenance.MaintenanceStatus.PASSED, -40,
             Decimal('88.00'), "Maintien validé."),
            ('suspendu', QualificationMaintenance.MaintenanceStatus.FAILED, -60,
             Decimal('52.00'), "Échec du maintien — agent suspendu."),
            ('mentor', QualificationMaintenance.MaintenanceStatus.WAIVED, -15, None,
             "Dispensé : agent en mission longue durée."),
        ]
        for who, status, due_offset, score, notes in data:
            obj, created = QualificationMaintenance.objects.get_or_create(
                agent=p[who], due_date=d(due_offset),
                defaults={
                    'training': trainings['maintien_cns'],
                    'score': score,
                    'maintenance_status': status,
                    'notes': notes,
                    'evaluated_by': p['evaluateur'] if status != QualificationMaintenance.MaintenanceStatus.PENDING else None,
                    'evaluated_at': timezone.now() if status != QualificationMaintenance.MaintenanceStatus.PENDING else None,
                },
            )
            if created:
                etat = 'en retard' if (status == 'PENDING' and due_offset < 0) else status
                self.ok(f'Maintien QF {p[who].matricule} [{etat}]')

    def seed_reports(self, p):
        combos = [
            (Report.ReportType.PROBATION, Report.ReportStatus.DRAFT, 'prob_j14'),
            (Report.ReportType.PROBATION, Report.ReportStatus.SUBMITTED, 'prob_reussie'),
            (Report.ReportType.MENTORING, Report.ReportStatus.SUBMITTED, 'mentore'),
            (Report.ReportType.MENTORING, Report.ReportStatus.APPROVED, 'qualifie'),
            (Report.ReportType.ASSESSMENT, Report.ReportStatus.APPROVED, 'qualifie2'),
            (Report.ReportType.ASSESSMENT, Report.ReportStatus.REJECTED, 'suspendu'),
        ]
        labels = dict(Report.ReportType.choices)
        for kind, status, who in combos:
            title = f'{labels[kind]} — {p[who].full_name}'
            obj, created = Report.objects.get_or_create(
                report_type=kind, agent=p[who], title=title,
                defaults={
                    'created_by': p['chef_cns'],
                    'content': "Corps du rapport : constats, suivi et appréciation générale.",
                    'conclusion': "Conclusion et recommandations du rédacteur.",
                    'report_status': status,
                    'approver': p['approbateur'] if status in ('APPROVED', 'REJECTED') else None,
                    'approver_opinion': ('Avis favorable.' if status == 'APPROVED'
                                         else 'Rapport à reprendre.' if status == 'REJECTED' else ''),
                    'submitted_at': timezone.now() if status != 'DRAFT' else None,
                    'approved_at': timezone.now() if status == 'APPROVED' else None,
                },
            )
            if created:
                self.ok(f'Rapport {kind} [{status}] — {p[who].matricule}')

    def seed_workflows(self, p):
        """Workflows génériques rattachés à des objets réels (GenericForeignKey)."""
        ct_report = ContentType.objects.get_for_model(Report)
        ct_mentoring = ContentType.objects.get_for_model(MentoringRecord)

        targets = []
        for report in Report.objects.all()[:2]:
            targets.append((ct_report, report.id,
                            ApprovalWorkflow.WorkflowStatus.SUBMITTED))
        for rec in MentoringRecord.objects.all()[:2]:
            targets.append((ct_mentoring, rec.id,
                            ApprovalWorkflow.WorkflowStatus.APPROVED))
        if Report.objects.count() > 2:
            r = Report.objects.all()[2]
            targets.append((ct_report, r.id, ApprovalWorkflow.WorkflowStatus.REJECTED))

        for ct, oid, status in targets:
            obj, created = ApprovalWorkflow.objects.get_or_create(
                content_type=ct, object_id=oid,
                defaults={
                    'submitted_by': p['chef_cns'],
                    'approver': p['approbateur'],
                    'unit_chief': p['chef_cns'],
                    'workflow_status': status,
                    'approver_comment': 'Traité par l\'approbateur.' if status != 'SUBMITTED' else '',
                    'submitted_at': timezone.now(),
                    'approved_at': timezone.now() if status == 'APPROVED' else None,
                    'rejected_at': timezone.now() if status == 'REJECTED' else None,
                },
            )
            if created:
                self.ok(f'Workflow {ct.model}#{oid} [{status}]')

    def seed_agent_extras(self, p):
        competences = [
            ('Maintenance VOR/DME', 4), ('Supervision réseau AFTN', 3),
            ('Radar primaire et secondaire', 5), ('Groupes électrogènes', 2),
            ('Systèmes météo automatiques', 4),
        ]
        for key in ('qualifie', 'qualifie2', 'chef_cns', 'mentore'):
            for name, level in competences[:4]:
                AgentSkill.objects.get_or_create(
                    agent=p[key], name=name,
                    defaults={'level': level, 'acquired_at': d(-300),
                              'notes': 'Évaluée en situation de travail.'},
                )
        self.ok(f'{AgentSkill.objects.count()} compétences')

        certifs = [
            ('Habilitation électrique BR', 'ASECNA', -500, 400),
            ('Certificat ICAO English Level 4', 'OACI', -900, -30),   # expirée
            ('Sécurité aéroportuaire', 'ANACIM', -200, 900),
        ]
        for key in ('qualifie', 'chef_cns'):
            for name, body, issued, expires in certifs:
                AgentCertification.objects.get_or_create(
                    agent=p[key], name=name,
                    defaults={'issuing_body': body, 'issue_date': d(issued),
                              'expiry_date': d(expires)},
                )
        self.ok(f'{AgentCertification.objects.count()} certifications '
                f'(dont une expirée, pour tester l\'affichage)')

        annee = TODAY.year
        for key, scores in (
            ('qualifie', [78, 84, 91]), ('qualifie2', [70, 75, 80]),
            ('chef_cns', [88, 90, 93]), ('suspendu', [65, 58, 52]),
        ):
            for offset, score in enumerate(scores):
                PerformanceIndicator.objects.get_or_create(
                    agent=p[key], year=annee - (len(scores) - 1 - offset),
                    defaults={'score': Decimal(str(score)),
                              'evaluator': p['chef_cns'],
                              'comments': 'Évaluation annuelle de performance.'},
                )
        self.ok(f'{PerformanceIndicator.objects.count()} indicateurs de performance '
                f'(3 années par agent, pour tracer une tendance)')

    # ------------------------------------------------------------------ rapport

    def print_summary(self):
        from django.apps import apps

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('=> Inventaire final'))
        apps_metier = {
            'accounts', 'units', 'agents', 'probation', 'mentoring', 'training',
            'evaluations', 'workflows', 'arcep', 'reports',
        }
        vides = []
        for model in sorted(apps.get_models(),
                            key=lambda m: (m._meta.app_label, m.__name__)):
            if model._meta.app_label not in apps_metier:
                continue
            n = model.objects.count()
            label = f'{model._meta.app_label}.{model.__name__}'
            if n == 0:
                vides.append(label)
                self.stdout.write(self.style.WARNING(f'  {label:44} {n:4}  <-- VIDE'))
            else:
                self.stdout.write(f'  {label:44} {n:4}')

        self.stdout.write('')
        if vides:
            self.stdout.write(self.style.WARNING(
                f'  {len(vides)} modèle(s) encore vide(s) : ' + ', '.join(vides)))
        else:
            self.stdout.write(self.style.SUCCESS(
                '  Tous les modèles métier contiennent des données.'))

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('=> Identifiants de connexion'))
        table = [
            ('Administrateur', 'ASE-2024-0001', PWD_ADMIN),
            ("Chef d'unité CNS", 'ASE-2024-0010', PWD_CHEF),
            ("Chef d'unité RSI", 'ASE-2024-0011', PWD_CHEF),
            ('Mentor', 'ASE-2024-0020', PWD_MENTOR),
            ('Évaluateur', 'ASE-2024-0030', PWD_EVAL),
            ('Évaluateur + Mentor', 'ASE-2024-0031', PWD_EVAL),
            ('Instructeur', 'ASE-2024-0040', PWD_INSTR),
            ('Approbateur', 'ASE-2024-0050', PWD_APPRO),
            ('Agent (nouveau)', 'ASE-2024-0100', PWD_AGENT),
            ("Agent (en période d'essai)", 'ASE-2024-0101', PWD_AGENT),
            ('Agent (qualifié)', 'ASE-2024-0104', PWD_AGENT),
            ('Agent (suspendu)', 'ASE-2024-0106', PWD_AGENT),
        ]
        self.stdout.write(f"  {'Rôle':30} {'Matricule':16} Mot de passe")
        self.stdout.write('  ' + '-' * 62)
        for role, mat, pwd in table:
            self.stdout.write(f'  {role:30} {mat:16} {pwd}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            '  Jeu de données prêt. Voir GUIDE_DE_TESTS.md pour le déroulé.'))
