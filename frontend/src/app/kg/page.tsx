"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ReactFlow, Background, Controls, MarkerType, Handle, Position } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Network, Search, Download, CalendarClock, Boxes, BookMarked, ShieldCheck, Landmark, FlaskConical, Factory, SlidersHorizontal, GitBranch, Layers, Sigma } from "lucide-react";
import { Badge, Card, ErrorBox, Loading, SectionTitle, Disclaimer } from "@/components/ui";
import { fileUrl, kgItem, kgNode, kgSearch, kgStats, studioCatalogue } from "@/lib/api";
import { cn } from "@/lib/utils";
import { PageIntro } from "@/components/gov-ui";

const ORDER = ["item", "parameter", "standard_family", "standard", "amendment", "regulation", "policy", "lab", "manufacturer", "product"];
const COLORS: Record<string, string> = {
  item: "#1d4f93", parameter: "#6d28d9", standard_family: "#059669", standard: "#047857", amendment: "#b45309",
  regulation: "#be123c", policy: "#9333ea", lab: "#0e7490", manufacturer: "#475569", product: "#64748b",
};
const TYPE_LABEL: Record<string, string> = { standard_family: "standard family", standard: "edition" };

function KgNodeView({ data }: any) {
  const c = COLORS[data.type] || "#64748b";
  return (
    <div className={cn("rounded-lg px-2.5 py-1.5 text-[0.75rem] max-w-[185px] border backdrop-blur", data.center && "ring-2 ring-white/70")}
      style={{ borderColor: c, background: `${c}${data.valid === false ? "0d" : "14"}`, color: data.valid === false ? "#94a3b8" : "#0f2748", borderStyle: data.valid === false ? "dashed" : "solid" }}>
      <Handle type="target" position={Position.Left} style={{ background: c, width: 6, height: 6 }} />
      <div className="uppercase tracking-wider font-bold" style={{ color: c, fontSize: 8 }}>
        {TYPE_LABEL[data.type] || data.type}{data.status ? ` · ${data.status}` : ""}{data.valid === false ? " · not valid on date" : ""}
      </div>
      <div className="font-semibold leading-snug line-clamp-2">{data.label}</div>
      <Handle type="source" position={Position.Right} style={{ background: c, width: 6, height: 6 }} />
    </div>
  );
}
const nodeTypes = { kg: KgNodeView };

function Explorer() {
  const params = useSearchParams();
  const [stats, setStats] = useState<any>(null);
  const [cat, setCat] = useState<any>(null);
  const [center, setCenter] = useState(params?.get("node") || "item:led_lamp");
  const [asOf, setAsOf] = useState(new Date().toISOString().slice(0, 10));
  const [depth, setDepth] = useState(2);
  const [data, setData] = useState<any>(null);
  const [sel, setSel] = useState<any>(null);
  const [bundle, setBundle] = useState<any>(null);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [hideMarket, setHideMarket] = useState(true);
  const [hidePolicy, setHidePolicy] = useState(true);

  useEffect(() => { kgStats().then(setStats).catch((e) => setErr(e.message)); studioCatalogue().then(setCat).catch(() => {}); }, []);
  useEffect(() => {
    setData(null);
    kgNode(center, depth, asOf, depth > 1 ? 110 : 60).then((d: any) => { setData(d); setSel(d.node); }).catch((e) => setErr(e.message));
    if (center.startsWith("item:")) kgItem(center.slice(5), asOf).then(setBundle).catch(() => setBundle(null)); else setBundle(null);
  }, [center, asOf, depth]);
  useEffect(() => {
    if (q.length < 2) { setHits([]); return; }
    const t = setTimeout(() => kgSearch(q).then(setHits).catch(() => {}), 200);
    return () => clearTimeout(t);
  }, [q]);

  const { nodes, edges } = useMemo(() => {
    if (!data) return { nodes: [], edges: [] };
    const g = data.graph;
    const keep = g.nodes.filter((n: any) => (!(hideMarket && ["product", "manufacturer"].includes(n.type)) && !(hidePolicy && n.type === "policy")) || n.id === center);
    const ids = new Set(keep.map((n: any) => n.id));
    const rows: Record<string, number> = {};
    const present = ORDER.filter((t) => keep.some((n: any) => n.type === t));
    const nodes = keep.map((n: any) => {
      const col = present.indexOf(n.type) >= 0 ? present.indexOf(n.type) : present.length;
      const r = (rows[n.type] = (rows[n.type] ?? -1) + 1);
      return { id: n.id, type: "kg", position: { x: col * 215, y: r * 58 }, data: { ...n, center: n.id === center } };
    });
    const edges = g.edges.filter((e: any) => ids.has(e.source) && ids.has(e.target)).map((e: any, i: number) => ({
      id: `${e.source}-${e.rel}-${e.target}-${i}`, source: e.source, target: e.target,
      label: e.label + (e.role ? ` (${e.role})` : "") + (e.grade ? ` [${e.grade}${e.min != null ? " ≥" + e.min : ""}${e.max != null ? " ≤" + e.max : ""}]` : ""),
      animated: e.rel === "MANDATES",
      style: { stroke: e.valid === false ? "#cbd5e1" : e.rel === "MANDATES" ? "#be123c" : e.rel === "SUPERSEDED_BY" ? "#b45309" : "#475569", strokeDasharray: e.valid === false ? "4 4" : undefined },
      labelStyle: { fill: "#475569", fontSize: 8 }, labelBgStyle: { fill: "#ffffff" }, labelBgPadding: [3, 1] as [number, number],
      markerEnd: { type: MarkerType.ArrowClosed, color: "#475569" },
    }));
    return { nodes, edges };
  }, [data, center, hideMarket, hidePolicy]);

  return (
    <div className="space-y-5">
      <ErrorBox error={err} />
      <div className="grid lg:grid-cols-[300px_1fr_360px] gap-4">
        {/* left: navigation */}
        <Card className="space-y-3 p-4">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-2.5 top-2.5 text-slate-500" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search IS 16102, QCO, efficacy…" className="w-full pl-8 pr-2 py-2 rounded-lg bg-slate-950 border border-slate-700 text-sm text-ink" />
            {hits.length > 0 && (
              <div className="absolute z-20 mt-1 w-full rounded-lg bg-slate-900 border border-slate-700 max-h-72 overflow-y-auto">
                {hits.map((h) => (
                  <button key={h.id} onClick={() => { setCenter(h.id); setQ(""); }} className="block w-full text-left px-2.5 py-1.5 text-xs hover:bg-slate-800">
                    <span className="text-[0.75rem] uppercase font-bold mr-1.5" style={{ color: COLORS[h.type] }}>{h.type}</span><span className="text-slate-200">{h.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div>
            <div className="text-[0.75rem] uppercase tracking-widest text-slate-500 font-bold mb-1.5">Procurement items</div>
            <div className="flex flex-wrap gap-1.5">
              {(cat?.items || []).map((it: any) => (
                <button key={it.id} onClick={() => setCenter(`item:${it.id}`)}
                  className={cn("text-[0.8125rem] px-2 py-1 rounded-lg border", center === `item:${it.id}` ? "border-sky-400 bg-sky-500/15 text-sky-200" : "border-slate-700 text-slate-300 hover:border-sky-500/50")}>
                  {it.label.split("(")[0]}
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-1.5 text-xs">
            <label className="text-slate-400 flex items-center gap-1"><CalendarClock className="w-3.5 h-3.5" /> As of (valid-time)</label>
            <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} className="w-full rounded-lg bg-slate-950 border border-slate-700 px-2 py-1.5 text-ink" />
            <div className="flex gap-1.5">
              {["2024-01-01", "2026-06-01", new Date().toISOString().slice(0, 10), "2027-03-01"].map((d) => (
                <button key={d} onClick={() => setAsOf(d)} className={cn("text-[0.75rem] px-1.5 py-0.5 rounded border", asOf === d ? "border-sky-400 text-sky-200" : "border-slate-700 text-slate-400")}>{d}</button>
              ))}
            </div>
            <label className="text-slate-400 flex items-center justify-between">Depth
              <select value={depth} onChange={(e) => setDepth(Number(e.target.value))} className="bg-slate-950 border border-slate-700 rounded px-1.5 py-0.5 text-ink">
                <option value={1}>1 hop</option><option value={2}>2 hops</option><option value={3}>3 hops</option>
              </select>
            </label>
            <label className="text-slate-400 flex items-center gap-2"><input type="checkbox" checked={!hideMarket} onChange={(e) => setHideMarket(!e.target.checked)} /> show market layer (products, makers)</label>
            <label className="text-slate-400 flex items-center gap-2"><input type="checkbox" checked={!hidePolicy} onChange={(e) => setHidePolicy(!e.target.checked)} /> show policy layer (GFR, MII, MSE)</label>
          </div>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {ORDER.map((t) => <span key={t} className="text-[0.75rem] px-1.5 py-0.5 rounded-full border" style={{ borderColor: COLORS[t], color: COLORS[t] }}>{TYPE_LABEL[t] || t}</span>)}
          </div>
          <p className="text-[0.75rem] text-slate-500">Dashed = not valid on the selected date (withdrawn edition, order not yet in force). Red animated edges = a regulation making a standard mandatory.</p>
        </Card>

        {/* center: graph */}
        <div className="h-[660px] rounded-2xl border border-slate-800 bg-slate-950/70 overflow-hidden">
          {!data ? <Loading label="Traversing the graph…" /> : (
            <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.05 }} minZoom={0.1} onNodeClick={(_, n) => setSel(n.data)}
              onNodeDoubleClick={(_, n) => setCenter(n.id)} proOptions={{ hideAttribution: true }}>
              <Background color="#d5deea" gap={24} />
              <Controls />
            </ReactFlow>
          )}
        </div>

        {/* right: inspector */}
        <div className="space-y-4 max-h-[660px] overflow-y-auto pr-1">
          {sel && (
            <Card className="p-4">
              <div className="text-[0.75rem] uppercase tracking-widest font-bold" style={{ color: COLORS[sel.type] }}>{TYPE_LABEL[sel.type] || sel.type}</div>
              <div className="text-sm font-bold text-ink">{sel.label}</div>
              {sel.title && sel.title !== sel.label && <div className="text-[0.8125rem] text-slate-400">{sel.title}</div>}
              <div className="grid grid-cols-2 gap-x-2 gap-y-1 mt-2 text-[0.8125rem]">
                {["status", "valid_from", "valid_to", "verification_state", "scheme", "authority", "unit", "regulation_type", "hsn", "domain"].filter((k) => sel[k]).map((k) => (
                  <div key={k} className="contents"><span className="text-slate-500">{k.replaceAll("_", " ")}</span><span className="text-slate-200 break-words">{String(sel[k])}</span></div>
                ))}
              </div>
              {sel.summary && <p className="text-[0.8125rem] text-slate-400 mt-2">{sel.summary}</p>}
              {sel.source_url && <a href={sel.source_url} target="_blank" rel="noreferrer" className="text-[0.8125rem] text-sky-300 underline mt-1 inline-block">source</a>}
              {sel.id !== center && <button onClick={() => setCenter(sel.id)} className="block mt-2 text-[0.8125rem] text-sky-300 hover:underline">Re-centre graph here →</button>}
              {sel.id === center && data?.impacted_items?.length > 0 && (
                <div className="mt-3 text-[0.8125rem]"><div className="text-slate-500 font-bold uppercase text-[0.75rem]">If this changes, these items (and their tenders) are re-validated</div>
                  <div className="flex flex-wrap gap-1 mt-1">{data.impacted_items.map((i: string) => <button key={i} onClick={() => setCenter(i)} className="px-1.5 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-200">{i.slice(5)}</button>)}</div>
                </div>
              )}
            </Card>
          )}
          {bundle && <BundleCard b={bundle} />}
        </div>
      </div>
      {stats && (
        <div className="flex flex-wrap gap-2 text-[0.8125rem] text-slate-400">
          <Badge className="border-slate-700 text-slate-300">{stats.nodes} nodes</Badge>
          <Badge className="border-slate-700 text-slate-300">{stats.edges} edges</Badge>
          {Object.entries(stats.node_types).map(([k, v]: any) => <span key={k} style={{ color: COLORS[k] }}>{TYPE_LABEL[k] || k}: {v}</span>)}
          <span className="ml-auto font-mono">KB snapshot {stats.snapshot}</span>
        </div>
      )}
    </div>
  );
}

function BundleCard({ b }: { b: any }) {
  return (
    <Card className="p-4">
      <div className="text-[0.75rem] uppercase tracking-widest text-sky-400 font-bold">Requirements bundle · as of {b.as_of}</div>
      <div className="text-sm font-bold text-ink">{b.item.label}</div>
      <div className="text-[0.8125rem] text-slate-500">unit {b.item.default_unit} · HSN {b.item.hsn} · market {b.market.manufacturers} makers / {b.market.products} models (synthetic)</div>
      <div className="mt-3 space-y-1">
        <div className="text-[0.75rem] uppercase font-bold text-emerald-300">Standards (edition in force)</div>
        {b.standards.map((s: any) => (
          <div key={s.designation} className="text-[0.8125rem]"><span className="font-mono text-emerald-200">{s.cite_as}</span> <span className="text-slate-500">· {s.role}</span>
            {s.concurrent_editions.map((c: any) => <div key={c.is_number} className="pl-3 text-amber-300">↳ {c.is_number} until {c.valid_to}</div>)}
            {s.amendments_in_force.length > 0 && <div className="pl-3 text-slate-400">{s.amendments_in_force.length} amendment(s) in force</div>}
          </div>
        ))}
        <div className="text-[0.75rem] uppercase font-bold text-rose-300 pt-2">Mandatory regulations in force</div>
        {b.regulations_in_force.map((g: any) => <div key={g.key} className="text-[0.8125rem] text-slate-300">{g.title} <span className="text-slate-500">· {g.scheme} · {g.verification_state}</span></div>)}
        {b.regulations_upcoming.map((g: any) => <div key={g.key} className="text-[0.8125rem] text-sky-300">Upcoming {g.effective_from}: {g.title}</div>)}
        {b.watchlist.length > 0 && <>
          <div className="text-[0.75rem] uppercase font-bold text-amber-300 pt-2">Watchlist</div>
          {b.watchlist.map((w: any, i: number) => <div key={i} className="text-[0.8125rem] text-amber-100/90">{w.date}: {w.message}</div>)}
        </>}
        <div className="text-[0.75rem] uppercase font-bold text-cyan-300 pt-2">Tests → accredited labs</div>
        {b.tests.map((t: any, i: number) => <div key={i} className="text-[0.8125rem] text-slate-300">{t.name} <span className="font-mono text-slate-500">({t.cite_as})</span> → {t.labs.join(", ") || "no lab in directory"}</div>)}
        <div className="text-[0.75rem] uppercase font-bold text-sky-300 pt-2">Buyer decisions (slots)</div>
        <div className="flex flex-wrap gap-1">{b.slots.map((s: any) => <span key={s.id} className={cn("text-[0.75rem] px-1.5 py-0.5 rounded border", s.ask ? "border-sky-500/50 text-sky-200" : "border-slate-700 text-slate-400")}>{s.label}{s.ask ? " (asked)" : ""}</span>)}</div>
      </div>
    </Card>
  );
}

const SCHEMA = [
  { icon: Boxes, t: "Item", d: "what is bought (LED lamp, wire, fan, MCB, cement, TMT, solar module, street light) with aliases in English, Hindi and Hinglish, HSN, unit of account", c: COLORS.item },
  { icon: BookMarked, t: "Standard family → editions", d: "valid-time intervals; supersession chains; concurrent-running periods (IS 16102 (Part 1):2012 → 2026)", c: COLORS.standard },
  { icon: ShieldCheck, t: "Regulation", d: "QCO / CRS / BEE label / ALMM with effective dates and a per-record verification state", c: COLORS.regulation },
  { icon: SlidersHorizontal, t: "Parameter", d: "units, synonyms, grade limits (SPECIFIES) and the test method that measures it (MEASURED_BY)", c: COLORS.parameter },
  { icon: FlaskConical, t: "Lab", d: "accreditation scope → which lab can run which test", c: COLORS.lab },
  { icon: Landmark, t: "Policy", d: "GFR 2017 rules, Make-in-India, MSE policy → clauses and procurement route", c: COLORS.policy },
  { icon: Factory, t: "Market", d: "manufacturers → products → certified-to → item (competition estimates)", c: COLORS.manufacturer },
];

export default function KgPage() {
  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <PageIntro icon={Network} kicker="Knowledge graph · how everything connects" title="How items, standards, rules, tests and labs connect"
        sub="Every tender, bid check and alert on this portal uses one connected map: what is being bought → which Indian Standard applies → which edition and amendments are in force → which regulations make certification compulsory → which tests prove it → which labs can test it → which manufacturers can supply it. Pick an item below to explore its map for any date."
        steps={["Search or pick a procurement item on the left.", "Choose the date you care about (rules change over time).", "Click any box in the map to see its details and source."]}
        details={<>
          <p>This <b>procurement graph</b> (items, parameters, regulations, labs, policies — curated, time-aware) sits on top of the <b>Indian Standards graph</b>: 29,875 standards, 80,834 typed links read from 19,492 full texts (references, test methods, terminology, dimensions…), editions and withdrawals from the <b>BIS portal</b>, 828 compulsory-certification rows and 821 <b>GeM categories</b> that specify a standard.</p>
          <p className="mt-2">Item → Standard → Edition → Amendment → Normative reference → Regulation → Parameter → Test → Lab → Manufacturer → Product, plus the GFR policy layer. Every node and edge has a validity interval, a source and a verification state — so every question is asked as of a date and every answer returns the path that produced it.</p>
        </>}
        right={<div className="flex gap-2">
          <a href={fileUrl("/kg/export.cypher")} className="text-[0.875rem] px-3 py-2 rounded-md border border-[#c9d5e6] text-[#0f2748] hover:bg-[#eef4fb] flex items-center gap-1.5 font-semibold"><Download className="w-4 h-4" /> Neo4j (Cypher)</a>
          <a href={fileUrl("/kg/export.jsonld")} target="_blank" rel="noreferrer" className="text-[0.875rem] px-3 py-2 rounded-md border border-[#c9d5e6] text-[#0f2748] hover:bg-[#eef4fb] flex items-center gap-1.5 font-semibold"><Download className="w-4 h-4" /> JSON-LD</a>
        </div>} />

      <Suspense fallback={<Loading />}><Explorer /></Suspense>

      <details className="glass-panel rounded-2xl p-5 group">
        <summary className="cursor-pointer list-none flex items-center gap-2 text-lg font-bold text-ink"><Layers className="w-5 h-5 text-sky-300" />How the knowledge graph powers the platform<span className="ml-auto text-[0.875rem] font-semibold text-[#1d4f93] group-open:hidden">Show</span><span className="ml-auto text-[0.875rem] font-semibold text-[#1d4f93] hidden group-open:inline">Hide</span></summary>
        <p className="text-xs text-slate-400 mt-2 mb-4 max-w-3xl">{"Built deterministically from the curated registry (standards, editions, amendments, relations, QCO/CRS/BEE/ALMM orders, parameter ontology, lab scopes, policies, market) and cached by the registry snapshot hash — the same hash is written to the audit ledger with every tender compile."}</p>
        <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">
          {SCHEMA.map(({ icon: Icon, t, d, c }) => (
            <div key={t} className="rounded-xl bg-slate-900/70 border border-slate-800 p-3">
              <div className="flex items-center gap-1.5 text-sm font-bold" style={{ color: c }}><Icon className="w-4 h-4" />{t}</div>
              <div className="text-[0.8125rem] text-slate-400 mt-1 leading-snug">{d}</div>
            </div>
          ))}
          <div className="rounded-xl bg-sky-500/5 border border-sky-500/30 p-3 xl:col-span-1">
            <div className="text-sm font-bold text-sky-200 flex items-center gap-1.5"><Sigma className="w-4 h-4" />Four queries do the work</div>
            <ul className="text-[0.8125rem] text-slate-300 mt-1 space-y-1 list-disc pl-4">
              <li><b>bundle(item, date)</b> → Tender Studio writes the clauses</li>
              <li><b>resolve(designation, date)</b> → edition in force, concurrent editions</li>
              <li><b>impacted_items(node)</b> → Regulatory Radar re-validates tenders</li>
              <li><b>explain_path(a, b)</b> → “why is this clause here?”</li>
            </ul>
          </div>
        </div>
        <div className="grid md:grid-cols-3 gap-3 mt-3 text-[0.8125rem]">
          <div className="rounded-lg border border-slate-800 p-2.5 text-slate-400"><GitBranch className="w-3.5 h-3.5 inline text-amber-300 mr-1" />Buyer: one sentence → items → bundle(as of publication) → clauses with KG paths → compiler verification.</div>
          <div className="rounded-lg border border-slate-800 p-2.5 text-slate-400"><GitBranch className="w-3.5 h-3.5 inline text-emerald-300 mr-1" />Contractor: the tender twin → bid form fields → evidence checked against the same parameters, units and certificates.</div>
          <div className="rounded-lg border border-slate-800 p-2.5 text-slate-400"><GitBranch className="w-3.5 h-3.5 inline text-rose-300 mr-1" />Radar: a new amendment / QCO → reverse traversal → every affected item and tender is re-compiled and notified.</div>
        </div>
      </details>

      <Disclaimer>Standards / regulation data are curated with verification states (source_checked · secondary_source · curated_unverified); labs, market and prices are synthetic demo data. Always confirm on the BIS / e-Gazette / MNRE portals.</Disclaimer>
    </div>
  );
}
