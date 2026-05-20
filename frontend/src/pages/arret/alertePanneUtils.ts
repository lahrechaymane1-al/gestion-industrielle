export type CascadeState = {
  moduleId?: number;
  posteId?: number;
  moyenId?: number;
};

export function onModuleChange(state: CascadeState, moduleId: number): CascadeState {
  return { ...state, moduleId, posteId: undefined, moyenId: undefined };
}

export function onPosteChange(state: CascadeState, posteId: number): CascadeState {
  return { ...state, posteId, moyenId: undefined };
}

export function autoTimeLabel(found: boolean | undefined, minutes: number | undefined): string {
  if (!found) return "0 si aucune donnee trouvee.";
  return `Recupere automatiquement depuis le module arret (${minutes ?? 0} min).`;
}
