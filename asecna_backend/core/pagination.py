"""
Pagination partagee de l'API.

DRF n'autorise pas le client a choisir la taille de page par defaut : le
frontend demandait `?page_size=200` (liste complete des agents d'une unite)
et recevait silencieusement 20 elements. Cette classe active le parametre
tout en bornant la taille maximale.
"""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 500
