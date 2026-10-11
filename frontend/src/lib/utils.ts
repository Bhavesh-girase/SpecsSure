import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getStatusColor(status?: string): string {
  switch ((status || "").toLowerCase()) {
    case "current":
    case "undated_current":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
    case "superseded":
    case "outdated_edition":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    case "withdrawn":
      return "bg-rose-500/15 text-rose-300 border-rose-500/30";
    case "future_effective":
    case "not_yet_effective":
      return "bg-sky-500/15 text-sky-300 border-sky-500/30";
    case "foreign":
      return "bg-violet-500/15 text-violet-300 border-violet-500/30";
    default:
      return "bg-slate-700/40 text-slate-300 border-slate-600/40";
  }
}

export function getSeverityColor(sev?: string): string {
  switch ((sev || "").toLowerCase()) {
    case "critical":
      return "bg-rose-500/10 border-rose-500/40 text-rose-200";
    case "major":
    case "warning":
      return "bg-amber-500/10 border-amber-500/40 text-amber-100";
    case "minor":
      return "bg-sky-500/10 border-sky-500/30 text-sky-100";
    default:
      return "bg-slate-800/60 border-slate-700 text-slate-300";
  }
}

export const SEV_DOT: Record<string, string> = {
  critical: "bg-rose-500",
  major: "bg-amber-400",
  minor: "bg-sky-400",
  info: "bg-slate-400",
};

export const STATUS_STYLE: Record<string, string> = {
  COMPLIANT: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  CLAIMED_ONLY: "bg-yellow-500/15 text-yellow-200 border-yellow-500/40",
  DECLARATION: "bg-slate-600/30 text-slate-300 border-slate-500/40",
  NEEDS_CLARIFICATION: "bg-orange-500/15 text-orange-200 border-orange-500/40",
  MISSING_EVIDENCE: "bg-rose-500/10 text-rose-200 border-rose-500/30",
  CONFLICTING_EVIDENCE: "bg-fuchsia-500/15 text-fuchsia-200 border-fuchsia-500/40",
  NON_COMPLIANT: "bg-rose-600/25 text-rose-100 border-rose-500/60",
};

export function formatScore(v?: number | null, digits = 0): string {
  if (v === undefined || v === null || Number.isNaN(v)) return "—";
  return v <= 1 ? `${(v * 100).toFixed(digits)}%` : `${v.toFixed(digits)}`;
}

export function fmtBound(norm: any): string {
  if (!norm) return "";
  const u = (norm.unit || "").replace("**2", "²").replace("percent", "%").replace("dimensionless", "");
  const { min, max } = norm;
  if (min != null && max != null) return min === max ? `= ${min} ${u}` : `${min} – ${max} ${u}`;
  if (min != null) return `≥ ${min} ${u}`;
  if (max != null) return `≤ ${max} ${u}`;
  return "";
}

export const gateStyle = (g?: string) =>
  g === "READY"
    ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
    : g === "NEEDS_REVIEW"
    ? "bg-amber-500/15 text-amber-200 border-amber-500/40"
    : "bg-rose-500/15 text-rose-200 border-rose-500/50";
