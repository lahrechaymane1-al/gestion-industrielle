/** Périmètre UEP (valeurs métier Berceau / CCB) — le champ API reste `equipe`. */
export type EquipeScope = "Berceau" | "CCB";

export interface Paginated<T> {
  results: T[];
  page: number;
  pages: number;
  total: number;
}

export interface EffectifOption {
  id: number;
  nom_complet: string;
  shift: string;
  fonction: string;
  equipe: string;
}

export interface AbsenceRow {
  id: number;
  equipe: string;
  shift: string;
  nom_complet: string;
  motif: string;
  remplacant: string;
  commentaire?: string;
  date_absence: string;
  created_at: string;
  effectif: number | null;
  remplacant_effectif: number | null;
  nom_absent: string;
  nom_remplacant: string;
  migration_status?: string;
  migration_note?: string;
}

export interface EffectifRow {
  id: number;
  nom_complet: string;
  shift: string;
  cin: string;
  type_contrat: string;
  date_naissance: string;
  sexe: string;
  date_entree: string;
  identifiant: string;
  matricule: string;
  num_tel: string;
  fonction: "PSP" | "OPERATEUR";
  ville_actuelle: string;
  niveau_etude: string;
  numero_casier: string;
  parada_transport: string;
  pointure_chaussure: number;
  specialite: string;
  taille_pantalon: string;
  taille_veste: string;
  ville_origine: string;
  equipe: string;
  code_equipe?: string;
  psp_lead?: number | null;
  psp_lead_nom?: string;
  /** RU/ADMIN : username Django lie a cette fiche PSP (via UserAccessProfile). */
  psp_linked_username?: string;
}

export interface ModeDegradeRow {
  id: number;
  equipe: string;
  shift: string;
  action: string;
  probleme: string;
  pilote: string;
  date: string;
  cause: string;
  statut: string;
  created_at: string;
}

export interface ProductionBerceauRow {
  id: number;
  line: string;
  date: string;
  shift: string;
  objectif: number;
  volume: number;
  rebut: number;
  retouche: number;
  temps_arrets: number;
  ro_percent: number;
  nro_total: number;
  validated_hours_mask: number;
  validated_hours: number[];
  arrets_source?: "arret_module";
  production_h1: number;
  production_h2: number;
  production_h3: number;
  production_h4: number;
  production_h5: number;
  production_h6: number;
  production_h7: number;
  production_h8: number;
  rebut_h1: number;
  rebut_h2: number;
  rebut_h3: number;
  rebut_h4: number;
  rebut_h5: number;
  rebut_h6: number;
  rebut_h7: number;
  rebut_h8: number;
  retouche_h1: number;
  retouche_h2: number;
  retouche_h3: number;
  retouche_h4: number;
  retouche_h5: number;
  retouche_h6: number;
  retouche_h7: number;
  retouche_h8: number;
  temps_arrets_h1: number;
  temps_arrets_h2: number;
  temps_arrets_h3: number;
  temps_arrets_h4: number;
  temps_arrets_h5: number;
  temps_arrets_h6: number;
  temps_arrets_h7: number;
  temps_arrets_h8: number;
  objectif_h1: number;
  objectif_h2: number;
  objectif_h3: number;
  objectif_h4: number;
  objectif_h5: number;
  objectif_h6: number;
  objectif_h7: number;
  objectif_h8: number;
  line_h1: "A1" | "A3";
  line_h2: "A1" | "A3";
  line_h3: "A1" | "A3";
  line_h4: "A1" | "A3";
  line_h5: "A1" | "A3";
  line_h6: "A1" | "A3";
  line_h7: "A1" | "A3";
  line_h8: "A1" | "A3";
}

export interface ProductionCCBRow {
  id: number;
  date: string;
  shift: string;
  objectif: number;
  objectif_h1: number;
  objectif_h2: number;
  objectif_h3: number;
  objectif_h4: number;
  objectif_h5: number;
  objectif_h6: number;
  objectif_h7: number;
  objectif_h8: number;
  production_h1: number;
  production_h2: number;
  production_h3: number;
  production_h4: number;
  production_h5: number;
  production_h6: number;
  production_h7: number;
  production_h8: number;
  rebut_h1: number;
  rebut_h2: number;
  rebut_h3: number;
  rebut_h4: number;
  rebut_h5: number;
  rebut_h6: number;
  rebut_h7: number;
  rebut_h8: number;
  volume: number;
  rebut: number;
  retouche: number;
  temps_arrets: number;
  ro_percent: number;
  temps_arrets_h1?: number;
  temps_arrets_h2?: number;
  temps_arrets_h3?: number;
  temps_arrets_h4?: number;
  temps_arrets_h5?: number;
  temps_arrets_h6?: number;
  temps_arrets_h7?: number;
  temps_arrets_h8?: number;
}

export interface BerceauModuleOption {
  id: number;
  name: string;
}

export interface BerceauPosteOption {
  id: number;
  name: string;
  module_id: number;
  module_name?: string;
  a1_enabled: boolean;
  a3_enabled: boolean;
}

export interface BerceauMoyenOption {
  id: number;
  name: string;
  poste_id: number;
}

export interface PanneTypeOption {
  id: number;
  name: string;
  description?: string;
  is_active?: boolean;
  is_catalog?: boolean;
}

export interface AlertePanneRow {
  id: number;
  module_id: number;
  module_nom: string;
  poste_id: number;
  poste_nom: string;
  moyen_id: number | null;
  moyen_nom: string;
  panne_type_id: number;
  panne_type_nom: string;
  cause: string;
  solution: string;
  category: "maintenance" | "kta" | "logistique" | "fabrication";
  category_label: string;
  date: string;
  shift: string;
  heure_production: number;
  temps_arret_min: number;
  /** Impact production % (Berceau) : (temps/div)×(100/Σ objectifs H1–H8 du shift) ; null si données indisponibles. */
  impact_pct?: number | null;
  equipe: EquipeScope;
  created_at: string;
}

export interface DashboardRoNroTrendResponse {
  labels: string[];
  series: {
    ro_percent: number[];
    nro_percent: number[];
  };
  totals: {
    objectif: number;
    volume: number;
  };
}

export interface DashboardArretsParJourResponse {
  labels: string[];
  series: {
    /** Minutes d'arrêt Berceau (module + alertes) par jour, aligné sur `labels`. */
    berceau_minutes: number[];
    /** Minutes d'arrêt CCB (alertes) par jour. */
    ccb_minutes: number[];
    /** Total Berceau + CCB par jour (rétrocompatibilité). */
    arrets_minutes: number[];
  };
  totals: {
    berceau_minutes: number;
    ccb_minutes: number;
    arrets_minutes: number;
  };
}

export interface DashboardParetoPannesResponse {
  labels: string[];
  series: {
    arrets_minutes: number[];
    cumulative_percent: number[];
  };
  totals: {
    arrets_minutes: number;
  };
  meta?: {
    group_by: "poste" | "category" | "panne_type";
    category_filter?: string | null;
    poste_id?: number | null;
  };
}

export interface StockJournalRow {
  id: number | null;
  date: string;
  equipe: EquipeScope;
  line: "A1" | "A3" | null;
  stock_debut: number;
  entree_calculee: number;
  entree_par_shift: { A: number; B: number; N: number };
  sortie_montage: number;
  /** Sortie imputée au shift PSP (prorata des entrées du jour) ; égale à sortie_montage hors scope shift. */
  sortie_imputee?: number;
  stock_fin: number;
  is_closed: boolean;
  note: string;
  updated_at: string | null;
}

export interface StockJournalResponse {
  current: StockJournalRow;
  history: StockJournalRow[];
}
