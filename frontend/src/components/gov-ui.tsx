"use client";

import Link from "next/link";
import { ReactNode } from "react";
import { ArrowRight, Check } from "lucide-react";
import { T, usePrefs } from "@/lib/prefs";

export const STAGES = ["draft", "published", "bids_closed", "financial_opened", "awarded"] as const;

export function SectionHead({ id, title, sub, right }: { id?: string; title: ReactNode; sub?: ReactNode; right?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 id={id} className="text-xl font-extrabold text-[#0f2748] flex items-center gap-2"><span className="w-1.5 h-6 bg-[#ff9933] rounded-sm" />{title}</h2>
        {sub && <p className="text-[0.9375rem] text-slate-400 mt-1 max-w-4xl">{sub}</p>}
      </div>
      {right}
    </div>
  );
}

export function PageHead({ kicker, title, sub, right, icon: Icon }: { kicker?: ReactNode; title: ReactNode; sub?: ReactNode; right?: ReactNode; icon?: any }) {
  return (
    <div className="bg-white border border-[#d5deea] rounded-lg shadow-card overflow-hidden">
      <div className="h-1 tricolour" />
      <div className="p-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4 min-w-0">
          {Icon && <span className="w-12 h-12 rounded-md bg-[#0f2748] text-white flex items-center justify-center shrink-0"><Icon className="w-6 h-6" /></span>}
          <div className="min-w-0">
            {kicker && <div className="text-[0.8125rem] uppercase tracking-widest font-bold text-[#b7862b]">{kicker}</div>}
            <h1 className="text-2xl font-extrabold text-[#0f2748] leading-tight">{title}</h1>
            {sub && <p className="text-[0.9375rem] text-slate-400 mt-1 max-w-3xl">{sub}</p>}
          </div>
        </div>
        {right}
      </div>
    </div>
  );
}

export function Kpi({ label, value, hint, tone = "navy", icon: Icon }: { label: ReactNode; value: ReactNode; hint?: ReactNode; tone?: "navy" | "green" | "saffron" | "red" | "blue"; icon?: any }) {
  const c = { navy: "#0f2748", green: "#138808", saffron: "#c26a00", red: "#c0262d", blue: "#1d4f93" }[tone];
  return (
    <div className="bg-white border border-[#d5deea] rounded-lg p-4 shadow-card relative overflow-hidden">
      <div className="absolute left-0 top-0 bottom-0 w-1" style={{ background: c }} />
      <div className="flex items-start justify-between gap-2">
        <div className="text-[0.8125rem] font-bold uppercase tracking-wider text-slate-500">{label}</div>
        {Icon && <Icon className="w-4 h-4" style={{ color: c }} />}
      </div>
      <div className="text-[1.75rem] font-extrabold font-mono mt-1 leading-none" style={{ color: c }}>{value}</div>
      {hint && <div className="text-[0.8125rem] text-slate-500 mt-1.5">{hint}</div>}
    </div>
  );
}

export function StagePill({ stage }: { stage: string }) {
  const { t } = usePrefs();
  const s: Record<string, string> = {
    draft: "bg-[#f1f5f9] text-[#334155] border-[#cbd5e1]", published: "bg-[#e7f5e9] text-[#0d6b06] border-[#9bd3a3]",
    bids_closed: "bg-[#fff4e0] text-[#8a5300] border-[#f2cf8c]", financial_opened: "bg-[#eef4fb] text-[#1d4f93] border-[#adc8ea]",
    awarded: "bg-[#0f2748] text-white border-[#0f2748]",
  };
  return <span className={`inline-block px-2 py-0.5 rounded-sm border text-[0.8125rem] font-bold whitespace-nowrap ${s[stage] || s.draft}`}>{t(`stage.${stage}`, stage)}</span>;
}

/** Horizontal lifecycle tracker (draft → published → evaluation → financial → awarded). */
export function StageTracker({ stage, compact }: { stage: string; compact?: boolean }) {
  const { t } = usePrefs();
  const idx = STAGES.indexOf(stage as any);
  return (
    <ol className="flex items-center w-full" aria-label="Tender stage">
      {STAGES.map((s, i) => {
        const done = i < idx || stage === "awarded", cur = i === idx && stage !== "awarded";
        return (
          <li key={s} className="flex-1 flex items-center last:flex-none">
            <div className="flex flex-col items-center gap-1 min-w-0">
              <span className={`w-6 h-6 rounded-full border-2 flex items-center justify-center text-[0.75rem] font-bold ${done ? "bg-[#138808] border-[#138808] text-white" : cur ? "bg-[#ff9933] border-[#ff9933] text-[#0f2748]" : "bg-white border-[#cbd5e1] text-slate-400"}`}
                aria-current={cur ? "step" : undefined}>{done ? <Check className="w-3.5 h-3.5" /> : i + 1}</span>
              {!compact && <span className={`text-[0.8125rem] text-center leading-tight whitespace-nowrap ${cur ? "font-bold text-[#0f2748]" : "text-slate-500 hidden sm:block"}`}>{t(`stage.${s}`)}</span>}
            </div>
            {i < STAGES.length - 1 && <div className={`h-0.5 flex-1 mx-1 ${compact ? "" : "-mt-4"} ${i < idx ? "bg-[#138808]" : "bg-[#dbe3ee]"}`} />}
          </li>
        );
      })}
    </ol>
  );
}

export function RoleCard({ icon: Icon, color, title, href, points }: { icon: any; color: string; title: string; href: string; points: [string, string][] }) {
  return (
    <Link href={href} className="group bg-white border border-[#d5deea] rounded-lg overflow-hidden shadow-card hover:shadow-lift transition-all flex flex-col">
      <div className="px-5 py-4 text-white flex items-center gap-3" style={{ background: color }}>
        <span className="w-10 h-10 rounded-full bg-white/15 flex items-center justify-center"><Icon className="w-5 h-5" /></span>
        <span className="font-extrabold text-[1.0625rem]">{title}</span>
      </div>
      <ul className="p-5 space-y-2 flex-1">
        {points.map(([en, hi]) => (
          <li key={en} className="flex gap-2 text-[0.9375rem] text-[#334155]"><span className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0" style={{ background: color }} /><T en={en} hi={hi} /></li>
        ))}
      </ul>
      <div className="px-5 py-3 border-t border-[#e2e8f0] text-[0.9375rem] font-bold flex items-center gap-1 group-hover:gap-2 transition-all" style={{ color }}>
        <T en="Enter workspace" hi="कार्यक्षेत्र खोलें" /><ArrowRight className="w-4 h-4" />
      </div>
    </Link>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warn" | "good" | "bad"; children: ReactNode }) {
  const s = { info: "bg-[#eef4fb] border-[#adc8ea] text-[#13325d]", warn: "bg-[#fff8ec] border-[#f2d8a7] text-[#6b4200]",
              good: "bg-[#e7f5e9] border-[#9bd3a3] text-[#0d4f07]", bad: "bg-[#fdecec] border-[#f1b0b0] text-[#8a1414]" }[tone];
  return <div className={`border rounded-md px-3 py-2 text-[0.875rem] ${s}`}>{children}</div>;
}

/**
 * Page introduction: what this page is for in plain words, the steps to use it, and — folded away —
 * the technical explanation for readers who want it.
 */
export function PageIntro({ icon: Icon, kicker, title, sub, steps, details, right }: {
  icon?: any; kicker?: ReactNode; title: ReactNode; sub?: ReactNode; steps?: ReactNode[]; details?: ReactNode; right?: ReactNode;
}) {
  return (
    <div className="bg-white border border-[#d5deea] rounded-lg shadow-card overflow-hidden">
      <div className="h-1 tricolour" />
      <div className="p-5 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-4 min-w-0 flex-1">
            {Icon && <span className="w-12 h-12 rounded-md bg-[#0f2748] text-white flex items-center justify-center shrink-0"><Icon className="w-6 h-6" /></span>}
            <div className="min-w-0">
              {kicker && <div className="text-[0.8125rem] uppercase tracking-wider font-bold text-[#b7862b]">{kicker}</div>}
              <h1 className="text-2xl font-extrabold text-[#0f2748] leading-tight">{title}</h1>
              {sub && <p className="text-[0.9375rem] text-[#475569] mt-1.5 max-w-3xl leading-relaxed">{sub}</p>}
            </div>
          </div>
          {right}
        </div>
        {steps && steps.length > 0 && (
          <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-[repeat(auto-fit,minmax(200px,1fr))] pt-4 border-t border-[#e2e8f0]" aria-label="How to use this page">
            {steps.map((s, i) => (
              <li key={i} className="flex items-start gap-2.5 text-[0.9375rem] text-[#334155]">
                <span className="w-6 h-6 rounded-full bg-[#eef4fb] text-[#1d4f93] text-[0.8125rem] font-bold flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                <span className="leading-snug">{s}</span>
              </li>
            ))}
          </ol>
        )}
        {details && (
          <details className="group text-[0.9375rem]">
            <summary className="cursor-pointer select-none font-semibold text-[#1d4f93] hover:underline list-none flex items-center gap-1.5">
              <span className="inline-block transition-transform group-open:rotate-90">›</span> How it works (technical details)
            </summary>
            <div className="mt-2 pl-4 border-l-2 border-[#d5deea] text-[#475569] leading-relaxed max-w-4xl">{details}</div>
          </details>
        )}
      </div>
    </div>
  );
}
