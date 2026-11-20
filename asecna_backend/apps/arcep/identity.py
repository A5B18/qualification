"""
En-tete du carnet ARCEP : identite de l'agent, qualifications et echeances.

Pourquoi ici et pas dans `serializers.py` : le carnet ARCEP est un document
opposable. Un releve d'activites sans l'identite du titulaire, sa profession
et l'etat de ses qualifications ne vaut rien a la relecture — c'est la
premiere page du carnet papier. Le calcul des echeances a ses propres regles
(fenetre d'alerte, statuts derives), il est donc isole ici et couvert par ses
propres tests.

Sources agregees :
  - `accounts.User` + `accounts.AgentProfile` → identite, profession, unite
  - `agents.AgentCertification`               → certifications et expirations
  - `training.QualificationMaintenance`       → controles biennaux et echeances
  - `training.Internship`                     → stages qualifiants reussis
"""

from __future__ import annotations

import datetime

from django.utils import timezone


#: Fenetre d'alerte : une echeance a moins de 90 jours est signalee.
#: Le controle de maintien de qualification se prepare sur un trimestre
#: (convocation, formation de remise a niveau), d'ou ce delai.
EXPIRY_WARNING_DAYS = 90


# =============================================================================
# Statuts d'une qualification
# =============================================================================

#: Vocabulaire unique pour les trois sources de qualification.
STATUS_LABELS = {
    'VALID':     'Valide',
    'EXPIRING':  'Échéance proche',
    'EXPIRED':   'Expirée',
    'PENDING':   'Contrôle à venir',
    'OVERDUE':   'Contrôle en retard',
    'PASSED':    'Contrôle réussi',
    'FAILED':    'Échec — agent suspendu',
    'WAIVED':    "Dispense du chef d'unité",
    'PERMANENT': 'Sans échéance',
}

#: Statuts qui demandent une action : ils alimentent `alert_level`.
CRITICAL_STATUSES = frozenset({'EXPIRED', 'OVERDUE', 'FAILED'})
WARNING_STATUSES  = frozenset({'EXPIRING'})


def _today() -> datetime.date:
    return timezone.localdate()


def _due_status(due_date, today) -> str:
    """Statut derive d'une date d'echeance seule."""
    if due_date is None:
        return 'PERMANENT'
    if due_date < today:
        return 'EXPIRED'
    if (due_date - today).days <= EXPIRY_WARNING_DAYS:
        return 'EXPIRING'
    return 'VALID'


def _days_remaining(due_date, today):
    return None if due_date is None else (due_date - today).days


def _entry(kind, kind_label, label, status, *, obtained_on=None, due_date=None,
           issuer='', score=None, note='', tracks_due=False, today=None):
    """
    Ligne de qualification, format commun aux trois sources.

    `tracks_due` dit si `due_date` est une echeance encore a tenir. Un
    controle deja reussi garde sa date — elle documente le dernier passage —
    mais ne doit pas apparaitre comme la prochaine echeance de l'agent.
    """
    return {
        'kind':          kind,
        'kind_label':    kind_label,
        'label':         label,
        'issuer':        issuer,
        'obtained_on':   obtained_on,
        'due_date':      due_date,
        'tracks_due':    tracks_due,
        'status':        status,
        'status_label':  STATUS_LABELS.get(status, status),
        'days_remaining': _days_remaining(due_date, today),
        'score':         None if score is None else str(score),
        'note':          note,
    }


# =============================================================================
# Qualifications de l'agent
# =============================================================================

def agent_qualifications(agent, today=None) -> list[dict]:
    """
    Qualifications de l'agent, echeance la plus urgente en tete.

    Trois sources, un seul tableau : le titulaire du carnet n'a pas a savoir
    dans quelle table ASECNA range telle attestation.
    """
    today = today or _today()
    items: list[dict] = []

    # ── Certifications officielles ────────────────────────────────────────────
    for cert in agent.certifications.all():
        items.append(_entry(
            'CERTIFICATION', 'Certification', cert.name,
            _due_status(cert.expiry_date, today),
            obtained_on=cert.issue_date,
            due_date=cert.expiry_date,
            issuer=cert.issuing_body,
            tracks_due=cert.expiry_date is not None,
            today=today,
        ))

    # ── Controles de maintien de qualification (tous les 2 ans) ───────────────
    # Un controle biennal n'est une echeance que tant qu'il est PENDING :
    # une fois reussi, dispense ou echoue, sa date documente le passage mais
    # ne pese plus sur l'agent. Le controle suivant est un autre
    # enregistrement, avec sa propre date d'echeance.
    for maint in agent.qualification_maintenances.all():
        pending = maint.maintenance_status == 'PENDING'
        if pending:
            status = 'OVERDUE' if maint.due_date < today else _due_status(maint.due_date, today)
            if status == 'VALID':
                status = 'PENDING'
        else:
            status = maint.maintenance_status  # PASSED, FAILED ou WAIVED

        training = getattr(maint, 'training', None)
        items.append(_entry(
            'MAINTENANCE', 'Maintien de qualification',
            training.title if training else 'Contrôle biennal',
            status,
            due_date=maint.due_date,
            score=maint.score,
            note=maint.notes or '',
            tracks_due=pending,
            today=today,
        ))

    # ── Stages qualifiants reussis ────────────────────────────────────────────
    for internship in agent.internships.all():
        if internship.internship_type != 'QUALIFYING' or internship.is_passed is not True:
            continue
        training = getattr(internship, 'training', None)
        items.append(_entry(
            'INTERNSHIP', 'Stage qualifiant',
            training.title if training else 'Stage qualifiant',
            'PERMANENT',
            obtained_on=internship.end_date,
            issuer=internship.location or '',
            today=today,
        ))

    # Les lignes a traiter remontent : d'abord les critiques, puis les
    # echeances les plus proches, enfin ce qui n'a pas de date.
    def sort_key(item):
        urgency = 0 if item['status'] in CRITICAL_STATUSES else (
            1 if item['status'] in WARNING_STATUSES else 2
        )
        due = item['due_date'] or datetime.date.max
        return (urgency, due, item['label'])

    items.sort(key=sort_key)
    return items


def qualifications_summary(items, today=None) -> dict:
    """Compteurs et prochaine echeance, pour l'en-tete du carnet."""
    today = today or _today()
    statuses = [item['status'] for item in items]

    upcoming = [
        item for item in items
        if item['tracks_due'] and item['due_date'] is not None
        and item['due_date'] >= today
    ]
    upcoming.sort(key=lambda item: item['due_date'])
    next_due = upcoming[0] if upcoming else None

    critical = sum(1 for s in statuses if s in CRITICAL_STATUSES)
    warning  = sum(1 for s in statuses if s in WARNING_STATUSES)

    return {
        'total':          len(items),
        'valid':          sum(1 for s in statuses
                              if s in ('VALID', 'PASSED', 'PERMANENT', 'PENDING')),
        'expiring_soon':  warning,
        'expired':        critical,
        'waived':         sum(1 for s in statuses if s == 'WAIVED'),
        'next_due_date':  next_due['due_date'] if next_due else None,
        'next_due_label': next_due['label'] if next_due else None,
        'next_due_in_days': next_due['days_remaining'] if next_due else None,
        'alert_level':    'CRITICAL' if critical else ('WARNING' if warning else 'OK'),
        'warning_window_days': EXPIRY_WARNING_DAYS,
    }


# =============================================================================
# Identite du titulaire du carnet
# =============================================================================

def _unit_block(unit):
    if unit is None:
        return None
    return {
        'id':        unit.id,
        'code':      unit.code,
        'name':      unit.name,
        'unit_type': unit.unit_type,
        'unit_type_label': unit.get_unit_type_display(),
        'location':  unit.location,
        'country':   unit.country,
    }


def _seniority_years(hire_date, today):
    """Anciennete en annees revolues, ou None si la date d'embauche manque."""
    if not hire_date:
        return None
    years = today.year - hire_date.year
    if (today.month, today.day) < (hire_date.month, hire_date.day):
        years -= 1
    return max(years, 0)


def agent_identity(agent, today=None) -> dict | None:
    """
    Premiere page du carnet : qui est le titulaire.

    `profession` est la specialite technique du profil agent (controle
    aerien, meteo, telecommunications…) : c'est elle qui qualifie le metier
    exerce dans l'unite. Les roles fonctionnels sont donnes a part, car un
    agent peut etre a la fois technicien et evaluateur.
    """
    if agent is None:
        return None

    today = today or _today()
    profile = getattr(agent, 'agent_profile', None)
    specialty = getattr(profile, 'specialty', None) if profile else None
    unit = getattr(profile, 'unit', None) if profile else None

    photo = None
    if getattr(agent, 'photo', None):
        try:
            photo = agent.photo.url
        except ValueError:
            # Fichier absent du stockage : l'en-tete doit rester lisible.
            photo = None

    roles = [role.role for role in agent.user_roles.all() if role.is_active]

    return {
        'id':         agent.id,
        'matricule':  agent.matricule,
        'last_name':  agent.last_name,
        'first_name': agent.first_name,
        'full_name':  agent.full_name,
        'email':      agent.email,
        'phone':      agent.phone,
        'photo':      photo,
        'profession':      specialty.name if specialty else None,
        'profession_code': specialty.code if specialty else None,
        'roles':           roles,
        'career_status':       profile.status if profile else None,
        'career_status_label': profile.get_status_display() if profile else None,
        'unit':               _unit_block(unit),
        'hire_date':          profile.hire_date if profile else None,
        'qualification_date': profile.qualification_date if profile else None,
        'seniority_years':    _seniority_years(
            profile.hire_date if profile else None, today,
        ),
    }
