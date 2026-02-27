// ─────────────────────────────────────────────────────────────────────────────
// User helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Safely compute a display initial for avatars.
 *
 * Important: never throw (some pages render before the user profile is loaded).
 */
export function getUserInitial(fullName?: string | null, fallback = 'U'): string {
  const initial = (fullName ?? '').trim().charAt(0)
  return (initial || fallback).toUpperCase()
}

