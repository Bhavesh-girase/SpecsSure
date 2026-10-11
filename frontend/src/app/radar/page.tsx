"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Radar, Zap, Bell, Search, Globe, ShieldAlert } from "lucide-react";
import { Badge, Button, Card, ErrorBox, SectionTitle } from "@/components/ui";
import { markNotificationsRead, notifications, qcoImpact, radarEvents, radarImpact, radarScenarios, radarSimulate, radarWatch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { PageIntro } from "@/components/gov-ui";

export default function RadarPage() {
  const [sc, setSc] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [notes, setNotes] = useState<any[]>([]);
  const [qco, setQco] = useState<any[]>([]);
  const [last, setLast] = useState<any>(null);
  const [std, setStd] = useState("IS 1608 (Part 1):2018");
  const [imp, setImp] = useState<any>(null);
  const [watch, setWatch] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = () => { radarEvents().then(setEvents); notifications().then(setNotes); qcoImpact().then(setQco); };
  useEffect(() => { radarScenarios().then(setSc).catch((e) => setErr(e.message)); load(); }, []);
  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <PageIntro icon={Radar} kicker="Regulatory radar · for procurement officers" title="Know when a rule change affects your tenders"
        sub="Standards get amended, replaced or withdrawn, and new Quality Control Orders make certification compulsory. The radar watches for these changes, finds every active tender that depends on the changed rule, re-checks it and tells you exactly what changed."
        steps={["Try a change: pick a simulated amendment, new edition or QCO below.", "See which tenders are affected and how their readiness score moved.", "Open an affected tender to fix it — alerts also appear under the bell icon."]}
        details={<>“Dependabot for tenders”: the impact set is found directly and through the normative-reference graph (a standard that depends on the changed one). Each affected tender’s Digital Twin is re-compiled and the owner is notified with the exact delta. Official source watchers poll BIS / ministry QCO pages, hash their content and raise a pending-triage event — nothing is auto-applied; a human confirms every regulatory change.</>} />
      <ErrorBox error={err} />
      <div className="grid lg:grid-cols-3 gap-6">
        <Card glow className="lg:col-span-2">
          <div className="text-sm font-bold text-ink mb-3 flex items-center gap-2"><Zap className="w-4 h-4 text-amber-300" />Inject a regulatory event (simulation)</div>
          <div className="grid sm:grid-cols-2 gap-2">
            {sc.map((s) => (
              <Button key={s.key} variant="subtle" className="justify-start text-left h-auto py-2" onClick={async () => { setLast(await radarSimulate(s.key)); load(); }}>
                <span><span className="font-mono text-[0.75rem] text-amber-300">{s.event_type}</span><br />{s.label}</span>
              </Button>
            ))}
          </div>
          {last && (
            <div className="mt-4 rounded-xl border border-sky-500/30 bg-sky-500/5 p-3 text-xs">
              <div className="text-ink font-semibold">{last.title}</div>
              <div className="text-slate-400">{last.kb_change}</div>
              <div className="text-slate-400">Impact set: direct {last.impact_set.direct.join(", ") || "—"} · via dependency graph {last.impact_set.dependents.join(", ") || "—"}</div>
              {last.affected_tenders.length === 0 ? <div className="text-emerald-300 mt-1">No active tender affected.</div> : last.affected_tenders.map((a: any) => (
                <div key={a.tender_id} className="mt-2 border-t border-slate-800 pt-2">
                  <Link href={`/tenders/${a.tender_id}`} className="text-sky-300 underline">{a.title}</Link> — {a.reason} · readiness {a.readiness_before} → <b>{a.readiness_after}</b>
                  {a.introduced?.map((d: any, i: number) => <div key={i} className="text-rose-200">+ {d.rule_id} Cl.{d.clause_key}: {d.message}</div>)}
                  {a.resolved?.map((d: any, i: number) => <div key={i} className="text-emerald-200">− {d.rule_id} Cl.{d.clause_key}</div>)}
                </div>
              ))}
            </div>
          )}
        </Card>
        <Card>
          <div className="flex items-center justify-between mb-2"><div className="text-sm font-bold text-ink flex items-center gap-2"><Bell className="w-4 h-4 text-sky-300" />Notifications</div>
            <button className="text-[0.75rem] text-slate-400 underline" onClick={async () => { await markNotificationsRead(); load(); }}>mark read</button></div>
          <div className="space-y-2 max-h-80 overflow-auto">
            {notes.length === 0 && <p className="text-xs text-slate-400">Nothing yet.</p>}
            {notes.map((n) => (
              <Link key={n.id} href={`/tenders/${n.tender_id}`} className={cn("block rounded-lg border p-2 text-[0.8125rem]", n.read ? "border-slate-800 opacity-60" : n.severity === "critical" ? "border-rose-500/40 bg-rose-500/5" : "border-amber-500/30")}>
                <div className="text-ink font-semibold">{n.title}</div><div className="text-slate-400">{n.message}</div>
              </Link>
            ))}
          </div>
        </Card>
      </div>
      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <div className="text-sm font-bold text-ink mb-2 flex items-center gap-2"><Search className="w-4 h-4 text-violet-300" />What-if impact analysis</div>
          <div className="flex gap-2"><input value={std} onChange={(e) => setStd(e.target.value)} className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-xs font-mono" />
            <Button onClick={async () => setImp(await radarImpact(std))}>Analyse</Button></div>
          {imp && <div className="mt-3 text-xs space-y-1">
            <div className="text-slate-400">Direct: {imp.impact_set.direct.join(", ")} · Dependents (reverse normative/test edges): <span className="text-amber-300">{imp.impact_set.dependents.join(", ") || "—"}</span></div>
            {imp.affected.map((a: any) => <div key={a.tender_id}>→ <Link className="text-sky-300 underline" href={`/tenders/${a.tender_id}`}>{a.title}</Link> <span className="text-slate-500">({a.reason})</span></div>)}
            {imp.affected.length === 0 && <div className="text-emerald-300">No tender affected.</div>}
          </div>}
        </Card>
        <Card>
          <div className="text-sm font-bold text-ink mb-2 flex items-center gap-2"><Globe className="w-4 h-4 text-emerald-300" />Official source watchers</div>
          <p className="text-[0.8125rem] text-slate-400 mb-2">Polls BIS / ministry QCO pages, hashes content, and raises a <i>pending-triage</i> event on change. Nothing is auto-applied — a human confirms every regulatory change.</p>
          <Button variant="subtle" onClick={async () => { setWatch(await radarWatch()); load(); }}>Check sources now</Button>
          {watch && watch.checked.map((w: any) => <div key={w.key} className="text-[0.8125rem] text-slate-300 mt-1">· {w.label}: <span className="font-mono text-slate-500">{w.status}</span> {w.changed ? <b className="text-amber-300">CHANGED</b> : w.first_seen ? "(baseline recorded)" : "(unchanged)"}</div>)}
        </Card>
      </div>
      <Card>
        <div className="text-sm font-bold text-ink mb-2 flex items-center gap-2"><ShieldAlert className="w-4 h-4 text-rose-300" />QCO Impact Radar — tenders under mandatory certification</div>
        <table className="w-full text-xs">
          <thead className="text-[0.75rem] uppercase text-slate-500"><tr><th className="text-left py-1">Tender</th><th>Domain</th><th>Standard</th><th className="text-left">Order</th><th>Effective</th><th>Data</th><th>Tender requires it?</th></tr></thead>
          <tbody className="divide-y divide-slate-800">
            {qco.map((q, i) => (
              <tr key={i}><td className="py-1.5"><Link className="text-sky-300 underline" href={`/tenders/${q.tender_id}`}>{q.tender.slice(0, 50)}</Link></td><td className="text-center capitalize">{q.domain}</td><td className="text-center font-mono">{q.standard}</td><td className="text-slate-300">{q.regulation}{q.upcoming ? " (upcoming)" : ""}</td><td className="text-center">{q.effective_from || "—"}</td>
                <td className="text-center"><Badge className="border-slate-700 text-slate-400">{q.verification_state}</Badge></td>
                <td className="text-center">{q.tender_requires_certification ? <span className="text-emerald-300">yes</span> : <span className="text-rose-300 font-bold">NO</span>}</td></tr>
            ))}
          </tbody>
        </table>
      </Card>
      <Card>
        <div className="text-sm font-bold text-ink mb-2">Event log</div>
        {events.map((e) => (
          <div key={e.id} className="text-[0.8125rem] border-b border-slate-800 py-1.5 flex gap-2">
            <span className="font-mono text-slate-500">#{e.id}</span><Badge className={e.simulated ? "border-violet-500/40 text-violet-300" : "border-slate-700 text-slate-300"}>{e.simulated ? "simulated" : e.status}</Badge>
            <span className="text-slate-200">{e.title}</span><span className="text-slate-500 ml-auto">effective {e.effective_from || "—"} · {e.impact?.affected?.length ?? 0} tender(s) re-validated</span>
          </div>
        ))}
      </Card>
    </div>
  );
}
