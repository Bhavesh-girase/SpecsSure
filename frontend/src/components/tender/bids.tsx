"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Users, Scale, Wand2, AlertTriangle } from "lucide-react";
import { Card, Empty, Loading, SectionTitle, Bar } from "@/components/ui";
import { comparativeStatement, tenderGeneration } from "@/lib/api";
import { StatusPill, TIER } from "@/components/market/match";
import { BASIS, PathChips } from "@/components/studio/common";
import { cn } from "@/lib/utils";

export function BidsComparative({ tenderId }: { tenderId: string }) {
  const [d, setD] = useState<any>(null);
  const [onlyDiff, setOnlyDiff] = useState(true);
  useEffect(() => { comparativeStatement(tenderId).then(setD).catch(() => setD({ bidders: [], rows: [], notes: [] })); }, [tenderId]);
  if (!d) return <Loading />;
  if (!d.bidders.length) return <Empty>No bids yet. Contractors bid from the <Link className="underline" href={`/market/${tenderId}`}>smart bid form</Link> (tender must be published).</Empty>;
  const rows = d.rows.filter((r: any) => !onlyDiff || new Set(r.cells.map((c: any) => c.status)).size > 1 || r.cells.some((c: any) => ["FAILS", "CONFLICT", "MISSING"].includes(c.status)));
  return (
    <div className="space-y-4">
      <SectionTitle title="Comparative statement of technical bids" icon={<Users className="w-5 h-5 text-emerald-300" />}
        subtitle={d.disclaimer} right={<label className="text-xs text-slate-400 flex items-center gap-1.5"><input type="checkbox" checked={onlyDiff} onChange={(e) => setOnlyDiff(e.target.checked)} /> only rows that differentiate</label>} />
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
        {d.bidders.map((b: any, i: number) => {
          const t = TIER[b.tier] || { label: b.tier, cls: "" };
          return (
            <Card key={b.bid_id} className="p-4">
              <div className="flex items-center gap-2">
                <span className="text-[0.8125rem] font-mono text-slate-500">#{i + 1}</span>
                <Link href={`/bids/${b.bid_id}`} className="text-sm font-bold text-ink hover:underline flex-1">{b.bidder}</Link>
                <span className="font-mono text-xl font-extrabold text-ink">{Math.round(b.match_index)}</span>
              </div>
              <div className="text-[0.8125rem] text-slate-400">{b.product_name} · quoting {b.scope?.join(", ")}</div>
              <div className={cn("text-xs font-bold mt-1", t.cls)}>{t.label}{b.knockouts ? ` · ${b.knockouts} knock-out(s)` : ""}</div>
              <div className="mt-2"><Bar value={b.match_index} /></div>
            </Card>
          );
        })}
      </div>
      {d.notes.map((n: string, i: number) => <div key={i} className="text-xs text-amber-200 flex gap-1.5"><AlertTriangle className="w-4 h-4" />{n}</div>)}
      <Card className="p-0 overflow-x-auto">
        <table className="w-full text-[0.8125rem]">
          <thead className="bg-slate-900/80">
            <tr>
              <th className="text-left p-2 text-slate-400 font-semibold">Clause · requirement</th>
              {d.bidders.map((b: any) => <th key={b.bid_id} className="p-2 text-left text-slate-300 font-semibold">{b.bidder}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((r: any) => (
              <tr key={r.field_id} className="border-t border-slate-800 align-top">
                <td className="p-2 text-slate-300"><span className="font-mono text-slate-500 mr-1">{r.clause_key}</span><b>{r.label}</b><div className="text-slate-500">{r.requirement}</div></td>
                {d.bidders.map((b: any) => {
                  const c = r.cells.find((x: any) => x.bid_id === b.bid_id);
                  return <td key={b.bid_id} className="p-2"><StatusPill s={c?.status || "N/A"} /><div className="text-slate-400 mt-0.5">{c?.detail}</div>{c?.evidence && c.status !== "N/A" && <div className="text-slate-400">{c.evidence}</div>}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

export function StudioProvenance({ tenderId }: { tenderId: string }) {
  const [g, setG] = useState<any>(null);
  const [none, setNone] = useState(false);
  useEffect(() => { tenderGeneration(tenderId).then(setG).catch(() => setNone(true)); }, [tenderId]);
  if (none) return <Empty>This tender was uploaded, not generated in the Tender Studio.</Empty>;
  if (!g) return <Loading />;
  return (
    <div className="space-y-4">
      <SectionTitle title="How this tender was generated" icon={<Wand2 className="w-5 h-5 text-sky-300" />}
        subtitle={`Request: “${g.intent?.input}” · generator ${g.generator} · knowledge-graph snapshot ${g.kg_snapshot} · as of ${g.as_of}`} />
      <div className="grid md:grid-cols-3 gap-3">
        {g.verification.passes.map((p: any) => (
          <Card key={p.pass} className="p-3 text-[0.8125rem]"><b className="text-ink">Compiler pass {p.pass}</b> — {Math.round(p.readiness)} · {p.gate}
            {p.auto_repaired.map((r: any, i: number) => <div key={i} className="text-fuchsia-300">auto-repaired {r.rule_id}</div>)}</Card>
        ))}
      </div>
      {g.competition_guard?.map((c: any, i: number) => <div key={i} className="text-xs text-amber-200"><Scale className="w-3.5 h-3.5 inline mr-1" />{c.reason}</div>)}
      <div className="space-y-3">
        {g.sections.map((s: any) => (
          <Card key={s.no} className="p-4">
            <div className="text-sm font-bold text-ink mb-2">{s.no}. {s.title}</div>
            {s.clauses.map((c: any) => {
              const b = BASIS[c.basis] || BASIS.practice;
              return (
                <div key={c.key} className={cn("rounded-lg border-l-4 border px-3 py-2 mb-1.5", b.cls)}>
                  <div className="text-[0.875rem] text-slate-200"><span className="font-mono text-slate-500 mr-1">{c.key}</span><b>{c.heading}</b> <span className="text-[0.75rem] text-slate-400">· {b.label}</span></div>
                  {(c.provenance || []).filter((p: any) => p.path).slice(0, 3).map((p: any, i: number) => <PathChips key={i} path={p.path} />)}
                </div>
              );
            })}
          </Card>
        ))}
      </div>
    </div>
  );
}
