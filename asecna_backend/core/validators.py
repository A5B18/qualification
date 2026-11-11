"""
Validateurs métier partagés.
"""

import re
from django.core.exceptions import ValidationError


# =============================================================================
# Format du matricule ASECNA
# =============================================================================

MATRICULE_PATTERN = re.compile(r'^ASE-\d{4}-\d{4}$')


def validate_matricule(value: str):
    """
    Valide le format du matricule ASECNA : ASE-YYYY-NNNN
    Exemples valides : ASE-2024-0001, ASE-1998-9999
    """
    if not MATRICULE_PATTERN.match(value):
        raise ValidationError(
            f"Le matricule '{value}' est invalide. "
            "Format attendu : ASE-YYYY-NNNN (ex: ASE-2024-0001)"
        )


# =============================================================================
# Score (0-100)
# =============================================================================

def validate_score(value):
    """Valide qu'un score est compris entre 0 et 100."""
    if not (0 <= value <= 100):
        raise ValidationError(f"Le score {value} doit être compris entre 0 et 100.")


# =============================================================================
# Numéro de téléphone (format international simplifié)
# =============================================================================

PHONE_PATTERN = re.compile(r'^\+?[1-9]\d{7,14}$')


def validate_phone(value: str):
    """Valide un numéro de téléphone au format international."""
    if value and not PHONE_PATTERN.match(value.replace(' ', '')):
        raise ValidationError(
            f"Le numéro de téléphone '{value}' est invalide. "
            "Format attendu : +221771234567"
        )
