"use client";

import Link from "next/link";

export const BASIS: Record<string, { label: string; cls: string; dot: string; hint: string }> = {
  standard: { label: "Standard", cls: "border-emerald-500/40 bg-emerald-500/5", dot: "bg-emerald-400", hint: "Required by the cited Indian Standard (edition in force on the tender date)" },
  regulation: { label: "Regulation", cls: "border-rose-500/40 bg-rose-500/5", dot: "bg-rose-400", hint: "Required by a QCO / CRS / BEE label / ALMM order in force" },
  buyer: { label: "Your choice", cls: "border-sky-500/50 bg-sky-500/5", dot: "bg-sky-400", hint: "A value you stated or answered" },
  buyer_default: { label: "Default choice", cls: "border-sky-500/25 bg-sky-500/[0.03]", dot: "bg-sky-700", hint: "A buyer choice filled with the typical default — change it if needed" },
  practice: { label: "Practice default", cls: "border-amber-500/40 bg-amber-500/5", dot: "bg-amber-400", hint: "Common public-procurement practice, not a statutory limit — editable" },
  policy: { label: "Policy", cls: "border-violet-500/40 bg-violet-500/5", dot: "bg-violet-400", hint: "GFR 2017 / Make in India / MSE policy" },
  repair: { label: "Auto-repair", cls: "border-fuchsia-500/40 bg-fuchsia-500/5", dot: "bg-fuchsia-400", hint: "Added by the self-verification loop after the compiler flagged a gap" },
};

export function PathChips({ path }: { path: string[] }) {
  return (
    <div className="flex flex-wrap items-center gap-1 mt-1">
      {path.map((p, i) => {
        const rel = /^[◀A-Z_]+$/.test(p);
        return rel ? <span key={i} className="text-[0.75rem] font-bold text-slate-500 tracking-wider">{p.replace("◀", "← ")}</span>
          : <Link key={i} href={`/kg?node=${encodeURIComponent(p)}`} className="text-[0.75rem] px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-sky-200 hover:border-sky-500">{p.replace(/^(\w+):/, (m) => m.toUpperCase().replace(":", " · "))}</Link>;
      })}
    </div>
  );
}

