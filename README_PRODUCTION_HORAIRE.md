# Production Berceau - Saisie Horaire H1..H8

## Nouveaux champs (model `ProductionBerceau`)
- `rebut_h1..rebut_h8`
- `retouche_h1..retouche_h8`
- `validated_hours_mask` (bitmask des heures validees)

## Calculs backend (source de verite)
- `volume = sum(production_h1..h8)`
- `rebut = sum(rebut_h1..h8)`
- `retouche = sum(retouche_h1..h8)`
- `temps_arrets = sum(temps_arrets_h1..h8)`
- `ro_percent = (volume / objectif) * 100` (0 si `objectif <= 0`)
- `nro_total = max(objectif - volume, 0)`

## Endpoint ajoute
- `POST /api/berceau/production/{id}/validate-hour/`
  - payload: `{ "hour": 1..8 }`
  - regle sequentielle active: impossible de valider `Hx` si `Hx-1` n'est pas validee

## Regles droits / verrouillage
- PSP: pas de suppression (inchangé), et ne peut pas modifier les champs horaires d'une heure deja validee.
- RU/ADMIN: peuvent modifier une heure deja validee (override autorise).
- Restriction shift/equipe PSP conservee (inchangée).

## Tests rapides
- Backend:
  - `python manage.py test`
- Frontend:
  - `cd frontend && npm test`
  - `cd frontend && npm run build`
  - `cd frontend && npm run lint`

