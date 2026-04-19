/** Full days from now until `iso` instant (UTC-safe for API timestamps). */
export function daysUntilExpiry(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const end = new Date(iso).getTime();
  if (Number.isNaN(end)) return null;
  const ms = end - Date.now();
  return Math.floor(ms / 86400000);
}

export type CertUrgency = "none" | "ok" | "warn" | "crit";

export function certUrgency(days: number | null): CertUrgency {
  if (days === null) return "none";
  if (days < 0) return "crit";
  if (days <= 14) return "crit";
  if (days <= 30) return "warn";
  return "ok";
}

export function certUrgencyClass(u: CertUrgency): string {
  if (u === "crit") return "text-rose-300";
  if (u === "warn") return "text-amber-200";
  if (u === "ok") return "text-emerald-200/90";
  return "text-slate-500";
}
