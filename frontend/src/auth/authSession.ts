/** Pure helpers for session / PSP shift locking (facile à tester sans React). */

export type MeLike = {
  role?: string;
  shift?: string | null;
};

/** Shift imposé dans les formulaires lorsque l'utilisateur est PSP. */
export function lockedShiftFromMe(me: MeLike | undefined): string | undefined {
  if (me?.role !== "PSP" || !me.shift) return undefined;
  return me.shift;
}
