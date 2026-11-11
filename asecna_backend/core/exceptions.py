"""
Gestionnaire d'exceptions global DRF.

Normalise TOUTES les réponses d'erreur en :
{
    "error": {
        "code": "validation_error",
        "message": "Message lisible",
        "details": { ... }   # optionnel
    }
}
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Handler d'exceptions custom — appelé par DRF pour chaque erreur.
    Surcharge exception_handler de DRF avant de normaliser la réponse.
    """
    # Les ValidationError de Django (levees par Model.full_clean() dans save())
    # ne sont pas reconnues par DRF : sans cette conversion elles remontent en 500
    # alors qu'il s'agit d'une erreur de saisie de l'utilisateur.
    if isinstance(exc, DjangoValidationError):
        details = _django_validation_details(exc)
        return Response(
            {
                'error': {
                    'code': 'validation_error',
                    'message': _first_django_message(details),
                    'details': details,
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Violation de contrainte en base (unicite, check constraint...) -> 409
    if isinstance(exc, IntegrityError):
        logger.warning("IntegrityError: %s", exc)
        return Response(
            {
                'error': {
                    'code': 'conflict',
                    'message': "Cette operation viole une contrainte d'integrite "
                               "(doublon ou regle metier non respectee).",
                    'details': None,
                }
            },
            status=status.HTTP_409_CONFLICT,
        )

    # Objet introuvable hors DRF -> 404
    if isinstance(exc, ObjectDoesNotExist):
        return Response(
            {'error': {'code': 'not_found', 'message': 'Ressource introuvable.', 'details': None}},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Laisser DRF traiter l'exception d'abord
    response = exception_handler(exc, context)

    if response is None:
        # Exception non gérée par DRF (ex: exception Python native)
        logger.exception("Unhandled exception in view", exc_info=exc)
        return Response(
            {
                'error': {
                    'code': 'internal_server_error',
                    'message': 'Une erreur interne est survenue.',
                    'details': None,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Normaliser la structure de la réponse
    error_code = _get_error_code(response.status_code, exc)
    message = _get_error_message(response.data)
    details = _get_error_details(response.data)

    response.data = {
        'error': {
            'code': error_code,
            'message': message,
            'details': details,
        }
    }

    return response


# =============================================================================
# Helpers
# =============================================================================

def _get_error_code(status_code: int, exc) -> str:
    """Dérive un code machine lisible depuis le code HTTP."""
    code_map = {
        400: 'bad_request',
        401: 'unauthorized',
        403: 'forbidden',
        404: 'not_found',
        405: 'method_not_allowed',
        409: 'conflict',
        429: 'too_many_requests',
        500: 'internal_server_error',
    }
    # Certaines exceptions DRF ont un attribut default_code
    if hasattr(exc, 'default_code'):
        return exc.default_code
    return code_map.get(status_code, 'error')


def _get_error_message(data) -> str:
    """Extrait un message lisible depuis les données d'erreur DRF."""
    if isinstance(data, dict):
        # Erreur de validation : premier message du premier champ
        if 'detail' in data:
            detail = data['detail']
            return str(detail) if not isinstance(detail, list) else str(detail[0])
        # Prendre le premier message disponible
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f"{key}: {value[0]}"
            if isinstance(value, str):
                return f"{key}: {value}"
    if isinstance(data, list) and data:
        return str(data[0])
    return 'Une erreur est survenue.'


def _get_error_details(data) -> dict | None:
    """Renvoie les détails structurés si c'est une erreur de validation."""
    if isinstance(data, dict) and 'detail' not in data:
        return data
    return None

def _django_validation_details(exc: DjangoValidationError) -> dict:
    """Normalise une ValidationError Django en dict {champ: [messages]}."""
    if hasattr(exc, 'message_dict'):
        return dict(exc.message_dict)
    return {'detail': list(exc.messages)}


def _first_django_message(details: dict) -> str:
    """Premier message lisible d'une ValidationError Django."""
    # Les erreurs non liees a un champ sont les plus parlantes : les montrer d'abord
    for key in ('__all__', 'detail'):
        if details.get(key):
            return str(details[key][0])
    for key, msgs in details.items():
        if msgs:
            return f"{key}: {msgs[0]}"
    return 'Donnees invalides.'
