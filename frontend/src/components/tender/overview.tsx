"use client";

import { AlertTriangle, CheckCircle2, XCircle, GitCompare, ShieldCheck, Fingerprint, Cpu } from "lucide-react";
import { Bar, Card, Gauge, SevBadge, Stat } from "@/components/ui";
import { gateStyle, cn } from "@/lib/utils";

const SUB_LABEL: Record<string, string> = {
  clarity: "Clarity", currency: "Standards currency", compliance: "Regulatory compliance",
  consistency: "Consistency (formal)", competition: "Competition", completeness: "Completeness",
};

export function Overview({ twin, onJump }: { twin: any; onJump: (tab: string) => void }) {
  const rd = twin.readiness;
  const top = twin.findings.filter((f: any) => f.severity === "critical" && (f.review_status || "open") === "open").slice(0, 5);
  const steel = (twin.market || [])[0];
  return (
    <div className="space-y-6">
      {twin.delta && (twin.delta.introduced?.length || twin.delta.resolved?.length) ? (
        <Card className="border-sky-500/30">
          <div className="flex items-center gap-2 text-sm font-bold text-ink mb-2">
            <GitCompare className="w-4 h-4 text-sky-400" /> Re-validation delta <span className="text-xs font-normal text-slate-400">({twin.delta.reason})</span>
            <span className="ml-auto font-mono text-xs text-slate-300">{twin.delta.previous_score} → {rd.score}</span>
          </div>
          <div className="grid md:grid-cols-2 gap-3 text-xs">
            <div>
              <div className="text-emerald-300 font-semibold mb-1">✓ Resolved ({twin.delta.resolved.length})</div>
              {twin.delta.resolved.slice(0, 6).map((d: any, i: number) => <div key={i} className="text-slate-400 truncate">· {d.rule_id} Cl.{d.clause_key} — {d.message}</div>)}
            </div>
            <div>
              <div className="text-rose-300 font-semibold mb-1">⚠ Introduced ({twin.delta.introduced.length}){twin.delta.introduced.some((d: any) => d.severity === "critical") ? " — REGRESSION" : ""}</div>
              {twin.delta.introduced.slice(0, 6).map((d: any, i: number) => <div key={i} className="text-slate-300 truncate">· <b>{d.rule_id}</b> Cl.{d.clause_key} — {d.message}</div>)}
            </div>
          </div>
        </Card>
      ) : null}

      <div className="grid lg:grid-cols-3 gap-6">
        <Card glow className="flex flex-col items-center justify-center gap-3">
          <Gauge score={rd.score} size={150} />
          <span className={cn("px-3 py-1 rounded-full border text-xs font-bold tracking-widest", gateStyle(rd.gate))}>{rd.gate.replace("_", " ")}</span>
          <p className="text-[0.8125rem] text-slate-400 text-center">Pre-publication gate. Critical findings block publication until fixed or dismissed with a recorded justification.</p>
        </Card>
        <Card className="lg:col-span-2">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
            <Stat label="Critical" value={rd.counts.critical} tone={rd.counts.critical ? "bad" : "good"} />
            <Stat label="Major" value={rd.counts.major} tone={rd.counts.major ? "warn" : "good"} />
            <Stat label="Requirements" value={twin.requirements.length} hint={`${rd.coverage?.quantitative ?? "—"} quantitative`} />
            <Stat label="Reviewed" value={rd.reviewed ?? 0} hint="human decisions" />
          </div>
          <div className="grid sm:grid-cols-2 gap-x-6 gap-y-3">
            {Object.entries(rd.subscores).map(([k, v]: any) => (
              <div key={k}>
                <div className="flex justify-between text-[0.8125rem] mb-1"><span className="text-slate-300">{SUB_LABEL[k] || k}</span><span className="font-mono text-slate-400">{Math.round(v)}</span></div>
                <Bar value={v} />
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <div className="text-sm font-bold text-ink mb-3 flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-sky-400" /> Pre-publication validation checklist</div>
          <div className="space-y-1.5">
            {rd.checklist.map((c: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                {c.ok ? <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" /> : <XCircle className="w-4 h-4 text-rose-400 shrink-0" />}
                <span className={c.ok ? "text-slate-300" : "text-ink"}>{c.item}</span>
                <span className="ml-auto text-[0.75rem] font-mono text-slate-500">{c.rules.join(" ")}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <div className="text-sm font-bold text-ink mb-3 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-rose-400" /> Blocking issues</div>
          {top.length === 0 ? <p className="text-xs text-emerald-300">No open critical findings.</p> : (
            <div className="space-y-2">
              {top.map((f: any) => (
                <button key={f.fingerprint} onClick={() => onJump(f.rule_id.startsWith("SS-CON-00") && f.source === "solver" ? "proofs" : "findings")}
                  className="w-full text-left p-2.5 rounded-lg bg-rose-500/5 border border-rose-500/20 hover:border-rose-500/50 transition-colors">
                  <div className="flex items-center gap-2 mb-0.5"><SevBadge sev={f.severity} /><span className="font-mono text-[0.75rem] text-slate-400">{f.rule_id} · Cl. {f.clause_key ?? "—"}</span></div>
                  <div className="text-xs text-slate-200 line-clamp-2">{f.message}</div>
                </button>
              ))}
            </div>
          )}
          {steel && (
            <div className="mt-4 text-[0.8125rem] text-slate-400">
              Market: <b className="text-ink">{steel.eligible_manufacturers}</b> of {steel.legal_manufacturers} licensed {steel.domain} manufacturers can comply (restriction index {steel.restriction_index}).
            </div>
          )}
        </Card>
      </div>

      <Card className="text-[0.8125rem] text-slate-400 flex flex-wrap gap-x-6 gap-y-1 items-center">
        <span className="flex items-center gap-1"><Cpu className="w-3.5 h-3.5 text-sky-400" /> {twin.provenance.engine} · {twin.provenance.solver}</span>
        <span className="flex items-center gap-1"><Fingerprint className="w-3.5 h-3.5 text-sky-400" /> KB snapshot <span className="font-mono">{twin.provenance.kb_snapshot.slice(0, 12)}</span></span>
        <span>content hash <span className="font-mono">{twin.provenance.content_hash.slice(0, 12)}</span></span>
        <span>compiled in {twin.provenance.compiled_in_ms} ms</span>
        <span>as-of {twin.tender.as_of}</span>
        <span className="text-emerald-300">deterministic · no LLM in the decision path</span>
      </Card>
    </div>
  );
}
