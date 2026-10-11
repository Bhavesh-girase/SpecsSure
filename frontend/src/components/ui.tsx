"use client";

import { ReactNode, useState } from "react";
import { Loader2 } from "lucide-react";
import { cn, SEV_DOT } from "@/lib/utils";

export function Card({ children, className, glow }: { children: ReactNode; className?: string; glow?: boolean }) {
  return <div className={cn(glow ? "glass-panel-glow" : "glass-panel", "rounded-2xl p-5", className)}>{children}</div>;
}

export function SectionTitle({ icon, title, subtitle, right }: { icon?: ReactNode; title: string; subtitle?: string; right?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3 mb-4">
      <div>
        <h2 className="text-lg font-bold text-ink flex items-center gap-2">
          {icon}
          {title}
        </h2>
        {subtitle && <p className="text-xs text-slate-400 mt-0.5 max-w-3xl">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export function Badge({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[0.75rem] font-semibold uppercase tracking-wide", className)}>{children}</span>;
}

export function SevBadge({ sev }: { sev: string }) {
  const styles: Record<string, string> = {
    critical: "bg-rose-500/15 text-rose-300 border-rose-500/40",
    major: "bg-amber-500/15 text-amber-300 border-amber-500/40",
    minor: "bg-sky-500/15 text-sky-300 border-sky-500/40",
    info: "bg-slate-700/50 text-slate-300 border-slate-600",
  };
  return (
    <Badge className={styles[sev] || styles.info}>
      <span className={cn("w-1.5 h-1.5 rounded-full", SEV_DOT[sev] || "bg-slate-400")} />
      {sev}
    </Badge>
  );
}

export function Button({
  children, onClick, variant = "primary", disabled, loading, className, type = "button", title,
}: {
  children: ReactNode; onClick?: () => any; variant?: "primary" | "ghost" | "danger" | "success" | "subtle";
  disabled?: boolean; loading?: boolean; className?: string; type?: "button" | "submit"; title?: string;
}) {
  const [busy, setBusy] = useState(false);
  const styles = {
    primary: "bg-sky-600 hover:bg-sky-500 text-white border-sky-500/50",
    ghost: "bg-slate-900 hover:bg-slate-800 text-slate-200 border-slate-700",
    subtle: "bg-slate-800/60 hover:bg-slate-700 text-slate-200 border-slate-700",
    danger: "bg-rose-600/80 hover:bg-rose-500 text-white border-rose-500/50",
    success: "bg-emerald-600/90 hover:bg-emerald-500 text-white border-emerald-500/50",
  }[variant];
  const isBusy = loading || busy;
  return (
    <button
      type={type}
      title={title}
      disabled={disabled || isBusy}
      onClick={async () => {
        if (!onClick) return;
        setBusy(true);
        try {
          await onClick();
        } finally {
          setBusy(false);
        }
      }}
      className={cn("inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed", styles, className)}
    >
      {isBusy && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
      {children}
    </button>
  );
}

export function Stat({ label, value, hint, tone = "default" }: { label: string; value: ReactNode; hint?: string; tone?: "default" | "good" | "bad" | "warn" }) {
  const c = { default: "text-ink", good: "text-emerald-300", bad: "text-rose-300", warn: "text-amber-300" }[tone];
  return (
    <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-3">
      <div className="text-[0.75rem] uppercase tracking-widest text-slate-500 font-semibold">{label}</div>
      <div className={cn("text-2xl font-bold font-mono mt-0.5", c)}>{value}</div>
      {hint && <div className="text-[0.8125rem] text-slate-500 mt-0.5">{hint}</div>}
    </div>
  );
}

export function Bar({ value, max = 100, tone }: { value: number; max?: number; tone?: string }) {
  const pct = Math.max(0, Math.min(100, (value / (max || 1)) * 100));
  const color = tone || (pct >= 80 ? "bg-emerald-500" : pct >= 55 ? "bg-amber-400" : "bg-rose-500");
  return (
    <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
      <div className={cn("h-full rounded-full transition-all duration-700", color)} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Gauge({ score, size = 132, label }: { score: number; size?: number; label?: string }) {
  const r = (size - 16) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score));
  const color = pct >= 80 ? "#138808" : pct >= 55 ? "#d97706" : "#c0262d";
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#e2e8f0" strokeWidth="10" fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth="10" fill="none" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (pct / 100) * c} style={{ transition: "stroke-dashoffset 1s ease" }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-extrabold font-mono text-ink">{Math.round(pct)}</span>
        <span className="text-[0.75rem] uppercase tracking-widest text-slate-400">{label || "readiness"}</span>
      </div>
    </div>
  );
}

export function Tabs<T extends string>({ tabs, active, onChange }: { tabs: { id: T; label: string; icon?: any; count?: number }[]; active: T; onChange: (t: T) => void }) {
  return (
    <div className="flex flex-wrap items-center gap-1 border-b border-slate-800 pb-px" role="tablist">
      {tabs.map((t) => {
        const Icon = t.icon;
        const on = t.id === active;
        return (
          <button key={t.id} role="tab" aria-selected={on} onClick={() => onChange(t.id)}
            className={cn("px-3.5 py-2.5 text-xs font-semibold flex items-center gap-1.5 whitespace-nowrap border-b-2 -mb-px transition-colors",
              on ? "border-sky-400 text-sky-300 bg-slate-900/70 rounded-t-lg" : "border-transparent text-slate-400 hover:text-slate-200")}>
            {Icon && <Icon className="w-3.5 h-3.5" />}
            {t.label}
            {t.count !== undefined && <span className={cn("ml-0.5 px-1.5 rounded-full text-[0.75rem]", on ? "bg-sky-500/20" : "bg-slate-800")}>{t.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="text-center text-sm text-slate-500 py-10 border border-dashed border-slate-800 rounded-xl">{children}</div>;
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-24 text-slate-400 text-sm">
      <Loader2 className="w-5 h-5 animate-spin text-sky-400" /> {label}
    </div>
  );
}

export function ErrorBox({ error }: { error?: string | null }) {
  if (!error) return null;
  return <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 text-rose-200 text-xs p-3">{error}</div>;
}

export function Disclaimer({ children }: { children?: ReactNode }) {
  return (
    <p className="text-[0.8125rem] text-slate-500 leading-relaxed">
      {children || "Decision support. Deterministic engines (parser, SMT solver, rule engine) produce the findings; any AI-generated text is labelled. Final decisions rest with the competent authority. Verify standards and QCOs on the official BIS portal."}
    </p>
  );
}
