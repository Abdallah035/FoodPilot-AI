import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind class names with conflict resolution. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format a number as EGP currency, in Arabic (Egypt) locale. */
export function formatEGP(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "string" ? parseFloat(value.replace(/[^\d.]/g, "")) : value;
  if (Number.isNaN(num)) return String(value);
  return new Intl.NumberFormat("ar-EG", {
    style: "currency",
    currency: "EGP",
    maximumFractionDigits: 0,
  }).format(num);
}

/** Clamp a number between min and max. */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/** Generate a reasonably-unique id without external deps. */
export function uid(prefix = "id"): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`;
}

/** Promise-based delay. */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Format a distance in km into a friendly Arabic string. */
export function formatDistance(km: number | null | undefined): string {
  if (km === null || km === undefined) return "";
  if (km < 1) return `${arabic(Math.round(km * 1000))} م`;
  return `${arabic(km.toFixed(1))} كم`;
}

/** Estimate delivery ETA from distance (rough heuristic for display). */
export function estimateEta(km: number | null | undefined): string {
  if (km === null || km === undefined) return `${arabic(25)}–${arabic(35)} دقيقة`;
  const base = 15;
  const perKm = 4;
  const mid = Math.round(base + km * perKm);
  return `${arabic(mid)}–${arabic(mid + 10)} دقيقة`;
}

/** Western → Arabic-Indic digits. */
export function arabic(value: string | number): string {
  const map = "٠١٢٣٤٥٦٧٨٩";
  return String(value).replace(/[0-9]/g, (d) => map[Number(d)]);
}
