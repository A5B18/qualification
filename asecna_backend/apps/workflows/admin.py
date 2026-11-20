"""
Admin de l'app workflows.

Le registre d'approbation se consulte par l'API (`/api/v1/workflows/`) et par
l'écran « Registre » du frontend. Aucun modèle n'est donc exposé ici : une
décision ne doit pas pouvoir être réécrite à la main depuis l'administration,
elle appartient aux actions `approve` / `reject` qui l'horodatent et la
rattachent à son auteur.

Ce fichier importait `django.contrib.admin` sans rien enregistrer, sous un
en-tête qui annonçait « workflows, arcep, reports, audit, agents » — ces
quatre dernières apps ayant en réalité leur propre `admin.py`.
"""
