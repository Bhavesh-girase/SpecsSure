"use client";

import { useState } from "react";
import { Sigma, Store, Clock3, FlaskConical, CalendarClock, AlertOctagon, Link2 } from "lucide-react";
import { Badge, Bar, Button, Card, Empty } from "@/components/ui";
import { updateTender } from "@/lib/api";
import { cn, getStatusColor } from "@/lib/utils";

/* ------------------------------------------------ formal proofs (Z3) */
export function Proofs({ twin }: { twin: any }) {
  const v = twin.verification;
  const conflicts = [...v.conflicts.map((c: any) => ({ ...c, kind: "tender" })), ...v.standard_conflicts.map((c: any) => ({ ...c, kind: "standard" }))];
  return (
    <div className="space-y-6">
      <Card glow className="flex flex-wrap items-center gap-4">
        <Sigma className="w-8 h-8 text-violet-300" />
        <div className="flex-1 min-w-[260px]">
          <div className="text-sm font-bold text-ink">Formal verification with an SMT solver</div>
          <p className="text-[0.8125rem] text-slate-400">Every quantitative clause becomes a linear constraint; engineering definitions (e.g. UTS ≥ TS/YS × YS) are added as background axioms. If no product can exist, the solver returns a <b>minimal unsatisfiable core</b> — the exact clauses that clash. No LLM, no heuristics: a proof.</p>
        </div>
        <div className="text-right">
          <div className={cn("text-lg font-bold", v.satisfiable ? "text-emerald-300" : "text-rose-300")}>{v.satisfiable ? "SATISFIABLE" : "UNSATISFIABLE"}</div>
          <div className="text-[0.75rem] font-mono text-slate-500">{v.engine} · {v.constraint_count} constraints</div>
        </div>
      </Card>
      {conflicts.length === 0 ? <Empty>No contradictions — a compliant product can exist for every combination of clauses.</Empty> : conflicts.map((c: any, i: number) => (
        <Card key={i} className="border-rose-500/30">
          <div className="flex items-center gap-2 mb-3">
            <AlertOctagon className="w-4 h-4 text-rose-400" />
            <span className="text-sm font-bold text-ink">{c.kind === "tender" ? "Clauses contradict each other" : "Clause contradicts the standard it cites"}</span>
            <Badge className="border-rose-500/40 text-rose-300 ml-auto">UNSAT core · {c.atoms.length} element(s)</Badge>
          </div>
          <div className="flex flex-wrap items-stretch gap-2">
            {c.atoms.map((a: any, j: number) => (
              <div key={j} className="flex items-center gap-2">
                <div className={cn("rounded-lg border p-2.5 max-w-xs", a.kind === "relation" ? "border-violet-500/40 bg-violet-500/10" : a.kind === "standard" ? "border-sky-500/40 bg-sky-500/10" : "border-rose-500/40 bg-rose-500/10")}>
                  <div className="text-[0.75rem] uppercase tracking-wide text-slate-400">{a.kind === "requirement" ? `Clause ${a.clause_key} · p.${a.page ?? "?"}` : a.kind === "relation" ? "Engineering axiom" : "Cited standard"}</div>
                  <div className="text-xs text-ink font-semibold">{a.description}</div>
                  {a.kind === "requirement" && <div className="text-[0.75rem] text-slate-400 italic mt-0.5 line-clamp-2">“{a.text}”</div>}
                </div>
                {j < c.atoms.length - 1 && <span className="text-rose-400 font-bold">∧</span>}
              </div>
            ))}
            <div className="flex items-center text-rose-300 font-mono text-sm px-2">⟹ ⊥</div>
          </div>
          {c.witness && <div className="mt-3 text-xs font-mono text-amber-200 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2">{c.witness}</div>}
          <p className="text-xs text-slate-300 mt-2">{c.explanation}</p>
        </Card>
      ))}
      <Card>
        <div className="text-sm font-bold text-ink mb-2">Feasible window per parameter (contradiction-free clauses)</div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {Object.entries(v.windows).map(([k, w]: any) => (
            <div key={k} className="rounded-lg bg-slate-950/60 border border-slate-800 p-2 text-[0.8125rem] flex justify-between">
              <span className="text-slate-300">{k.replace("_", " ")}</span>
              <span className="font-mono text-sky-300">[{w.min ?? "−∞"}, {w.max ?? "+∞"}]</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

/* ------------------------------------------------ market feasibility */
export function Market({ twin }: { twin: any }) {
  if (!twin.market?.length) return <Empty>No market catalogue for the detected product domains.</Empty>;
  return (
    <div className="space-y-6">
      {twin.market.map((m: any) => {
        const max = m.funnel[0].manufacturers || 1;
        return (
          <Card key={m.domain}>
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <Store className="w-5 h-5 text-amber-300" />
              <div className="text-sm font-bold text-ink"><span className="capitalize">{m.domain}</span>: how many manufacturers still qualify after each clause <span className="font-normal text-slate-400">(vs {m.standard} {m.grade || ""})</span></div>
              <Badge className={m.competition_ok ? "border-emerald-500/40 text-emerald-300" : "border-rose-500/40 text-rose-300"}>
                {m.eligible_manufacturers} / {m.legal_manufacturers} manufacturers eligible
              </Badge>
              <span className="ml-auto text-[0.8125rem] text-slate-400" title="0 = no restriction; higher means the specification shuts out more manufacturers">restriction index <b className="text-ink font-mono">{m.restriction_index}</b></span>
            </div>
            <div className="space-y-1.5 mb-5">
              {m.funnel.map((f: any, i: number) => (
                <div key={i} className="grid grid-cols-[minmax(0,1fr)_2fr_110px] gap-3 items-center text-[0.8125rem]">
                  <span className="truncate text-slate-300" title={f.step}>{f.clause_key ? <b className="font-mono text-sky-300">Cl.{f.clause_key} </b> : null}{f.step}</span>
                  <Bar value={f.manufacturers} max={max} tone={f.manufacturers < 3 ? "bg-rose-500" : "bg-amber-400"} />
                  <span className="font-mono text-slate-400 text-right">{f.manufacturers} mfr · {f.products}</span>
                </div>
              ))}
            </div>
            <table className="w-full text-[0.8125rem]">
              <thead className="text-slate-500 uppercase"><tr><th className="text-left py-1">Clause</th><th className="text-left">Constraint</th><th>Tender</th><th>Standard</th><th>Excludes</th><th>If relaxed</th><th>Verdict</th></tr></thead>
              <tbody className="divide-y divide-slate-800">
                {m.clause_impacts.filter((c: any) => c.kind !== "licence").map((c: any) => (
                  <tr key={c.label} className={c.verdict === "restrictive" ? "bg-rose-500/5" : ""}>
                    <td className="py-1.5 font-mono text-sky-300">{c.clause_key}</td>
                    <td className="text-slate-300 max-w-xs truncate">{c.description}</td>
                    <td className="text-center font-mono">{c.tender_bounds?.filter((x: any) => x != null).join("–") || "—"}</td>
                    <td className="text-center font-mono text-slate-400">{c.standard_bounds?.filter((x: any) => x != null).join("–") || "—"}</td>
                    <td className="text-center font-mono">{c.manufacturers_excluded_by_this_clause}</td>
                    <td className="text-center font-mono">{c.manufacturers_if_relaxed_to_standard ?? "—"}</td>
                    <td className="text-center"><Badge className={c.verdict === "restrictive" ? "border-rose-500/50 text-rose-300" : c.verdict === "neutral" ? "border-slate-700 text-slate-400" : "border-amber-500/40 text-amber-300"}>{c.verdict.replaceAll("_", " ")}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[0.75rem] text-slate-500 mt-3">{m.catalogue_note} Contradictory clauses excluded from this analysis: {m.excluded_contradictory_requirements?.join(", ") || "none"}.</p>
          </Card>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------ standards, temporal, QCO */
export function Standards({ twin, tenderId, onChanged }: { twin: any; tenderId: string; onChanged: () => void }) {
  const [asOf, setAsOf] = useState(twin.tender.as_of);
  return (
    <div className="space-y-6">
      <Card className="flex flex-wrap items-center gap-3">
        <CalendarClock className="w-5 h-5 text-sky-300" />
        <div className="flex-1 min-w-[240px]">
          <div className="text-sm font-bold text-ink">Check the standards as they stood on a different date</div>
          <p className="text-[0.8125rem] text-slate-400">Every citation is resolved against the registry <i>as of</i> a date: which edition was valid, which amendments were in force, which QCOs applied. Change the date and the whole twin is re-compiled.</p>
        </div>
        <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} className="bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-200" />
        <Button onClick={async () => { await updateTender(tenderId, { as_of_date: asOf }); onChanged(); }}>Re-check on this date</Button>
      </Card>
      <Card>
        <div className="text-sm font-bold text-ink mb-3">Citations resolved (as of {twin.tender.as_of})</div>
        <table className="w-full text-xs">
          <thead className="text-[0.75rem] uppercase text-slate-500"><tr><th className="text-left py-1">Clause</th><th className="text-left">Cited</th><th>Status</th><th className="text-left">Applicable edition</th><th>Amendments</th><th className="text-left">Explanation</th></tr></thead>
          <tbody className="divide-y divide-slate-800">
            {twin.citations.map((c: any, i: number) => (
              <tr key={i}>
                <td className="py-2 font-mono text-sky-300">{c.clause_key}</td>
                <td className="font-mono text-ink">{c.citation}</td>
                <td className="text-center"><span className={cn("px-2 py-0.5 rounded-full border text-[0.75rem]", getStatusColor(c.status))}>{c.status.replaceAll("_", " ")}</span></td>
                <td className="font-mono text-emerald-300">{c.in_force?.is_number || c.replacement || "—"}</td>
                <td className="text-center font-mono">{(c.amendments_in_force || []).length}{(c.amendments_pending || []).length ? ` (+${c.amendments_pending.length} pending)` : ""}</td>
                <td className="text-[0.8125rem] text-slate-400 max-w-md">{c.explanation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {twin.corpus_check?.available && (
        <Card>
          <div className="text-sm font-bold text-ink mb-1">Cross-check against the Indian Standards corpus</div>
          <p className="text-[0.8125rem] text-slate-400 mb-3">{twin.corpus_check.note}</p>
          <table className="gov-table">
            <thead><tr><th>Cited</th><th>Standard (latest archived)</th><th>Compulsory certification</th><th>Its own references / tests not cited in this tender</th></tr></thead>
            <tbody>
              {twin.corpus_check.citations.map((c: any) => (
                <tr key={c.family}>
                  <td className="font-mono whitespace-nowrap">{c.citation}<div className="text-[0.75rem] text-slate-500">Cl. {c.clause_key || "—"}</div></td>
                  <td>{c.found ? <>
                      <b className="font-mono">{c.base}:{c.latest_archived_year}</b> <span className="text-slate-400">{c.title}</span>
                      {c.newer_edition_archived && <div className="text-[0.8125rem] font-bold text-[#8a5300]">Cited edition {c.cited_year} is older than the archived {c.latest_archived_year} edition</div>}
                    </> : <span className="text-[#8a1414] font-semibold">Not found in the catalogue — check the number</span>}</td>
                  <td className="text-[0.8125rem]">{c.certification?.length ? c.certification.map((x: any, i: number) => <div key={i}><b>{x.scheme}</b> — {x.order}</div>) : "—"}</td>
                  <td className="text-[0.8125rem]">
                    {c.not_cited_dependencies?.length ? c.not_cited_dependencies.slice(0, 6).map((d: any) => (
                      <div key={d.base}><span className="font-mono font-semibold">{d.base}</span> {d.title} <i className="text-slate-500">({d.kind.replace("_", " ")}{d.normative ? ", normative" : ""})</i></div>
                    )) : "—"}
                    {c.not_cited_dependencies?.length > 6 && <div className="text-slate-500">+{c.not_cited_dependencies.length - 6} more</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      <div className="grid lg:grid-cols-2 gap-6">
        {Object.entries(twin.domain_standards).map(([dom, ds]: any) => (
          <Card key={dom}>
            <div className="flex items-center gap-2 mb-2">
              <div className="text-sm font-bold text-ink capitalize">{dom}</div>
              <Badge className="border-slate-700 text-slate-300">{ds.source}</Badge>
              <span className="font-mono text-xs text-emerald-300 ml-auto">{ds.resolved} {ds.grade ? `· ${ds.grade}` : ""}</span>
            </div>
            <div className="text-[0.75rem] uppercase text-slate-500 mt-3 mb-1">Mandatory certification (QCO / CRS)</div>
            {[...ds.regulations_in_force, ...ds.regulations_upcoming].length === 0 ? <p className="text-xs text-slate-400">No mandatory order found in the curated registry.</p> :
              [...ds.regulations_in_force, ...ds.regulations_upcoming].map((g: any) => (
                <div key={g.key} className="rounded-lg bg-slate-950/60 border border-slate-800 p-2 mb-1.5 text-xs">
                  <div className="text-ink font-semibold">{g.title}</div>
                  <div className="text-[0.8125rem] text-slate-400">{g.scheme} · {g.issuing_authority} {g.notification_number ? `· ${g.notification_number}` : ""}</div>
                  <div className="flex gap-2 mt-1">
                    <Badge className="border-slate-700 text-slate-300">effective {g.effective_from || "date unverified"}</Badge>
                    <Badge className={g.verification_state === "source_checked" ? "border-emerald-500/40 text-emerald-300" : g.verification_state === "simulated" ? "border-violet-500/40 text-violet-300" : "border-amber-500/40 text-amber-300"}>{g.verification_state}</Badge>
                    {g.source_url && <a href={g.source_url} className="text-[0.75rem] text-sky-400 underline" target="_blank" rel="noreferrer">source</a>}
                  </div>
                </div>
              ))}
            {twin.missing_dependencies.filter((m: any) => m.affected_standard === ds.resolved).map((m: any, i: number) => (
              <div key={i} className="mt-3">
                <div className="text-[0.75rem] uppercase text-slate-500 mb-1 flex items-center gap-1"><Link2 className="w-3 h-3" />Normative dependencies not cited</div>
                {m.items.map((it: any) => <div key={it.is_number} className="text-[0.8125rem] text-slate-300">· <span className="font-mono text-amber-300">{it.is_number}</span> — {it.title} <span className="text-slate-500">({it.type.replaceAll("_", " ")})</span></div>)}
              </div>
            ))}
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------ tests & labs */
export function Tests({ twin }: { twin: any }) {
  const tp = twin.test_plan;
  const max = Math.max(tp.critical_path_days, 1);
  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-3 gap-3">
        <Card><div className="text-[0.75rem] uppercase text-slate-500">Distinct tests</div><div className="text-2xl font-mono text-ink">{tp.tests.length}</div><div className="text-[0.8125rem] text-slate-500">covering {tp.tests.reduce((a: number, t: any) => a + t.parameters.length, 0)} parameters</div></Card>
        <Card><div className="text-[0.75rem] uppercase text-slate-500">Critical path</div><div className="text-2xl font-mono text-ink flex items-center gap-2"><Clock3 className="w-5 h-5 text-sky-400" />{tp.critical_path_days} d</div><div className="text-[0.8125rem] text-slate-500">labs run in parallel</div></Card>
        <Card><div className="text-[0.75rem] uppercase text-slate-500">Labs used</div><div className="text-2xl font-mono text-ink">{tp.gantt.length}</div><div className="text-[0.8125rem] text-slate-500">{tp.lab_directory_note}</div></Card>
      </div>
      {tp.warnings.length > 0 && <Card className="border-amber-500/30">{tp.warnings.map((w: string, i: number) => <div key={i} className="text-xs text-amber-200">⚠ {w}</div>)}</Card>}
      <Card>
        <div className="text-sm font-bold text-ink mb-3 flex items-center gap-2"><FlaskConical className="w-4 h-4 text-emerald-300" />Laboratory route (Gantt)</div>
        <div className="space-y-2">
          {tp.gantt.map((g: any) => (
            <div key={g.lab_id} className="grid grid-cols-[220px_1fr] gap-3 items-center text-[0.8125rem]">
              <span className="text-slate-300 truncate" title={g.lab}>{g.lab}</span>
              <div className="relative h-6 bg-slate-900 rounded">
                <div className="absolute h-6 rounded bg-gradient-to-r from-emerald-600 to-sky-600 flex items-center px-2 text-[0.75rem] text-white whitespace-nowrap overflow-hidden"
                  style={{ left: `${(g.start_day / max) * 100}%`, width: `${Math.max(6, ((g.end_day - g.start_day) / max) * 100)}%` }}>{g.end_day} d · {g.tests.join(", ")}</div>
              </div>
            </div>
          ))}
        </div>
      </Card>
      <Card>
        <table className="w-full text-xs">
          <thead className="text-[0.75rem] uppercase text-slate-500"><tr><th className="text-left py-1">Test</th><th className="text-left">Method</th><th className="text-left">Parameters covered</th><th>Days</th><th>Cited?</th><th className="text-left">Accredited labs</th></tr></thead>
          <tbody className="divide-y divide-slate-800">
            {tp.tests.map((t: any) => (
              <tr key={t.test_id}>
                <td className="py-2 text-ink">{t.name}<div className="text-[0.75rem] text-slate-500">{t.sample} · {t.discipline}</div></td>
                <td className="font-mono text-sky-300">{t.standard}</td>
                <td className="text-slate-300">{t.parameters.join(", ")}</td>
                <td className="text-center font-mono">{t.days}</td>
                <td className="text-center">{t.cited_in_tender ? "✓" : <span className="text-amber-300">no</span>}</td>
                <td className="text-[0.8125rem] text-slate-400">{t.labs.map((l: any) => `${l.name} (${l.est_days}d)`).join("; ") || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {tp.consolidation.length > 0 && <div className="mt-3 text-[0.8125rem] text-emerald-300">{tp.consolidation.map((c: string, i: number) => <div key={i}>✓ {c}</div>)}</div>}
        {tp.duplicates.length > 0 && <div className="mt-2 text-[0.8125rem] text-amber-300">{tp.duplicates.map((d: any, i: number) => <div key={i}>⚠ {d.parameter}: {d.methods.join(", ")} — {d.note}</div>)}</div>}
      </Card>
    </div>
  );
}
