"use client";

import { AlertOctagon, CheckCircle2, FileWarning, Wrench, ScanText } from "lucide-react";
import { Bar, Card, Gauge } from "@/components/ui";
import { cn } from "@/lib/utils";

export const FSTATUS: Record<string, string> = {
  MEETS: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  EXCEEDS: "bg-teal-500/15 text-teal-200 border-teal-500/40",
  MISSING: "bg-slate-700/40 text-slate-300 border-slate-600",
  UNVERIFIED: "bg-yellow-500/15 text-yellow-200 border-yellow-500/40",
  FAILS: "bg-rose-600/25 text-rose-100 border-rose-500/60",
  CONFLICT: "bg-fuchsia-500/15 text-fuchsia-200 border-fuchsia-500/40",
  CLARIFY: "bg-orange-500/15 text-orange-200 border-orange-500/40",
  "N/A": "bg-slate-900 text-slate-400 border-slate-800",
};
export const TIER: Record<string, { label: string; cls: string }> = {
  FULLY_RESPONSIVE: { label: "Fully responsive", cls: "text-emerald-300" },
  RESPONSIVE_WITH_GAPS: { label: "Responsive — curable gaps", cls: "text-amber-300" },
  SUBJECT_TO_CLARIFICATION: { label: "Subject to clarification", cls: "text-orange-300" },
  NON_RESPONSIVE: { label: "Non-responsive (knock-out)", cls: "text-rose-300" },
};

export function StatusPill({ s }: { s: string }) {
  return <span className={cn("inline-flex px-1.5 py-0.5 rounded border text-[0.75rem] font-bold uppercase tracking-wide", FSTATUS[s] || FSTATUS.MISSING)}>{s}</span>;
}

export function MatchPanel({ score, compact }: { score: any; compact?: boolean }) {
  if (!score) return null;
  const t = TIER[score.tier] || { label: score.tier, cls: "text-slate-200" };
  const subs = score.path_to_compliance.filter((p: any) => p.kind === "substantive");
  const docs = score.path_to_compliance.filter((p: any) => p.kind === "documentary");
  return (
    <Card glow className="space-y-3">
      <div className="flex items-center gap-4">
        <Gauge score={score.match_index} size={compact ? 96 : 118} label="match" />
        <div className="flex-1">
          <div className="text-[0.75rem] uppercase tracking-widest text-slate-500 font-bold">Tender Match Index</div>
          <div className={cn("text-base font-extrabold", t.cls)}>{t.label}</div>
          <div className="text-[0.8125rem] text-slate-400 leading-snug">{score.verdict}</div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-slate-900/70 border border-slate-800 p-1.5"><div className="text-[0.75rem] uppercase text-slate-500">coverage</div><div className="font-mono text-sm text-ink">{Math.round(score.coverage * 100)}%</div></div>
        <div className="rounded-lg bg-slate-900/70 border border-slate-800 p-1.5"><div className="text-[0.75rem] uppercase text-slate-500">evidence</div><div className="font-mono text-sm text-ink">{Math.round(score.evidence_confidence * 100)}%</div></div>
        <div className="rounded-lg bg-slate-900/70 border border-slate-800 p-1.5" title={score.headroom_note}><div className="text-[0.75rem] uppercase text-slate-500">headroom</div><div className="font-mono text-sm text-ink">{score.headroom == null ? "—" : `+${Math.round(score.headroom * 100)}%`}</div></div>
      </div>
      {!compact && (
        <div className="space-y-1.5">
          {score.groups.map((g: any) => (
            <div key={g.group}>
              <div className="flex justify-between text-[0.8125rem]"><span className="text-slate-300 capitalize">{g.group}</span><span className="font-mono text-slate-400">{g.met}/{g.total}{g.knockouts ? ` · ${g.knockouts} KO` : ""}</span></div>
              <Bar value={g.met} max={g.total} tone={g.knockouts ? "bg-rose-500" : undefined} />
            </div>
          ))}
        </div>
      )}
      {(subs.length > 0 || docs.length > 0) && (
        <div className="space-y-1">
          <div className="text-[0.75rem] uppercase tracking-widest text-slate-500 font-bold flex items-center gap-1"><Wrench className="w-3 h-3" /> Path to compliance</div>
          {subs.slice(0, compact ? 3 : 8).map((p: any, i: number) => (
            <div key={i} className="text-[0.8125rem] text-rose-200 flex gap-1.5"><AlertOctagon className="w-3.5 h-3.5 shrink-0 mt-0.5" /><span><b>Change</b> (Cl. {p.clause_key}): {p.action}</span></div>
          ))}
          {docs.slice(0, compact ? 3 : 8).map((p: any, i: number) => (
            <div key={i} className="text-[0.8125rem] text-amber-100/90 flex gap-1.5"><FileWarning className="w-3.5 h-3.5 shrink-0 mt-0.5" /><span><b>Attach / fill</b> (Cl. {p.clause_key}): {p.action}</span></div>
          ))}
          {subs.length + docs.length > (compact ? 6 : 16) && <div className="text-[0.75rem] text-slate-500">+{subs.length + docs.length - (compact ? 6 : 16)} more</div>}
        </div>
      )}
      {score.knockouts === 0 && score.tier === "FULLY_RESPONSIVE" && <div className="text-[0.8125rem] text-emerald-300 flex gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> Every requirement is met and evidenced.</div>}
      <div className="text-[0.75rem] text-slate-500 leading-snug">{score.formula} {score.headroom_note}</div>
    </Card>
  );
}

export function FileReadout({ files }: { files: any[] }) {
  if (!files?.length) return null;
  return (
    <div className="space-y-1.5">
      {files.map((f) => (
        <div key={f.filename + f.sha256} className="rounded-lg bg-slate-900/70 border border-slate-800 px-2.5 py-1.5 text-[0.8125rem]">
          <div className="flex items-center gap-1.5">
            <ScanText className="w-3.5 h-3.5 text-sky-300" /><b className="text-slate-200 truncate">{f.filename}</b>
            <span className="ml-auto text-slate-500">{f.doc_type} · {f.facts} facts · {f.parser}</span>
          </div>
          {f.ocr?.map((o: any) => (
            <div key={o.page} className="text-slate-400 pl-5">OCR p.{o.page}: {o.engine} · confidence <b className={o.mean_conf > 0.9 ? "text-emerald-300" : "text-amber-300"}>{Math.round((o.mean_conf || 0) * 100)}%</b> · {Math.round(o.ms)} ms
              {o.repairs?.filter((r: any) => r.from.trim() !== r.to.trim()).length > 0 && <> · repaired {o.repairs.filter((r: any) => r.from.trim() !== r.to.trim()).map((r: any) => `“${r.from}”→“${r.to}”`).join(", ")}</>}</div>
          ))}
          {f.warnings?.map((w: string, i: number) => <div key={i} className="text-amber-300 pl-5">{w}</div>)}
        </div>
      ))}
    </div>
  );
}
