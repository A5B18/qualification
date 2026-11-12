# Guide de tests — Système de Gestion des Agents ASECNA

Ce guide permet de vérifier **toutes** les fonctionnalités de l'application, à
la main, écran par écran. Chaque scénario indique le compte à utiliser, ce qu'il
faut faire et le résultat attendu.

Le jeu de données de démonstration est conçu pour que **chaque scénario trouve
déjà de quoi être testé** : aucune saisie préalable n'est nécessaire.

---

## Sommaire

1. [Préparation](#1-préparation)
2. [Comptes de test](#2-comptes-de-test)
3. [Tests automatisés](#3-tests-automatisés)
4. [Tests manuels par rôle](#4-tests-manuels-par-rôle)
5. [Tests des règles métier](#5-tests-des-règles-métier)
6. [Tests de sécurité et de cloisonnement](#6-tests-de-sécurité-et-de-cloisonnement)
7. [Tests de l'API via Swagger](#7-tests-de-lapi-via-swagger)
8. [Fiche de suivi à imprimer](#8-fiche-de-suivi)

---

## 1. Préparation

### 1.1 Lancer le backend

```powershell
cd asecna_backend
.\venv\Scripts\Activate.ps1
python manage.py migrate --settings=config.settings.development
python manage.py seed_demo --reset --settings=config.settings.development
python manage.py runserver --settings=config.settings.development
```

La commande `seed_demo` affiche en fin d'exécution l'inventaire des données
créées et le tableau des identifiants. `--reset` repart d'une base propre ;
sans ce drapeau, la commande complète l'existant sans créer de doublon.

### 1.2 Lancer le frontend

Dans un **second** terminal :

```powershell
cd asecna_frontend
npm install
npm run dev
```

| Interface | Adresse |
|---|---|
| Application React | http://localhost:5173 |
| API Swagger | http://127.0.0.1:8000/api/docs/ |
| API ReDoc | http://127.0.0.1:8000/api/redoc/ |
| Admin Django | http://127.0.0.1:8000/admin/ |

> Si le frontend doit viser un backend sur une autre adresse, renseigner
> `VITE_API_BASE_URL` dans `asecna_frontend/.env`.

### 1.3 Quel SGBD ?

- **Développement : SQLite** (`asecna_backend/db.sqlite3`), aucune configuration.
- **Production : PostgreSQL**, via les variables `DB_*` du fichier `.env`.
- Pour développer sur PostgreSQL : poser `USE_POSTGRES=True` dans `.env` et
  renseigner les `DB_*`, puis `python manage.py migrate` et `seed_demo`.

---

## 2. Comptes de test

Tous les comptes sont créés par `seed_demo`. Le mot de passe est **réappliqué à
chaque exécution** de la commande : ces identifiants fonctionnent donc toujours.

| Rôle | Matricule | Mot de passe | Sert à tester |
|---|---|---|---|
| Administrateur | `ASE-2024-0001` | `Admin2024` | Tout, statistiques globales, audit |
| Chef d'unité CNS | `ASE-2024-0010` | `Chef@2024!` | Validations, signatures ARCEP |
| Chef d'unité RSI | `ASE-2024-0011` | `Chef@2024!` | Second chef (cloisonnement) |
| Mentor | `ASE-2024-0020` | `Mentor@2024!` | Fiches de mentorat |
| Évaluateur | `ASE-2024-0030` | `Eval@2024!` | Corrections, scores, alertes |
| Évaluateur + Mentor | `ASE-2024-0031` | `Eval@2024!` | **Cumul de deux rôles** |
| Instructeur | `ASE-2024-0040` | `Instr@2024!` | Cours e-learning |
| Approbateur | `ASE-2024-0050` | `Appro@2024!` | Rapports, workflows |
| Agent — nouveau | `ASE-2024-0100` | `Agent@2024!` | Statut NEW |
| Agent — période d'essai | `ASE-2024-0101` | `Agent@2024!` | Statut PROBATION |
| Agent — mentorat | `ASE-2024-0102` | `Agent@2024!` | Statut MENTORED |
| Agent — formation | `ASE-2024-0103` | `Agent@2024!` | Statut TRAINEE |
| Agent — qualifié | `ASE-2024-0104` | `Agent@2024!` | Carnet ARCEP, maintien QF |
| Agent — qualifié 2 | `ASE-2024-0105` | `Agent@2024!` | Maintien QF **en retard** |
| Agent — suspendu | `ASE-2024-0106` | `Agent@2024!` | Statut SUSPENDED |
| Agent — retraité | `ASE-2024-0107` | `Agent@2024!` | Statut RETIRED |

### Agents dédiés aux scénarios de période d'essai

| Matricule | Situation |
|---|---|
| `ASE-2024-0110` | Période d'essai en cours, **échéance dans 10 jours** → alerte J-14 |
| `ASE-2024-0111` | Période d'essai **réussie** (85/100) |
| `ASE-2024-0112` | 1<sup>re</sup> tentative échouée (55/100), **2<sup>e</sup> en cours** |
| `ASE-2024-0113` | **Deux échecs** (48 puis 61/100) → agent non retenu |

---

## 3. Tests automatisés

À lancer avant toute démonstration : c'est le filet de sécurité.

```powershell
cd asecna_backend
python manage.py test --settings=config.settings.development
```

**Attendu : `Ran 204 tests ... OK`**

| Suite | Tests | Ce qu'elle couvre |
|---|---|---|
| `apps.*.tests` | 110 | Modèles, règles métier, contraintes de base |
| `apps.evaluations.tests_scoring` | 6 | Calcul du score d'une session d'examen |
| `tests.test_api_contract` | 45 | Vues, permissions, serializers, pages HTML |
| `tests.test_correction_workflow` | 25 | Workflow de correction via l'API, filtres de la fiche agent, cours, reset de mot de passe |
| `tests.test_workflow_ledger` | 17 | Registre d'approbation : alimentation par les 3 modules, unicité, cloisonnement |

> **Important — version de Django.** Le projet exige **Django 5.2.19**
> (`requirements/base.txt`). Avec une série 4.2 installée globalement, les 5
> tests de `HtmlPagesTest` échouent sur une incompatibilité
> Django 4.2 / Python 3.14 (`Context.__copy__`), sans aucun rapport avec le
> code du projet. Travaillez toujours dans le `venv` :
>
> ```powershell
> .\venv\Scripts\Activate.ps1
> python -c "import django; print(django.get_version())"   # doit afficher 5.2.19
> ```

### Tests du frontend

```powershell
cd asecna_frontend
npm test          # 29 tests (Vitest)
```

| Suite | Tests | Ce qu'elle couvre |
|---|---|---|
| `src/api/client.test.ts` | 11 | Taille de page par défaut, lecture des erreurs métier |
| `src/utils/dates.test.ts` | 11 | Règle d'alerte J-14 |
| `src/pages/evaluations/SessionDetailPage.test.tsx` | 7 | Écran de correction : bornes du barème, cloisonnement agent |

Pour une suite en particulier :

```powershell
python manage.py test tests.test_api_contract --settings=config.settings.development
python manage.py test apps.probation --settings=config.settings.development
```

### Vérifications complémentaires

```powershell
# Cohérence du projet
python manage.py check --settings=config.settings.development

# Aucune migration oubliée
python manage.py makemigrations --check --dry-run --settings=config.settings.development

# Schéma OpenAPI : attendu aucune sortie (ni erreur, ni avertissement)
python manage.py spectacular --file schema.yml --fail-on-warn --settings=config.settings.development
```

Côté frontend :

```powershell
cd asecna_frontend
npx tsc -b        # typage : aucune sortie = succès
npm run lint      # attendu : aucune erreur
npm test          # attendu : 29 tests passés
npm run build     # compilation de production
```

---

## 4. Tests manuels par rôle

### 4.1 Administrateur — `ASE-2024-0001` / `Admin2024`

| # | Action | Résultat attendu |
|---|---|---|
| A1 | Se connecter | Badge **🛡️ Administrateur**, menu de **12 entrées** |
| A2 | Tableau de bord | Bandeaux d'alerte, 4 compteurs, graphique **des 7 statuts** |
| A3 | Vérifier le graphique | Les 7 barres sont présentes (Nouveau, Probation, Mentorat, Formation, Qualifié, Suspendu, **Retraité**) |
| A4 | Menu **Agents** | Tableau de **23 agents** : matricule, nom complet, statut, unité, date de recrutement — **aucune cellule vide** |
| A5 | Rechercher `DIOP` | La liste se filtre sur l'agent correspondant. La recherche part au serveur : elle trouve aussi les agents absents de la première page |
| A6 | Filtrer par statut **Qualifié** | Seuls les agents qualifiés restent affichés, le compteur se met à jour |
| A7 | Cliquer sur un agent | Fiche détaillée, onglet **Profil** : statut, unité, spécialité, dates |
| A8 | Onglets de la fiche | Probation / Mentorat / ARCEP / Rapports affichent **uniquement** les données de cet agent |
| A9 | Onglets **Compétences / Certifications / Performances** | Compétences avec leur niveau 1-5, certifications (dont une **expirée** en rouge), performances sur 3 ans |
| A10 | Menu **Unités** | 5 unités, chacune avec **son nombre d'agents** (non nul) et son chef |
| A11 | Déplier une unité | Liste des agents de cette unité uniquement |
| A12 | Menu **Formations** | 6 formations, onglet **Cours** (dont 1 brouillon), 4 stages |
| A13 | Menu **Maintien QF** | 5 contrôles, dont 1 **en retard** signalé en rouge |
| A14 | Menu **Comptes & rôles** | Liste des comptes avec leurs rôles, boutons d'attribution et de révocation |
| A15 | Attribuer un rôle **Mentor** à un agent | La pastille du rôle apparaît sur sa ligne |
| A16 | Révoquer ce rôle (croix sur la pastille) | La pastille disparaît |
| A17 | **Réinitialiser** le mot de passe d'un agent | En développement, le mot de passe temporaire s'affiche dans un bandeau (le courriel ne part pas avec le backend `console`) |
| A18 | Menu **Journal d'audit**, onglet **Actions** | Chaque POST / PUT / PATCH / DELETE journalisé : méthode, endpoint, code, IP |
| A19 | Onglet **Connexions** | Connexions réussies **et** échouées |

### 4.2 Chef d'unité — `ASE-2024-0010` / `Chef@2024!`

| # | Action | Résultat attendu |
|---|---|---|
| C1 | Se connecter | Badge **👑 Chef d'unité**, menu de 7 entrées |
| C2 | Tableau de bord | Alertes « évaluation(s) à valider » et « mentorat(s) soumis » |
| C3 | Menu **Évaluations** | Une session en `PENDING_APPROVAL` avec son score provisoire |
| C4 | **Approuver** cette session | Statut → `GRADED`, le score devient officiel, `is_passed` calculé |
| C5 | Menu **Mentorat** | Une fiche en `SUBMITTED` |
| C6 | **Approuver** la fiche | Statut → `APPROVED`, date d'approbation renseignée |
| C7 | Reprendre une autre fiche et **Rejeter** | Un motif est exigé ; statut → `REJECTED` |
| C8 | Menu **Carnets ARCEP** | 14 carnets, avec le total d'heures par carnet |
| C9 | Déplier un carnet | 5 entrées : 3 marquées **signées**, 2 **non signées** |
| C10 | **Signer** le carnet | Les entrées récentes basculent à « signée ». La période est déduite automatiquement |
| C11 | Menu **Probations** | Les périodes en cours, dont une **en alerte J-14** (surlignée) |
| C12 | Menu **Rapports** | Les rapports soumis, avec possibilité d'approuver ou rejeter |

### 4.3 Évaluateur — `ASE-2024-0030` / `Eval@2024!`

C'est le rôle le plus riche : il porte le **workflow de correction en 4 étapes**.

| # | Action | Résultat attendu |
|---|---|---|
| E1 | Se connecter | Badge **📋 Évaluateur** |
| E2 | Tableau de bord | 3 alertes : sessions à corriger, probations à évaluer (**2**), maintiens QF en retard (**1**) |
| E3 | Menu **Évaluations** | Des sessions dans **les 5 états** : `SUBMITTED`, `CORRECTING`, `PENDING_APPROVAL`, `GRADED`, `REJECTED`. Les sessions à corriger affichent « N réponse(s) à corriger » |
| E4 | **Cliquer** sur la session `SUBMITTED` | L'écran de correction s'ouvre : chaque réponse de l'agent, son barème et la **réponse attendue** |
| E5 | Corriger une réponse (note + Correcte/Incorrecte + commentaire) | La note est enregistrée, le compteur « réponses corrigées » avance, la session passe à `CORRECTING` |
| E6 | Saisir un score hors barème (ex. 999 sur 10) | **Refusé avant envoi** : « Le score doit être compris entre 0 et 10 » et le bouton reste inactif |
| E7 | Saisir un score non numérique | **Refusé** : « Le score doit être un nombre » |
| E8 | Tenter de soumettre avant d'avoir tout corrigé | Le bouton **Soumettre au chef d'unité** reste inactif, avec le nombre de réponses restantes |
| E9 | Corriger **toutes** les réponses puis soumettre | Le score /100 est **calculé automatiquement** sur le barème de l'examen complet, statut → `PENDING_APPROVAL` |
| E9b | Vérifier la session de l'agent `mentoré` | `seed_demo` la livre avec **2 réponses sur 4 corrigées** : c'est le cas de test de E8 → E9 |
| E9c | Ouvrir une session **rejetée** par le chef | Le motif du rejet s'affiche en rouge ; la correction peut être reprise |
| E10 | Menu **Probations** | Les périodes à échéance proche |
| E11 | **Finaliser** une probation avec 85 | Statut → `PASSED` ; l'agent passe en mentorat |
| E12 | Finaliser une autre avec 55 | Statut → `FAILED` |
| E13 | Menu **Maintien QF** | Le contrôle en retard est visible |
| E14 | **Finaliser** un maintien avec 50 | Statut → `FAILED` et **l'agent passe automatiquement en SUSPENDU** |

### 4.4 Mentor — `ASE-2024-0020` / `Mentor@2024!`

| # | Action | Résultat attendu |
|---|---|---|
| M1 | Se connecter | Badge **🤝 Mentor**, menu de 4 entrées |
| M2 | Menu **Mes mentorats** | Uniquement **ses** fiches (3), pas celles des autres mentors |
| M3 | Créer une fiche | Agent, dates, objectifs ; statut initial `DRAFT` |
| M4 | Compléter et **Soumettre** | Choisir le chef d'unité ; statut → `SUBMITTED` |
| M5 | Tenter de modifier une fiche approuvée | Action indisponible |

### 4.5 Instructeur — `ASE-2024-0040` / `Instr@2024!`

| # | Action | Résultat attendu |
|---|---|---|
| I1 | Se connecter | Badge **🎓 Instructeur** |
| I2 | Menu **Formations**, onglet **Cours** | 4 cours, dont **1 brouillon non publié** |
| I3 | **Nouveau cours** | Titre, formation et contenu ; il naît en **brouillon** |
| I4 | **Publier** le cours | Pastille « Publié » ; il devient visible des agents |
| I5 | **Dépublier** | Retour en brouillon ; le cours disparaît de la vue des agents |
| I6 | Se reconnecter en **agent** (`ASE-2024-0104`), onglet **Cours** | Seuls les cours **publiés** apparaissent, aucun bouton de publication |

### 4.6 Approbateur — `ASE-2024-0050` / `Appro@2024!`

| # | Action | Résultat attendu |
|---|---|---|
| P1 | Se connecter | Badge **✅ Approbateur**, menu de **5 entrées** |
| P2 | Tableau de bord | Bandeau « décision(s) en attente au registre » et la liste nominative de ce qui attend |
| P3 | Menu **Rapports à approuver** | 2 rapports en `SUBMITTED` |
| P4 | **Approuver** un rapport | Statut → `APPROVED`, approbateur et date enregistrés |
| P5 | **Rejeter** un rapport | Statut → `REJECTED` avec l'avis saisi |
| P6 | Menu **Approbations** | Le registre : rapports, fiches de mentorat **et** corrections d'examen dans la même liste |
| P7 | Vérifier une ligne | Elle nomme l'objet, son module, l'agent concerné et qui l'a soumis |
| P8 | Cliquer sur une ligne | Renvoie vers l'écran du module d'origine, là où la décision se prend |
| P9 | Filtrer **Approuvés** | Les lignes portent le décideur, la date et l'avis |
| P10 | Filtrer par module **Corrections d'examen** | Seules les corrections restent |
| P11 | Approuver un rapport depuis son écran, revenir au registre | La ligne est passée à **Approuvé**, sans doublon |

### 4.7 Agent — `ASE-2024-0104` / `Agent@2024!`

| # | Action | Résultat attendu |
|---|---|---|
| G1 | Se connecter | Badge **👤 Agent**, menu de 7 entrées **au « Mon/Ma »** |
| G2 | Tableau de bord | Carte « Mon parcours » avec le statut **Qualifié ✓** |
| G3 | Menu **Mon carnet ARCEP** | **Son seul** carnet, avec son total d'heures |
| G4 | Déplier le carnet | 3 entrées signées, 2 non signées |
| G5 | **Ajouter une entrée** | Activité + durée ; elle apparaît comme non signée |
| G6 | Menu **Ma probation** | Uniquement ses propres périodes |
| G7 | Menu **Mes évaluations** | Uniquement ses sessions |
| G8 | Menu **Formations**, onglet **Cours** | Uniquement les cours **publiés** |
| G9 | Sur un examen **publié**, cliquer **Passer l'épreuve** | L'écran de composition s'ouvre : les énoncés, **sans la bonne réponse** |
| G10 | Répondre puis **Enregistrer cette réponse** | La réponse est conservée côté serveur ; la pastille « enregistrée » apparaît |
| G11 | Recharger la page | Les réponses déjà enregistrées sont **toujours là** (le brouillon vit sur le serveur) |
| G12 | **Rendre ma copie** | Un avertissement signale les questions laissées vides (notées 0) ; après confirmation, statut → `SUBMITTED` |
| G13 | Rouvrir l'épreuve | « Votre copie a déjà été rendue » — elle n'est plus modifiable |
| G14 | Ouvrir **sa** session corrigée | Il relit sa copie et les commentaires, **sans** voir la réponse attendue |
| G15 | Icône **Mon profil** (en haut à droite) | Son parcours, ses coordonnées modifiables et le changement de mot de passe |
| G16 | Changer son mot de passe avec une confirmation différente | Refusé : « La confirmation ne correspond pas » |
| G17 | Changer son mot de passe correctement, puis se reconnecter | Le nouveau mot de passe fonctionne |

### 4.8 Cumul de rôles — `ASE-2024-0031` / `Eval@2024!`

| # | Action | Résultat attendu |
|---|---|---|
| R1 | Se connecter | Ce compte porte **Évaluateur + Mentor** |
| R2 | Vérifier le menu | Le rôle le plus élevé détermine la vue (Évaluateur) |
| R3 | Accéder aux mentorats | L'accès reste autorisé grâce au second rôle |

---

## 5. Tests des règles métier

Ce sont les règles que le jury est le plus susceptible de questionner.

### 5.1 Période d'essai

| Règle | Comment la vérifier | Attendu |
|---|---|---|
| Note minimale 70/100 | Finaliser avec 69 puis avec 70 | 69 → `FAILED`, 70 → `PASSED` |
| 2 tentatives maximum | Voir `ASE-2024-0113` (2 échecs) puis tenter une 3<sup>e</sup> | Création refusée |
| Pas de 2<sup>e</sup> si la 1<sup>re</sup> est réussie | Tenter une 2<sup>e</sup> sur `ASE-2024-0111` | Refusé : « La 1<sup>re</sup> tentative a été réussie » |
| Durée ≈ 3 mois | Créer une période de 5 jours | Refusé : « doit être approximativement de 3 mois (80 à 100 jours) » |
| Alerte à J-14 | Tableau de bord Évaluateur | `ASE-2024-0110` apparaît (échéance J+10) |

### 5.2 Évaluations

| Règle | Comment la vérifier | Attendu |
|---|---|---|
| Correction **manuelle** | Soumettre une copie | Aucun score automatique : l'évaluateur saisit chaque note |
| Workflow en 4 étapes | Dérouler E4 → E9 → C4 | `SUBMITTED` → `CORRECTING` → `PENDING_APPROVAL` → `GRADED` |
| Score calculé sur l'examen complet | Ne répondre qu'à 1 question sur 4 et la réussir | **25/100**, et non 100/100. L'écran de correction liste les questions sans réponse |
| Rejet par le chef | Rejeter une correction | Statut `REJECTED`, motif obligatoire, l'évaluateur peut recorriger |
| Score borné au barème | Saisir 999 sur une question à 10 points | Refusé **côté interface**, avant même l'appel serveur |
| Le corrigé ne fuit pas | Composer une épreuve en tant qu'agent | Les énoncés ne portent pas `correct_answer` |
| Un examen vide n'est pas publiable | Créer un examen puis tenter de le publier sans question | Le bouton **Publier** reste inactif ; par l'API, 400 explicite |

### 5.3 Carnet ARCEP

| Règle | Comment la vérifier | Attendu |
|---|---|---|
| Création automatique | Passer un agent en `QUALIFIED` depuis l'admin Django | Son carnet est créé par signal |
| Un seul carnet par agent | Tenter d'en créer un second | Refusé (relation un-à-un) |
| Signature par le chef d'unité | Essayer de signer en tant qu'agent | Refusé (403) |
| Validité = couverture par une signature | Comparer entrées anciennes et récentes | Anciennes « signées », récentes « non signées » |

### 5.4 Maintien de qualification

| Règle | Comment la vérifier | Attendu |
|---|---|---|
| Seuil 70/100 | Finaliser avec 69 puis 70 | 69 → `FAILED`, 70 → `PASSED` |
| Suspension sur échec | Finaliser le maintien de `ASE-2024-0105` avec 50 | L'agent passe en **SUSPENDED** |
| Dispense | En tant que chef d'unité, dispenser un contrôle | Statut → `WAIVED` |
| Détection des retards | Menu Maintien QF | `ASE-2024-0105` signalé en retard |

### 5.5 Registre d'approbation

| Règle | Comment la vérifier | Attendu |
|---|---|---|
| Un brouillon n'y figure pas | Créer un rapport sans le soumettre | Absent du registre |
| La soumission l'y inscrit | Soumettre ce rapport | Une ligne `SUBMITTED` apparaît |
| Une seule ligne par objet | Rejeter puis resoumettre le même rapport | Toujours **une** ligne, remise à `SUBMITTED` |
| La décision est tracée | Approuver avec un avis | Décideur, date et avis enregistrés |
| Les 3 modules l'alimentent | Soumettre un rapport, un mentorat, une correction | Les trois apparaissent dans la même liste |
| La trace survit à l'objet | Supprimer un objet soumis | La ligne reste, marquée « objet supprimé » |

### 5.6 Qualification initiale

| Règle | Comment la vérifier | Attendu |
|---|---|---|
| Seuil 80/100 (EAMAC) | Consulter « Qualification initiale CNS (EAMAC) » | `passing_score` = 80 |

---

## 6. Tests de sécurité et de cloisonnement

| # | Test | Attendu |
|---|---|---|
| S1 | Ouvrir http://localhost:5173/dashboard sans être connecté | Redirection vers `/login` |
| S2 | Ouvrir http://localhost:5173/page-inexistante | Page « Page introuvable » (pas d'écran blanc) |
| S3 | Se connecter avec un mauvais mot de passe | Message « Matricule ou mot de passe incorrect » |
| S4 | Se connecter avec un matricule mal formé | Refusé (format attendu `ASE-YYYY-NNNN`) |
| S5 | En tant qu'**agent**, aller sur `/units` par l'URL | Aucune donnée d'autres agents n'est exposée |
| S6 | En tant qu'**agent**, appeler `/api/v1/audit/logs/` | **403** (réservé à l'administrateur) |
| S7 | En tant que **chef d'unité**, créer un utilisateur via l'API | **403** (réservé à l'administrateur) |
| S8 | Un agent tente de consulter le carnet ARCEP d'un autre | **404** (cloisonnement) |
| S9 | **Se déconnecter** | Retour à `/login` ; le jeton est blacklisté côté serveur |
| S10 | Après déconnexion, revenir en arrière dans le navigateur | Pas d'accès aux données ; redirection vers `/login` |
| S11 | Laisser la session ouverte > 60 min puis agir | Le jeton est renouvelé **sans déconnexion** |
| S12 | Se connecter à l'admin Django avec le matricule | Le formulaire attend bien un matricule |
| S13 | En tant que **chef d'unité**, ouvrir `/audit` par l'URL | Écran « Accès réservé à l'administrateur » (pas d'erreur brute) |
| S14 | En tant que **chef d'unité**, ouvrir `/users` par l'URL | Même message : aucune donnée de compte n'est exposée |
| S15 | En tant qu'**agent**, ouvrir la session d'examen d'un autre par son URL | « Session introuvable, ou vous n'y avez pas accès » (404 côté API) |
| S16 | En tant qu'**agent**, appeler `/api/v1/evaluations/sessions/<id>/answers/` sur la copie d'un autre | **404** (cloisonnement) |
| S17 | En tant qu'**agent**, ouvrir `/workflows` | Uniquement **ses** soumissions, avec un message l'indiquant |
| S18 | En tant qu'**agent**, appeler `/api/v1/workflows/pending/` | **403** (réservé aux décideurs) |

### Vérifier la traçabilité

En tant qu'administrateur, après avoir effectué quelques actions :

| # | Test | Attendu |
|---|---|---|
| T1 | `/api/v1/audit/logs/` | Chaque POST/PUT/PATCH/DELETE est journalisé (méthode, endpoint, code, IP) |
| T2 | Vérifier qu'aucun mot de passe n'y figure | Les champs `password` sont retirés des journaux |
| T3 | `/api/v1/audit/logins/` | Connexions **réussies et échouées** enregistrées |

---

## 7. Tests de l'API via Swagger

Ouvrir http://127.0.0.1:8000/api/docs/

| # | Action | Résultat attendu |
|---|---|---|
| W1 | Vérifier la liste des endpoints | Tous les modules présents, dont `/auth/logout/` |
| W2 | `POST /api/v1/auth/login/` avec `ASE-2024-0001` / `Admin2024` | 200, avec `access`, `refresh` et un bloc `user` contenant `roles` et `is_admin` |
| W3 | Cliquer **Authorize** et coller le jeton `access` | Les appels suivants sont authentifiés |
| W4 | `GET /api/v1/auth/me/` | Profil complet : `full_name`, `roles`, `status`, `agent_profile` |
| W5 | `GET /api/v1/auth/users/?page_size=100` | 23 agents, chacun avec `user_detail` et `unit_detail` |
| W6 | `GET /api/v1/probation/evaluation-due/` | Les périodes à échéance J-14 |
| W7 | `GET /api/v1/training/maintenances/overdue/` | Les contrôles en retard |
| W8 | `POST /api/v1/auth/token/refresh/` avec le `refresh` | 200, et un **nouveau** `refresh` est renvoyé |
| W9 | Rappeler `/token/refresh/` avec l'**ancien** `refresh` | **401** (jeton blacklisté après rotation) |
| W10 | `GET /api/v1/arcep/entries/?book=1` | Uniquement les entrées de ce carnet |
| W11 | `POST /api/v1/probation/` avec une durée de 5 jours | **400** avec le message métier (pas de 500) |
| W12 | `GET /api/v1/evaluations/sessions/{id}/answers/` | La copie : réponses, barèmes, corrections, questions sans réponse |
| W13 | `GET /api/v1/evaluations/exams/{id}/questions/` en tant qu'agent | Les énoncés **sans** `correct_answer` |
| W14 | `POST /api/v1/evaluations/exams/{id}/publish/` sur un examen sans question | **400** « Un examen sans question ne peut pas etre publie » |
| W15 | `GET /api/v1/agents/skills/?agent=<id>` | Uniquement les compétences de cet agent |
| W16 | `GET /api/v1/training/courses/?is_published=false` en tant qu'instructeur | Uniquement ses brouillons |
| W17 | `POST /api/v1/auth/users/{id}/reset-password/` | `delivered_by_email` indique si le courriel est parti ; `temp_password` n'apparaît **que** s'il n'a pas pu partir |
| W18 | `GET /api/v1/workflows/pending/` | Les décisions en attente, chacune avec `module`, `module_label` et `target` |
| W19 | `GET /api/v1/workflows/?module=examsession` | Uniquement les corrections d'examen |
| W20 | `POST /api/v1/reports/{id}/submit/` puis `GET /api/v1/workflows/?object_id={id}` | La ligne de registre vient d'être créée |

---

## 8. Fiche de suivi

À imprimer et cocher pendant la campagne de tests.

```
PREPARATION
[ ] venv active (Django 5.2.19)          [ ] Frontend lance
[ ] seed_demo execute                    [ ] 204 tests backend OK
[ ] 29 tests frontend OK                 [ ] npm run lint sans erreur

PAR ROLE
[ ] A1-A19   Administrateur
[ ] C1-C12   Chef d'unite
[ ] E1-E14   Evaluateur (dont E4-E9 : ecran de correction)
[ ] M1-M5    Mentor
[ ] I1-I6    Instructeur (onglet Cours)
[ ] P1-P11   Approbateur (dont le registre)
[ ] G1-G17   Agent (dont G9-G14 : composition d'examen)
[ ] R1-R3    Cumul de roles

REGLES METIER
[ ] 5.1 Periode d'essai (5 regles)
[ ] 5.2 Evaluations (7 regles)
[ ] 5.3 Carnet ARCEP (4 regles)
[ ] 5.4 Maintien de qualification (4 regles)
[ ] 5.5 Registre d'approbation (6 regles)
[ ] 5.6 Qualification initiale

SECURITE
[ ] S1-S18   Authentification et cloisonnement
[ ] T1-T3    Tracabilite

API
[ ] W1-W20   Swagger
```

---

## Annexe — Remettre la base à zéro

```powershell
cd asecna_backend

# Repartir du jeu de démonstration (conserve les comptes et le référentiel)
python manage.py seed_demo --reset --settings=config.settings.development

# Repartir d'une base totalement vierge
Remove-Item db.sqlite3
python manage.py migrate --settings=config.settings.development
python manage.py loaddata fixtures/initial_data.json --settings=config.settings.development
python manage.py seed_demo --settings=config.settings.development
```
