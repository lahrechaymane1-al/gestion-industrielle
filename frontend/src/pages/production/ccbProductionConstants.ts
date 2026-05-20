/** Objectifs horaires CCB (H1–H8), identiques pour chaque shift. Total = somme. */
export const CCB_OBJECTIFS_HORAIRES = [20, 20, 20, 20, 11, 20, 20, 20] as const;
export const CCB_OBJECTIF_TOTAL_SHIFT = CCB_OBJECTIFS_HORAIRES.reduce((a, b) => a + b, 0);
