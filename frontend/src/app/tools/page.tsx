"use client";

import { useEffect, useState } from "react";
import { Scale, CalendarClock, Code2, BookOpen, Library } from "lucide-react";
import { Badge, Button, Card, SectionTitle, SevBadge, Tabs } from "@/components/ui";
import { addReview, compareStandards, equivalenceStandards, lintText, memorySearch, rules, temporalResolve, temporalTimeline } from "@/lib/api";
import { cn, getStatusColor } from "@/lib/utils";
import { PageIntro } from "@/components/gov-ui";

type T = "equivalence" | "time" | "lint" | "rules" | "memory";

export default function ToolsPage() {
  const [tab, setTab] = useState<T>("equivalence");
  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <PageIntro icon={Scale} kicker="Standards tools · for buyers, bidders and auditors" title="Standards tools"
        sub="Small, stand-alone tools that answer everyday standards questions. Pick a tool below." />
      <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3" role="tablist" aria-label="Tools">
        {([
          ["equivalence", Scale, "Compare two standards", "Is a foreign or older standard equivalent to the Indian one?"],
          ["time", CalendarClock, "Standard on a past date", "Which edition and amendments were in force on a given day?"],
          ["lint", Code2, "Check a clause", "Paste tender text and see what the checker flags."],
          ["rules", BookOpen, "List of checks", "Every rule the tender checker applies, with examples."],
          ["memory", Library, "Past tender lessons", "Search issues and clarifications from earlier tenders."],
        ] as const).map(([id, Icon, label, d]) => (
          <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id as T)}
            className={cn("text-left rounded-lg border p-3.5 bg-white transition-colors", tab === id ? "border-[#1d4f93] ring-2 ring-[#1d4f93]/15" : "border-[#d5deea] hover:border-[#7ea7db]")}>
            <span className="flex items-center gap-2 font-bold text-[#0f2748]"><Icon className={cn("w-4 h-4", tab === id ? "text-[#1d4f93]" : "text-slate-500")} />{label}</span>
            <span className="block text-[0.875rem] text-[#475569] mt-1 leading-snug">{d}</span>
          </button>
        ))}
      </div>
      {tab === "equivalence" && <Equivalence />}
      {tab === "time" && <TimeMachine />}
      {tab === "lint" && <LintPlayground />}
      {tab === "rules" && <RuleCatalogue />}
      {tab === "memory" && <MemorySearch />}
    </div>
  );
}

function Equivalence() {
  const [avail, setAvail] = useState<any>({});
  const [a, setA] = useState("IS 1786"); const [b, setB] = useState("BS 4449");
  const [ga, setGa] = useState("Fe 500D"); const [gb, setGb] = useState("B500B");
  const [r, setR] = useState<any>(null);
  const [done, setDone] = useState<string | null>(null);
  useEffect(() => { equivalenceStandards().then(setAvail); }, []);
  const sel = (v: string, set: any, g: string, setG: any) => (
    <div className="flex gap-2">
      <select value={v} onChange={(e) => { set(e.target.value); setG(avail[e.target.value]?.grades?.[0] || ""); }} className="bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-xs">
        {Object.keys(avail).map((k) => <option key={k}>{k}</option>)}
      </select>
      <select value={g} onChange={(e) => setG(e.target.value)} className="bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-xs">
        {(avail[v]?.grades || []).map((x: string) => <option key={x}>{x}</option>)}
      </select>
    </div>
  );
  const color: Record<string, string> = { equal: "text-emerald-300", stricter: "text-emerald-300", looser: "text-rose-300", not_controlled_by_b: "text-amber-300", only_in_b: "text-slate-400" };
  return (
    <div className="space-y-4">
      <Card className="flex flex-wrap items-center gap-3">
        <span className="text-xs text-slate-400">Reference (A)</span>{sel(a, setA, ga, setGa)}
        <span className="text-xs text-slate-400">Candidate (B)</span>{sel(b, setB, gb, setGb)}
        <Button onClick={async () => { setDone(null); setR(await compareStandards(a, b, ga, gb)); }}>Compare</Button>
      </Card>
      {r && (
        <>
          <Card glow className="flex flex-wrap items-center gap-4">
            <div className={cn("text-lg font-extrabold", r.verdict === "NOT_EQUIVALENT" ? "text-rose-300" : r.verdict === "PARTIALLY_COMPARABLE" ? "text-amber-300" : "text-emerald-300")}>{r.verdict.replaceAll("_", " ")}</div>
            <div className="text-xs text-slate-400">B covers {Math.round(r.coverage_of_a_by_b * 100)}% of A's controlled parameters at equal-or-stricter level · {r.summary.gaps} gap(s)</div>
            <Badge className="border-violet-500/40 text-violet-300 ml-auto">{r.decision_status.replaceAll("_", " ")}</Badge>
          </Card>
          {r.regulatory_implication && <Card className="border-rose-500/40 text-xs text-rose-200">⚖ {r.regulatory_implication}</Card>}
          <Card>
            <table className="w-full text-xs">
              <thead className="text-[0.75rem] uppercase text-slate-500"><tr><th className="text-left py-1">Parameter</th><th>{r.a.family} {r.a.grade}</th><th>{r.b.family} {r.b.grade}</th><th>B vs A</th></tr></thead>
              <tbody className="divide-y divide-slate-800">
                {r.parameters.map((p: any) => (
                  <tr key={p.parameter}><td className="py-1.5 text-slate-200">{p.label}</td>
                    <td className="text-center font-mono">{p.a ? `${p.a.min != null ? "≥" + p.a.min : ""} ${p.a.max != null ? "≤" + p.a.max : ""}` : "—"}</td>
                    <td className="text-center font-mono">{p.b ? `${p.b.min != null ? "≥" + p.b.min : ""} ${p.b.max != null ? "≤" + p.b.max : ""}` : "—"}</td>
                    <td className={cn("text-center font-semibold", color[p.b_vs_a])}>{p.b_vs_a.replaceAll("_", " ")}</td></tr>
                ))}
              </tbody>
            </table>
            <div className="mt-3 text-[0.8125rem] text-slate-400">Test methods: {r.test_methods.map((t: any) => `${t.property}: ${t.a || "—"} vs ${t.b || "—"}`).join(" · ")}</div>
            {r.test_method_note && <div className="text-[0.8125rem] text-amber-300 mt-1">{r.test_method_note}</div>}
            <p className="text-[0.8125rem] text-slate-500 mt-2">{r.disclaimer}</p>
            <div className="flex gap-2 mt-3">
              {["approved", "rejected", "needs_info"].map((d) => (
                <Button key={d} variant={d === "approved" ? "success" : d === "rejected" ? "danger" : "ghost"}
                  onClick={async () => { await addReview({ subject_type: "equivalence", subject_id: `${a}:${ga}|${b}:${gb}`, decision: d, reviewer: "Technical committee", data: { verdict: r.verdict } }); setDone(d); }}>
                  Committee: {d.replace("_", " ")}
                </Button>
              ))}
              {done && <span className="text-xs text-emerald-300 self-center">Decision “{done}” recorded in the audit ledger.</span>}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

function TimeMachine() {
  const [cit, setCit] = useState("IS 8112:1989");
  const [date, setDate] = useState("2012-01-01");
  const [r, setR] = useState<any>(null);
  const [tl, setTl] = useState<any>(null);
  const run = async (d = date) => { setR(await temporalResolve(cit, d)); setTl(await temporalTimeline(cit)); };
  const years = [1990, 2000, 2008, 2012, 2014, 2016, 2020, 2026];
  return (
    <div className="space-y-4">
      <Card className="flex flex-wrap items-center gap-3">
        <input value={cit} onChange={(e) => setCit(e.target.value)} className="bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-xs font-mono w-56" />
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-xs" />
        <Button onClick={() => run()}>Resolve</Button>
        <div className="flex gap-1 ml-auto">{years.map((y) => <button key={y} onClick={() => { const d = `${y}-06-01`; setDate(d); run(d); }} className="px-2 py-1 text-[0.75rem] rounded border border-slate-700 text-slate-300 hover:border-sky-500">{y}</button>)}</div>
      </Card>
      {r && (
        <Card glow>
          <div className="flex items-center gap-3 mb-2"><span className={cn("px-2 py-0.5 rounded-full border text-xs", getStatusColor(r.status))}>{r.status.replaceAll("_", " ")}</span><span className="text-sm text-ink">{r.explanation}</span></div>
          <div className="text-xs text-slate-400">Applicable: <b className="font-mono text-emerald-300">{r.in_force?.is_number || "—"}</b> · amendments in force: {r.amendments_in_force.map((a: any) => `Amd ${a.number}`).join(", ") || "none"} · QCO in force: {r.regulations_in_force.map((g: any) => g.title).join("; ") || "none"}</div>
        </Card>
      )}
      {tl && (
        <Card>
          <div className="text-sm font-bold text-ink mb-3">Edition timeline — {tl.family}</div>
          <div className="space-y-2">
            {tl.editions.map((e: any) => (
              <div key={e.is_number} className="grid grid-cols-[180px_1fr] gap-3 items-center text-xs">
                <span className="font-mono text-slate-200">{e.is_number}</span>
                <div className="flex items-center gap-2"><span className={cn("px-2 py-0.5 rounded border text-[0.75rem]", getStatusColor(e.status))}>{e.status}</span><span className="text-slate-400">{e.from || "?"} → {e.to || "present"}</span>{e.superseded_by && <span className="text-amber-300">superseded by {e.superseded_by}</span>}</div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function LintPlayground() {
  const [text, setText] = useState("4.1 Material: Bars shall be of good quality and conform to IS 1786 Grade Fe 500D.\n4.2 The yield stress shall not be less than 500 N/mm2.\n4.3 The yield stress shall not exceed 480 N/mm2.\n4.4 Make: TATA Tiscon only.\n5.1 Delivery within 10 days.");
  const [tw, setTw] = useState<any>(null);
  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <Card>
        <textarea value={text} onChange={(e) => setText(e.target.value)} className="w-full h-72 bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs font-mono" />
        <Button className="mt-2" onClick={async () => setTw(await lintText(text))}>Lint (stateless — nothing stored)</Button>
      </Card>
      <Card>
        {!tw ? <p className="text-xs text-slate-400">Results appear here. Same engine as the Digital Twin; also available as an MCP tool for AI assistants.</p> : (
          <div className="space-y-2">
            <div className="text-xs text-slate-300">Readiness <b className="text-ink">{Math.round(tw.readiness.score)}</b> · {tw.readiness.gate} · solver: {tw.verification.satisfiable ? "SAT" : "UNSAT"}</div>
            {tw.findings.map((f: any) => (
              <div key={f.fingerprint} className="text-xs border-b border-slate-800 pb-1.5"><SevBadge sev={f.severity} /> <span className="font-mono text-[0.75rem] text-slate-400">{f.rule_id} Cl.{f.clause_key}</span><div className="text-slate-200">{f.message}</div></div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function RuleCatalogue() {
  const [rs, setRs] = useState<any[]>([]);
  useEffect(() => { rules().then(setRs); }, []);
  return (
    <Card>
      <div className="text-xs text-slate-400 mb-3">{rs.length} rules. Stable IDs → findings are fingerprinted and their review status survives re-compilation, like code-scanning alerts.</div>
      <div className="grid md:grid-cols-2 gap-2">
        {rs.map((r) => (
          <div key={r.id} className="rounded-lg border border-slate-800 bg-slate-950/50 p-2.5 text-xs">
            <div className="flex items-center gap-2"><span className="font-mono text-sky-300">{r.id}</span><SevBadge sev={r.default_severity} /><Badge className="border-slate-700 text-slate-400">{r.category}</Badge></div>
            <div className="text-ink font-semibold mt-1">{r.name}</div>
            <div className="text-slate-400 text-[0.8125rem]">{r.description}</div>
            {r.basis && <div className="text-[0.75rem] text-violet-300 mt-1">{r.basis}</div>}
          </div>
        ))}
      </div>
    </Card>
  );
}

function MemorySearch() {
  const [q, setQ] = useState("Carbon content shall not exceed 0.18%");
  const [r, setR] = useState<any>(null);
  return (
    <div className="space-y-4">
      <Card className="flex gap-2"><input value={q} onChange={(e) => setQ(e.target.value)} className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs" /><Button onClick={async () => setR(await memorySearch(q))}>Search memory</Button></Card>
      {r && (
        <div className="grid lg:grid-cols-2 gap-4">
          <Card><div className="text-sm font-bold text-ink mb-2">Clause precedents</div>
            {r.clause_precedents.map((h: any, i: number) => (
              <div key={i} className="text-xs border-b border-slate-800 py-2"><div className="text-slate-200">“{h.text}”</div>
                <div className="text-[0.8125rem] text-slate-400">{h.tender_ref} Cl.{h.clause_key} · sim {h.score} · issues {h.issues.join(", ") || "—"}</div>
                {h.prebid_questions.map((x: string, j: number) => <div key={j} className="text-[0.8125rem] text-sky-200">Q: {x}</div>)}
                {h.resolution && <div className="text-[0.8125rem] text-emerald-300">→ {h.resolution}</div>}</div>
            ))}</Card>
          <Card><div className="text-sm font-bold text-ink mb-2">Similar tenders</div>
            {r.similar_tenders.map((t: any) => <div key={t.ref} className="text-xs py-1.5 border-b border-slate-800"><div className="text-slate-200">{t.title}</div><div className="text-[0.8125rem] text-slate-400">{t.ref} · {t.outcome}</div></div>)}</Card>
        </div>
      )}
    </div>
  );
}
