# Berceau — gestion industrielle

## Authentification

- **Connexion** : identifiant (`User.username`) + **code** (mot de passe hashé Django, jamais stocké en clair).
- **Session** : cookies de session Django + protection CSRF (aligné avec le client React / Axios).
- **Endpoints JSON (SPA)** :
  - `POST /auth/login/` — corps JSON `{ "identifiant": "...", "code": "..." }`
  - `POST /auth/logout/`
  - `GET /auth/me/` — profil courant (rôle, shift PSP si applicable, permissions).

## Rôles (RBAC)

| Rôle   | Description |
|--------|-------------|
| **ADMIN** | Accès complet (superuser migré ou profil explicite). |
| **RU**    | Responsable d’unité : lecture/écriture sur toutes les équipes et shifts. |
| **PSP**   | Opérateur : accès limité à l’**équipe** et au **shift** de l’**effectif** lié au profil (`UserAccessProfile.effectif` → `OperateurEffectif`). |

Le **shift effectif PSP** est relu en base à **chaque requête** (changement sur l’effectif appliqué immédiatement).

- **PSP** : pas de suppression sur les APIs concernées ; listes filtrées sur le shift ; création/mise à jour refusées si le shift ou l’équipe ne correspondent pas (**403**).
- **RU / ADMIN** : pas de filtre shift obligatoire sur les mêmes APIs.

## Démarrage (rappel)

```bash
python manage.py migrate
python manage.py runserver
```

Frontend (développement) :

```bash
cd frontend && npm install && npm run dev
```

Le proxy Vite expose `/auth` vers Django (`vite.config.ts`). Tests unitaires SPA (ex. verrouillage shift) : `npm run test` dans `frontend/`.

## Logo Stellantis (déploiement)

- Fichiers : `static/brand/stellantis-logo.png` (page login Django) et `frontend/public/brand/stellantis-logo.png` (barre latérale React).
- Après modification du logo : garder les deux copies identiques, puis `npm run build --workspace gestion-industrielle-ui`.
- Détails : `static/brand/README.md`.

## Module Alerte Panne Berceau

- Page React: `/app/berceau/arret`
- API principales:
  - `GET /berceau/modules/`
  - `GET /berceau/modules/{id}/postes/`
  - `GET /berceau/postes/{id}/moyens/`
  - `GET|POST /panne-types/`
  - `GET /arrets/temps-auto/`
  - `GET|POST /alertes-pannes/`
  - `GET|PATCH|DELETE /alertes-pannes/{id}/`
  - `GET /alertes-pannes/export/?format=csv|excel`
- Seed matrice Module/Poste/Moyen:
  - `python manage.py seed_berceau_matrix`
  - Fichier source initial: `app/seeds/berceau_matrix.json` (a remplacer par la matrice metier reelle).
