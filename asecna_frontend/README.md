# ASECNA Frontend — Système de Gestion des Agents

Interface React / TypeScript du système de gestion du parcours des agents ASECNA.
Elle consomme l'API REST décrite dans [`../asecna_backend/README.md`](../asecna_backend/README.md).

---

## 🚀 Démarrage

```powershell
cd asecna_frontend
npm install
copy .env.example .env      # renseigne VITE_API_BASE_URL
npm run dev
```

| Interface | Adresse |
|---|---|
| Application | http://localhost:5173 |
| API attendue | `VITE_API_BASE_URL`, par défaut `http://127.0.0.1:8000` |

Le backend doit tourner en parallèle, avec `seed_demo` exécuté : les comptes de
démonstration et le déroulé de test sont dans
[`../GUIDE_DE_TESTS.md`](../GUIDE_DE_TESTS.md).

---

## 📜 Commandes

| Commande | Effet |
|---|---|
| `npm run dev` | Serveur de développement avec rechargement à chaud |
| `npm run build` | Compilation de production (typage puis bundle) |
| `npm run lint` | ESLint — doit rester **sans erreur** |
| `npm test` | Vitest, une passe (29 tests) |
| `npm run test:watch` | Vitest en continu |
| `npx tsc -b` | Typage seul |

---

## 🗂️ Organisation

```
src/
├── api/
│   ├── client.ts     ← Axios : jetons JWT, rafraîchissement, taille de page, erreurs
│   └── index.ts      ← Une fonction par endpoint, groupée par module
├── components/
│   └── Layout.tsx    ← Menu latéral par rôle, en-tête, photo de profil
├── pages/
│   ├── auth/         ← Connexion
│   ├── dashboard/    ← Tableau de bord, une vue par rôle (7)
│   ├── agents/       ← Annuaire et fiche agent (8 onglets)
│   ├── probation/    ← Périodes d'essai
│   ├── mentoring/    ← Fiches de mentorat
│   ├── arcep/        ← Carnets, entrées, signatures
│   ├── evaluations/  ← Liste, composition d'examen, correction, passage d'épreuve
│   ├── training/     ← Formations, cours, stages, maintien de qualification
│   ├── reports/      ← Rapports de période
│   ├── units/        ← Unités organisationnelles
│   ├── workflows/    ← Registre transversal des approbations
│   ├── users/        ← Comptes et rôles (ADMIN)
│   ├── audit/        ← Journal d'audit et connexions (ADMIN)
│   └── profile/      ← Mon profil, changement de mot de passe
├── store/            ← Contexte d'authentification
├── types/            ← Interfaces et libellés partagés
└── utils/            ← Dates, règle J-14
```

---

## 🔑 Authentification

Le contexte (`src/store/AuthContext.tsx`) conserve `access` et `refresh` dans
`localStorage` et récupère le profil complet (rôles, statut, parcours) via
`/auth/me/`.

Le client axios gère seul la rotation : sur un 401, il rafraîchit le jeton et
rejoue la requête. Un seul rafraîchissement est en vol à la fois — le backend
tourne avec `ROTATE_REFRESH_TOKENS` et `BLACKLIST_AFTER_ROTATION`, N
rafraîchissements concurrents invalideraient tout sauf le premier.

---

## 🧭 Menus par rôle

Le rôle le plus habilité détermine la vue. Un compte qui cumule deux rôles garde
l'accès aux écrans des deux.

| Rôle | Entrées de menu |
|---|---|
| Administrateur | 13, dont **Approbations**, **Comptes & rôles** et **Journal d'audit** |
| Chef d'unité | 8 |
| Évaluateur | 5 |
| Approbateur | 5, dont **Approbations** |
| Mentor | 4 |
| Instructeur | 4 |
| Agent | 7, au « Mon / Ma » |

---

## 📄 Pagination

Le backend pagine à 20 (`core.pagination.StandardPagination`). Le client demande
`page_size=200` par défaut sur tout GET qui ne précise ni `page_size` ni `page`
(`DEFAULT_PAGE_SIZE` dans `src/api/client.ts`).

Sans cela les listes étaient tronquées en silence : la page Agents affichait 20
des 23 agents, sa recherche — purement locale — ne trouvait pas les trois
derniers, et le tableau de bord calculait compteurs et graphique sur la première
page seulement. Les recherches et filtres partent désormais au serveur
(`?search=`, `?status=`).

---

## 🧪 Tests

```powershell
npm test
```

| Suite | Tests | Portée |
|---|---|---|
| `src/api/client.test.ts` | 11 | Taille de page par défaut, lecture des erreurs métier normalisées |
| `src/utils/dates.test.ts` | 11 | Règle d'alerte J-14 |
| `src/pages/evaluations/SessionDetailPage.test.tsx` | 7 | Écran de correction : bornes du barème, saisie non numérique, cloisonnement agent |

Vitest tourne sous `jsdom`, avec `@testing-library/react`. La mise en place
commune est dans `src/test/setup.ts`.

---

## 🎨 Couleurs

Onze familles de couleurs cohabitaient : trois quasi identiques (`asecna`,
`indigo`, `blue`), deux violets, trois tons chauds et deux verts. Deux
éléments de même nature portaient des couleurs différentes d'un écran à
l'autre. L'ensemble tient désormais en **six familles**, définies dans le bloc
`@theme` de [`src/index.css`](src/index.css) — seule source de vérité.

| Famille | Teinte | Emploi |
|---|---|---|
| `asecna-*` | sarcelle | Marque : navigation, actions principales, liens |
| `success-*` | émeraude | Approuvé, qualifié, réussi, publié |
| `warning-*` | ambre | En attente, en cours, en retard, brouillon |
| `danger-*` | rouge | Échoué, suspendu, rejeté, expiré |
| `info-*` | ciel | Mentorat, rapports, bandeaux d'information |
| `accent-*` | violet | Évaluations et formations |

Le gris de Tailwind reste utilisé pour les neutres. **N'employez pas
`bg-green-*`, `text-blue-*` ou leurs voisins directement** : passez par la
famille sémantique, sans quoi la dispersion reviendra.

### Lisibilité

Les échelles sont décalées d'un cran par rapport à celles de Tailwind pour que
la nuance **600** — celle que portent les boutons à texte blanc — atteigne le
rapport 4,5:1 exigé par WCAG AA. Le sarcelle 600 de Tailwind (`#0d9488`) ne
plafonne qu'à 3,9:1 : son libellé blanc serait illisible pour une partie des
utilisateurs.

Contraste mesuré sur blanc : sarcelle 5,47 · émeraude 5,48 · rouge 4,83
· ciel 5,93 · violet 5,70. L'ambre ne porte jamais de texte blanc ; son texte
prend la nuance 700 (5,02 sur blanc).

### Graphiques

Recharts peint ses barres en CSS inline : il lui faut une valeur, pas une
classe. `AgentStatusChartColors` ([`src/types/index.ts`](src/types/index.ts))
donne les nuances 500 des mêmes familles, pour qu'une barre et sa pastille
portent la même couleur. Le graphique se dérive de `AgentStatusLabels` : un
statut ajouté au backend y apparaît sans toucher au tableau de bord.

> `tailwind.config.js` ne définit **aucune** couleur. En Tailwind 4 il n'est lu
> que si une directive `@config` le désigne depuis le CSS, ce qui n'est pas le
> cas : il dupliquait la palette sans effet, et les deux définitions avaient
> divergé.

---

## 🔀 Registre d'approbation

L'écran `/workflows` lit `ApprovalWorkflow`, le registre transversal alimenté
par les rapports, les fiches de mentorat et les corrections d'examen. Il montre
au même endroit tout ce qui attend une décision, avec l'objet concerné, l'agent
et un lien vers l'écran d'origine.

La décision se prend **dans le module d'origine**, pas depuis le registre :
c'est lui qui porte la règle métier (un rapport approuvé enregistre un avis, une
correction approuvée rend le score officiel). Le registre sert à voir et à
retracer.

---

## 📦 Découpage du bundle

Chaque route est chargée à la demande (`lazy()` dans `src/App.tsx`).
L'application partait auparavant en un seul paquet de plus de 800 kB,
téléchargé en entier avant le premier écran — écrans d'administration compris.
Le paquet initial fait désormais ~310 kB (~100 kB compressé).

---

## 🔧 Variables d'environnement

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## 🛠️ Pile technique

| Paquet | Rôle |
|---|---|
| React 19 + TypeScript | Interface |
| Vite 7 | Build et serveur de développement |
| React Router 6 | Navigation |
| TanStack Query 5 | Données serveur, cache, invalidation |
| Axios | Client HTTP, intercepteurs JWT |
| Tailwind CSS 4 | Styles |
| Recharts | Graphique du tableau de bord |
| lucide-react | Icônes |
| Vitest + Testing Library | Tests |
