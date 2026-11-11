# -*- coding: utf-8 -*-
"""
Script de creation de donnees de demonstration pour la soutenance ASECNA.
Cree tous les roles fonctionnels : ADMIN, UNIT_CHIEF, MENTOR, EVALUATOR, INSTRUCTOR, APPROVER, AGENT

Usage :
    python scripts/create_demo_data.py
"""
import os
import sys
import django
import datetime
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    django.setup()

from django.db import transaction

from apps.accounts.models import User, UserRole, AgentProfile, FunctionalRole, AgentStatus
from apps.units.models import Unit
from apps.training.models import Specialty, Training
from apps.probation.models import ProbationPeriod
from apps.mentoring.models import MentoringRecord
from apps.arcep.models import ARCEPBook, ARCEPEntry
from apps.reports.models import Report


def ok(msg):
    print(f"  [OK] {msg}")


def make_user(matricule, email, fn, ln, password, is_staff=False, is_superuser=False):
    """Cree ou recupere un utilisateur et force le mot de passe."""
    user, created = User.objects.get_or_create(
        matricule=matricule,
        defaults={
            'email': email,
            'first_name': fn,
            'last_name': ln,
            'is_staff': is_staff,
            'is_superuser': is_superuser,
        }
    )
    # Toujours mettre a jour le mot de passe
    user.set_password(password)
    user.save()
    return user, created


def assign_role(user, role, assigned_by):
    """Assigne un role fonctionnel a un utilisateur."""
    UserRole.objects.get_or_create(
        user=user, role=role,
        defaults={'assigned_by': assigned_by, 'is_active': True}
    )


def run():
    today          = datetime.date.today()
    end_probation  = today + datetime.timedelta(days=91)

    with transaction.atomic():
        print("\n" + "=" * 60)
        print("  CREATION DES DONNEES DE DEMO ASECNA")
        print("=" * 60 + "\n")

        # ── 1. Unites MIRE-Informatique ───────────────────────────────
        cns_unit  = Unit.objects.get_or_create(code='MIRE-CNS',     defaults={'name': 'CNS',      'unit_type': 'COM'})[0]
        rsi_unit  = Unit.objects.get_or_create(code='MIRE-RSI-MTO', defaults={'name': 'RSI/MTO',  'unit_type': 'OTHER'})[0]
        qip_unit  = Unit.objects.get_or_create(code='MIRE-QIP',     defaults={'name': 'QIP',      'unit_type': 'OTHER'})[0]
        elb_unit  = Unit.objects.get_or_create(code='MIRE-ELB',     defaults={'name': 'ELB',      'unit_type': 'OTHER'})[0]
        ok("Unites MIRE : CNS, RSI/MTO, QIP, ELB")

        # ── 2. Specialite et Formation ────────────────────────────────
        specialty, _ = Specialty.objects.get_or_create(
            code='INFO',
            defaults={'name': 'Informatique aeronautique', 'is_active': True}
        )
        Training.objects.get_or_create(
            title='Formation systemes CNS/ATM',
            defaults={
                'specialty': specialty,
                'training_type': Training.TrainingType.QUALIFYING,
                'duration_days': 90,
                'passing_score': 80,
            }
        )
        ok("Specialite INFO + Formation CNS/ATM")

        # ── 3. ADMIN SYSTEME ──────────────────────────────────────────
        admin, _ = make_user(
            'ASE-2024-0001', 'admin@asecna.sn',
            'Directeur', 'General', 'Admin2024',
            is_staff=True, is_superuser=True
        )
        assign_role(admin, FunctionalRole.ADMIN, admin)
        ok("Admin systeme : ASE-2024-0001 / Admin2024")

        # ── 4. CHEFS D'UNITE (Un par unite) ───────────────────────────
        chiefs_data = [
            ('ASE-2024-0010', 'Ibrahim',  'DIALLO', 'chef.cns@asecna.sn', cns_unit),
            ('ASE-2024-0011', 'Ousmane',  'NDIAYE', 'chef.rsi@asecna.sn', rsi_unit),
            ('ASE-2024-0012', 'Aissatou', 'SENE',   'chef.qip@asecna.sn', qip_unit),
            ('ASE-2024-0013', 'Mamadou',  'FALL',   'chef.elb@asecna.sn', elb_unit),
        ]

        chief = None # Garde une ref pour la suite
        for mat, fn, ln, email, unit in chiefs_data:
            c, created = make_user(mat, email, fn, ln, 'Chef@2024!')
            if created:
                AgentProfile.objects.get_or_create(
                    user=c,
                    defaults={
                        'unit': unit, 'specialty': specialty,
                        'hire_date': datetime.date(2015, 3, 1),
                        'status': AgentStatus.QUALIFIED,
                    }
                )
            assign_role(c, FunctionalRole.UNIT_CHIEF, admin)
            ok(f"Chef d'unite ({unit.code}): {mat} / Chef@2024!")
            if mat == 'ASE-2024-0010':
                chief = c

        # ── 5. MENTOR ─────────────────────────────────────────────────
        mentor, created = make_user(
            'ASE-2024-0020', 'mentor.mire@asecna.sn',
            'Moussa', 'TRAORE', 'Mentor@2024!'
        )
        if created:
            AgentProfile.objects.get_or_create(
                user=mentor,
                defaults={
                    'unit': rsi_unit, 'specialty': specialty,
                    'hire_date': datetime.date(2018, 6, 15),
                    'status': AgentStatus.QUALIFIED,
                }
            )
        assign_role(mentor, FunctionalRole.MENTOR, admin)
        ok("Mentor         : ASE-2024-0020 / Mentor@2024!")

        # ── 6. EVALUATEUR ─────────────────────────────────────────────
        evaluator, created = make_user(
            'ASE-2024-0030', 'evaluateur@asecna.sn',
            'Kofi', 'MENSAH', 'Eval@2024!'
        )
        if created:
            AgentProfile.objects.get_or_create(
                user=evaluator,
                defaults={
                    'unit': qip_unit, 'specialty': specialty,
                    'hire_date': datetime.date(2017, 1, 10),
                    'status': AgentStatus.QUALIFIED,
                }
            )
        assign_role(evaluator, FunctionalRole.EVALUATOR, admin)
        ok("Evaluateur     : ASE-2024-0030 / Eval@2024!")

        # ── 7. INSTRUCTEUR ────────────────────────────────────────────
        instructor, created = make_user(
            'ASE-2024-0040', 'instructeur@asecna.sn',
            'Awa', 'COULIBALY', 'Instr@2024!'
        )
        if created:
            AgentProfile.objects.get_or_create(
                user=instructor,
                defaults={
                    'unit': elb_unit, 'specialty': specialty,
                    'hire_date': datetime.date(2016, 9, 5),
                    'status': AgentStatus.QUALIFIED,
                }
            )
        assign_role(instructor, FunctionalRole.INSTRUCTOR, admin)
        ok("Instructeur    : ASE-2024-0040 / Instr@2024!")

        # ── 8. APPROBATEUR ────────────────────────────────────────────
        approver, created = make_user(
            'ASE-2024-0050', 'approbateur@asecna.sn',
            'Seydou', 'KONE', 'Appro@2024!'
        )
        if created:
            AgentProfile.objects.get_or_create(
                user=approver,
                defaults={
                    'unit': cns_unit, 'specialty': specialty,
                    'hire_date': datetime.date(2014, 4, 20),
                    'status': AgentStatus.QUALIFIED,
                }
            )
        assign_role(approver, FunctionalRole.APPROVER, admin)
        ok("Approbateur    : ASE-2024-0050 / Appro@2024!")

        # ── 9. AGENTS STAGIAIRES (un par unite) ───────────────────────
        agents_data = [
            ('ASE-2024-0100', 'Amadou',  'SALL',   'agent.cns@asecna.sn', cns_unit),
            ('ASE-2024-0101', 'Fatou',   'DIOP',   'agent.rsi@asecna.sn', rsi_unit),
            ('ASE-2024-0102', 'Cheikh',  'BA',     'agent.qip@asecna.sn', qip_unit),
            ('ASE-2024-0103', 'Mariama', 'CAMARA', 'agent.elb@asecna.sn', elb_unit),
        ]

        agents = []
        for mat, fn, ln, email, unit in agents_data:
            agent, created = make_user(mat, email, fn, ln, 'Agent@2024!')
            if created:
                AgentProfile.objects.get_or_create(
                    user=agent,
                    defaults={
                        'unit': unit, 'specialty': specialty,
                        'hire_date': today,
                        'status': AgentStatus.PROBATION,
                    }
                )
                ProbationPeriod.objects.get_or_create(
                    agent=agent, attempt_number=1,
                    defaults={
                        'start_date': today, 'end_date': end_probation,
                        'probation_status': ProbationPeriod.ProbationStatus.IN_PROGRESS,
                    }
                )
                book = ARCEPBook.objects.get_or_create(agent=agent)[0]
                ARCEPEntry.objects.get_or_create(
                    book=book, entry_date=today,
                    defaults={
                        'activity': f'Prise de poste - unite {unit.code}',
                        'duration_hours': 8.0,
                        'notes': 'Premier jour de service.',
                    }
                )
            assign_role(agent, FunctionalRole.AGENT, admin)
            agents.append(agent)
            ok(f"Agent          : {mat} - {fn} {ln} ({unit.code}) / Agent@2024!")

        # ── 10. Fiche de mentorat ─────────────────────────────────────
        if not MentoringRecord.objects.filter(agent=agents[0]).exists():
            MentoringRecord.objects.create(
                agent=agents[0],
                mentor=mentor,
                start_date=today,
                objectives=(
                    'Maitriser les systemes CNS/ATM de la section MIRE. '
                    'Acquerir les procedures exploitation et maintenance.'
                ),
            )
        ok(f"Fiche mentorat : {mentor.full_name} -> {agents[0].full_name}")

        # ── 11. Rapport demo ──────────────────────────────────────────
        if not Report.objects.filter(agent=agents[0], report_type=Report.ReportType.ASSESSMENT).exists():
            Report.objects.create(
                report_type=Report.ReportType.ASSESSMENT,
                agent=agents[0],
                created_by=chief,
                title=f'Bilan periodique - {agents[0].full_name}',
                content=(
                    'Bonne assimilation des procedures CNS. '
                    'Presence reguliere, attitude professionnelle.'
                ),
                conclusion='Avis favorable pour la suite du parcours.',
            )
        ok(f"Rapport bilan  : cree pour {agents[0].full_name}")

        # ── Resume ────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  COMPTE RENDUS DES COMPTES CREES")
        print("=" * 60)
        print("""
  Role          Matricule          Mot de passe
  -----------   ----------------   -----------
  Admin         ASE-2024-0001      Admin2024
  Chef CNS      ASE-2024-0010      Chef@2024!
  Chef RSI      ASE-2024-0011      Chef@2024!
  Chef QIP      ASE-2024-0012      Chef@2024!
  Chef ELB      ASE-2024-0013      Chef@2024!
  Mentor        ASE-2024-0020      Mentor@2024!
  Evaluateur    ASE-2024-0030      Eval@2024!
  Instructeur   ASE-2024-0040      Instr@2024!
  Approbateur   ASE-2024-0050      Appro@2024!
  Agent CNS     ASE-2024-0100      Agent@2024!
  Agent RSI     ASE-2024-0101      Agent@2024!
  Agent QIP     ASE-2024-0102      Agent@2024!
  Agent ELB     ASE-2024-0103      Agent@2024!

  URLs :
    Admin   : http://localhost:8000/admin/
    API     : http://localhost:8000/api/docs/
    Frontend: http://localhost:5173/
""")
        print("=" * 60 + "\n")


if __name__ == '__main__':
    run()
