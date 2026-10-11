"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  Wand2, Mic, MicOff, Sparkles, CheckCircle2, AlertTriangle, FileDown, Save, Send, Network, ShieldCheck, Store, CalendarClock,
  Route, HelpCircle, ChevronRight, Languages, BookMarked, Scale, Info, Loader2,
} from "lucide-react";
import { Badge, Bar, Button, Card, ErrorBox, Gauge, SectionTitle, Disclaimer } from "@/components/ui";
import { studioCatalogue, studioDocx, studioGenerate, studioParse, studioSave } from "@/lib/api";
import { cn } from "@/lib/utils";
import { BASIS, PathChips } from "@/components/studio/common";
import { PageIntro } from "@/components/gov-ui";

function useSpeech(onText: (t: string) => void) {
  const recRef = useRef<any>(null);
  const [on, setOn] = useState(false);
  const [supported, setSupported] = useState(false);   // decided after mount → no hydration mismatch
  useEffect(() => { setSupported(!!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)); }, []);
  const start = (lang: string) => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;
    const r = new SR();
    r.lang = lang;
    r.interimResults = false;
    r.continuous = false;
    r.onresult = (e: any) => onText(Array.from(e.results).map((x: any) => x[0].transcript).join(" "));
    r.onend = () => setOn(false);
    r.onerror = () => setOn(false);
    recRef.current = r;
    setOn(true);
    r.start();
  };
  const stop = () => { recRef.current?.stop(); setOn(false); };
  return { on, start, stop, supported: !!supported };
}

function fmtINR(v: number) {
  return "₹" + Math.round(v).toLocaleString("en-IN");
}

export default function StudioPage() {
  const [cat, setCat] = useState<any>(null);
  const [text, setText] = useState("need a tender of 500 light bulbs and 100 meteres");
  const [org, setOrg] = useState("District Health Society, Demo City");
  const [asOf, setAsOf] = useState(new Date().toISOString().slice(0, 10));
  const [intent, setIntent] = useState<any>(null);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [overrides, setOverrides] = useState<Record<string, Record<string, any>>>({});
  const [gen, setGen] = useState<any>(null);
  const [sel, setSel] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saved, setSaved] = useState<any>(null);
  const [voiceLang, setVoiceLang] = useState("en-IN");
  const speech = useSpeech((t) => setText((x) => (x ? x + " " : "") + t));

  useEffect(() => { studioCatalogue().then(setCat).catch(() => {}); }, []);
  // deep link from the home page: /studio?q=<one sentence>
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) {
      setText(q);
      studioParse(q).then((r: any) => {
        setIntent(r);
        const a: Record<string, any> = {};
        r.questions.forEach((x: any) => { if (x.default !== undefined) a[x.id] = x.default; });
        setAnswers(a);
      }).catch((e) => setErr(e.message));
    }
  }, []);

  async function doParse() {
    setErr(null); setGen(null); setSaved(null); setSel(null);
    try {
      const r: any = await studioParse(text);
      setIntent(r);
      const a: Record<string, any> = {};
      r.questions.forEach((q: any) => { if (q.default !== undefined) a[q.id] = q.default; });
      setAnswers(a);
      setOverrides({});
    } catch (e: any) { setErr(e.message); }
  }
  async function doGenerate() {
    setErr(null); setSaved(null);
    try {
      const g: any = await studioGenerate({ intent, answers, as_of: asOf, meta: { organisation: org }, overrides });
      setGen(g);
      setSel(null);
      setTimeout(() => document.getElementById("draft")?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch (e: any) { setErr(e.message); }
  }
  async function doSave(publish: boolean) {
    try {
      const r: any = await studioSave({ intent, answers, as_of: asOf, meta: { organisation: org }, overrides, publish });
      setSaved(r);
    } catch (e: any) { setErr(e.message); }
  }
  async function download() {
    const blob = await studioDocx(gen);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${gen.meta.reference_no.replaceAll("/", "_")}.docx`; a.click();
    URL.revokeObjectURL(url);
  }

  const missing = (intent?.questions || []).filter((q: any) => q.required && (answers[q.id] === undefined || answers[q.id] === ""));

  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <PageIntro icon={Wand2} kicker="Tender Studio · for procurement officers"
        title="Create a tender from one sentence"
        sub={<>Write what your office needs in English, Hindi or Hinglish — for example <i>“500 LED bulbs and 100 metres of wire”</i>. SpecSure picks the correct Indian Standards, mandatory certifications, tests and rules, writes the tender, and checks it before you see it. Every clause shows <b>why</b> it is there.</>}
        right={<Link href="/kg" className="text-[0.875rem] font-semibold text-[#1d4f93] hover:underline flex items-center gap-1"><Network className="w-4 h-4" /> How the knowledge graph works</Link>}
        details={<>One sentence → the Procurement Knowledge Graph picks the Indian Standards in force on the publication date, the QCO / CRS / BEE / ALMM orders, tests, labs and GFR clauses → the Tender Compiler (Z3 SMT solver + 38 lint rules + market model) verifies the draft and repairs it until it passes. Values marked “practice default” are recommendations, not statutory limits.</>} />
      <StudioSteps step={saved ? 4 : gen ? 3 : intent ? 2 : 1} />

      {/* ---------------- 1. request ---------------- */}
      <Card glow>
        <div className="grid lg:grid-cols-[1fr_280px] gap-4">
          <div className="space-y-3">
            <div className="relative">
              <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3}
                className="w-full rounded-xl bg-slate-950/80 border border-slate-700 focus:border-sky-500 outline-none p-4 pr-14 text-base text-ink placeholder:text-slate-400"
                placeholder="e.g. need a tender of 500 light bulbs and 100 metres of wire for the district hospital" />
              {speech.supported && (
                <button onClick={() => (speech.on ? speech.stop() : speech.start(voiceLang))} title="Speak your requirement"
                  className={cn("absolute right-3 top-3 p-2.5 rounded-full border", speech.on ? "bg-rose-600 border-rose-400 animate-pulse" : "bg-slate-800 border-slate-600 hover:bg-slate-700")}>
                  {speech.on ? <MicOff className="w-4 h-4 text-white" /> : <Mic className="w-4 h-4 text-sky-300" />}
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {(cat?.examples || []).map((ex: any) => (
                <button key={ex.text} onClick={() => setText(ex.text)} className="text-[0.8125rem] px-2.5 py-1 rounded-full bg-slate-900 border border-slate-700 text-slate-300 hover:border-sky-500/60 max-w-[420px] truncate">
                  <span className="text-sky-400 font-bold mr-1">{ex.lang}</span>{ex.text}
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-2 text-xs">
            <label className="block text-slate-400">Organisation
              <input value={org} onChange={(e) => setOrg(e.target.value)} className="mt-1 w-full rounded-lg bg-slate-950 border border-slate-700 px-2 py-1.5 text-ink" />
            </label>
            <label className="block text-slate-400 flex items-center gap-1"><CalendarClock className="w-3.5 h-3.5" /> Publication date (time machine)
            </label>
            <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} className="w-full rounded-lg bg-slate-950 border border-slate-700 px-2 py-1.5 text-ink" />
            {speech.supported && (
              <label className="block text-slate-400 flex items-center gap-1"><Languages className="w-3.5 h-3.5" /> Voice language
                <select value={voiceLang} onChange={(e) => setVoiceLang(e.target.value)} className="ml-auto rounded bg-slate-950 border border-slate-700 px-1.5 py-1 text-ink">
                  <option value="en-IN">English (India)</option><option value="hi-IN">हिन्दी</option>
                </select>
              </label>
            )}
            <Button className="w-full py-2.5 text-sm" onClick={doParse}><Sparkles className="w-4 h-4" /> Understand request</Button>
          </div>
        </div>
      </Card>
      <ErrorBox error={err} />

      {/* ---------------- 2. understanding + questions ---------------- */}
      {intent && (
        <div className="grid lg:grid-cols-[1.2fr_1fr] gap-5">
          <Card>
            <SectionTitle title="What I understood" icon={<CheckCircle2 className="w-5 h-5 text-emerald-400" />}
              subtitle={`Parser: ${intent.parser} · language: ${intent.language}. Items are matched against the knowledge graph's item layer; quantities are converted to the unit of account.`} />
            <div className="space-y-3">
              {intent.line_items.map((li: any) => {
                const itemId = answers[`L${li.index}.item`] || li.item_id;
                const item = cat?.items.find((x: any) => x.id === itemId);
                return (
                  <div key={li.index} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[0.75rem] font-mono text-slate-500">L{li.index}</span>
                      <span className="text-sm font-bold text-ink">{item?.label || "Unknown item"}</span>
                      <Badge className={li.match === "alias" ? "border-emerald-500/40 text-emerald-300" : li.match === "fuzzy" ? "border-sky-500/40 text-sky-300" : "border-amber-500/40 text-amber-300"}>
                        {li.match === "inferred" ? "inferred · confirm" : li.match} {Math.round((li.confidence || 0) * 100)}%
                      </Badge>
                      <span className="ml-auto font-mono text-sm text-sky-300">{li.quantity ?? "?"} {li.unit}</span>
                    </div>
                    <div className="text-[0.8125rem] text-slate-500 mt-1">“{li.text}”</div>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {Object.entries(li.slots || {}).map(([k, v]: any) => (
                        <span key={k} className={cn("text-[0.75rem] px-2 py-0.5 rounded-full border", li.slot_sources?.[k] === "stated" ? "border-sky-500/50 text-sky-200" : "border-slate-700 text-slate-400")}>
                          {k.replaceAll("_", " ")}: <b>{Array.isArray(v) ? v.join(", ") : String(v)}</b>{li.slot_sources?.[k] === "stated" ? " ✓" : ""}
                        </span>
                      ))}
                    </div>
                    {li.notes?.map((n: string, i: number) => <div key={i} className="text-[0.8125rem] text-amber-200/80 mt-1.5 flex gap-1"><Info className="w-3 h-3 mt-0.5 shrink-0" />{n}</div>)}
                  </div>
                );
              })}
              {intent.globals && Object.keys(intent.globals).length > 0 && (
                <div className="text-[0.8125rem] text-slate-400">Also understood: {Object.entries(intent.globals).map(([k, v]: any) => `${k.replaceAll("_", " ")} = ${k === "budget_inr" ? fmtINR(v) : v}`).join(" · ")}</div>
              )}
            </div>
          </Card>
          <Card>
            <SectionTitle title={intent.questions.length ? `Only ${intent.questions.length} question${intent.questions.length > 1 ? "s" : ""} that matter` : "Nothing to ask"}
              icon={<HelpCircle className="w-5 h-5 text-amber-300" />}
              subtitle="Questions come from the knowledge graph: mandatory buyer decisions still empty for each item, and items that could not be named. Everything else uses a traceable default." />
            <div className="space-y-3">
              {intent.questions.map((q: any) => (
                <div key={q.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <div className="text-sm text-ink font-semibold">{q.question}</div>
                  {q.question_hi && intent.language !== "en" && <div className="text-xs text-slate-400">{q.question_hi}</div>}
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {(q.options || []).map((o: any) => {
                      const val = typeof o === "object" ? o.value : o;
                      const lab = typeof o === "object" ? o.label : `${o}${q.unit ? " " + q.unit : ""}`;
                      const on = JSON.stringify(answers[q.id]) === JSON.stringify(val);
                      return (
                        <button key={String(val)} onClick={() => setAnswers((a) => ({ ...a, [q.id]: val }))} title={typeof o === "object" ? o.why : undefined}
                          className={cn("px-2.5 py-1 rounded-lg border text-xs", on ? "bg-sky-600 border-sky-400 text-white" : "bg-slate-900 border-slate-700 text-slate-300 hover:border-sky-500/50")}>
                          {lab}
                        </button>
                      );
                    })}
                    {q.type === "number" && !q.options && (
                      <input type="number" className="w-32 rounded bg-slate-900 border border-slate-700 px-2 py-1 text-xs text-ink" value={answers[q.id] ?? ""}
                        onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value ? Number(e.target.value) : "" }))} />
                    )}
                  </div>
                  {q.why && <div className="text-[0.8125rem] text-slate-500 mt-1.5">Why: {q.why}</div>}
                </div>
              ))}
              <AssumedValues intent={intent} cat={cat} answers={answers} overrides={overrides} setOverrides={setOverrides} />
              <Button className="w-full py-2.5 text-sm" disabled={missing.length > 0} onClick={doGenerate}>
                <Wand2 className="w-4 h-4" /> Generate & verify tender
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* ---------------- 3. verified draft ---------------- */}
      {gen && <Draft gen={gen} sel={sel} setSel={setSel} onDownload={download} onSave={doSave} saved={saved} />}
      <Disclaimer>
        Tender Studio produces a draft for the competent authority. Standards/QCO coverage is curated with a per-record verification state; market and price data are synthetic in this demo.
        Values marked “practice default” are recommendations, not statutory limits.
      </Disclaimer>
    </div>
  );
}

function AssumedValues({ intent, cat, answers, overrides, setOverrides }: any) {
  const [open, setOpen] = useState(false);
  if (!cat) return null;
  return (
    <div className="rounded-xl border border-slate-800 p-3">
      <button onClick={() => setOpen(!open)} className="text-xs text-slate-300 flex items-center gap-1 w-full">
        <ChevronRight className={cn("w-3.5 h-3.5 transition-transform", open && "rotate-90")} /> Review assumed values (practice defaults) — optional
      </button>
      {open && intent.line_items.map((li: any) => {
        const itemId = answers[`L${li.index}.item`] || li.item_id;
        const item = cat.items.find((x: any) => x.id === itemId);
        if (!item) return null;
        return (
          <div key={li.index} className="mt-2">
            <div className="text-[0.8125rem] font-bold text-slate-400">L{li.index} · {item.label}</div>
            <div className="grid sm:grid-cols-2 gap-1.5 mt-1">
              {item.slots.filter((s: any) => !s.ask && s.options).map((s: any) => (
                <label key={s.id} className="text-[0.8125rem] text-slate-400 flex items-center justify-between gap-2 bg-slate-900/60 rounded px-2 py-1">
                  <span>{s.label} <span className="text-slate-400">({s.basis})</span></span>
                  <select className="bg-slate-950 border border-slate-700 rounded px-1 py-0.5 text-ink"
                    value={String(overrides[li.index]?.[s.id] ?? li.slots?.[s.id] ?? s.default)}
                    onChange={(e) => {
                      const v = isNaN(Number(e.target.value)) ? e.target.value : Number(e.target.value);
                      setOverrides((o: any) => ({ ...o, [li.index]: { ...(o[li.index] || {}), [s.id]: v } }));
                    }}>
                    {s.options.map((o: any) => <option key={String(o)} value={String(o)}>{String(o)} {s.unit || ""}</option>)}
                  </select>
                </label>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Draft({ gen, sel, setSel, onDownload, onSave, saved }: any) {
  const v = gen.verification;
  const total = Object.values(gen.basis_counts as Record<string, number>).reduce((a, b) => a + b, 0);
  return (
    <div id="draft" className="grid xl:grid-cols-[1fr_380px] gap-5">
      <div className="space-y-4">
        <Card>
          <div className="flex flex-wrap items-start gap-3">
            <div className="flex-1 min-w-[240px]">
              <div className="text-[0.8125rem] uppercase tracking-widest text-sky-400 font-bold">Verified draft · {gen.meta.reference_no}</div>
              <div className="text-lg font-bold text-ink">{gen.meta.title}</div>
              <div className="text-[0.8125rem] text-slate-400">{gen.meta.organisation} · published {gen.meta.publication} · bid due {gen.meta.bid_due} · estimated {fmtINR(gen.meta.estimated_value)} · EMD {fmtINR(gen.meta.emd)}</div>
              <div className="text-[0.75rem] text-slate-500">Estimate: {gen.meta.estimate_source}</div>
            </div>
            <Button variant="ghost" onClick={onDownload}><FileDown className="w-3.5 h-3.5" /> Word (.docx)</Button>
            <Button variant="subtle" onClick={() => onSave(false)}><Save className="w-3.5 h-3.5" /> Save draft</Button>
            <Button variant="success" disabled={v.final.gate === "BLOCKED"} onClick={() => onSave(true)} title="Publishing is refused while critical findings are open">
              <Send className="w-3.5 h-3.5" /> Save & publish
            </Button>
          </div>
          {saved && (
            <div className="mt-3 rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-2.5 text-xs text-emerald-200 flex flex-wrap gap-3 items-center">
              <CheckCircle2 className="w-4 h-4" /> Saved as tender <b>{saved.tender_id}</b> ({saved.status}, readiness {Math.round(saved.readiness)} · {saved.gate}).
              <Link className="underline" href={`/tenders/${saved.tender_id}`}>Open in cockpit →</Link>
              {saved.status === "published" && <Link className="underline" href={`/market/${saved.tender_id}`}>View as a contractor →</Link>}
            </div>
          )}
          <div className="flex flex-wrap gap-2 mt-4">
            {Object.entries(BASIS).map(([k, b]) => gen.basis_counts[k] ? (
              <span key={k} title={b.hint} className="text-[0.75rem] px-2 py-0.5 rounded-full border border-slate-700 text-slate-300 flex items-center gap-1">
                <span className={cn("w-2 h-2 rounded-full", b.dot)} /> {b.label} <b>{gen.basis_counts[k]}</b>
              </span>
            ) : null)}
            <span className="text-[0.75rem] text-slate-500 self-center">{total} clauses · click any clause to see why it exists</span>
          </div>
        </Card>
        <div className="space-y-4">
          {gen.sections.map((s: any) => (
            <Card key={s.no} className="p-4">
              <div className="text-sm font-bold text-ink mb-2">{s.no}. {s.title}</div>
              <div className="space-y-1.5">
                {s.clauses.map((c: any) => {
                  const b = BASIS[c.basis] || BASIS.practice;
                  return (
                    <button key={c.key} onClick={() => setSel(c)}
                      className={cn("w-full text-left rounded-lg border-l-4 border px-3 py-2 text-[0.9375rem] leading-relaxed transition-colors hover:bg-slate-800/60",
                        b.cls, sel?.key === c.key && "ring-1 ring-sky-400")}>
                      <span className="font-mono text-[0.8125rem] text-slate-500 mr-1.5">{c.key}</span>
                      <b className="text-slate-100">{c.heading}:</b> <span className="text-slate-300">{c.text}</span>
                    </button>
                  );
                })}
              </div>
            </Card>
          ))}
        </div>
      </div>
      <div className="space-y-4 xl:sticky xl:top-20 self-start max-h-[calc(100vh-6rem)] overflow-y-auto pr-1">
        {sel ? <WhyPanel c={sel} onClose={() => setSel(null)} /> : null}
        <Card>
          <div className="flex items-center gap-4">
            <Gauge score={v.final.readiness} size={110} />
            <div className="flex-1">
              <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">Self-verification</div>
              <div className={cn("text-lg font-extrabold", v.final.gate === "READY" ? "text-emerald-300" : v.final.gate === "BLOCKED" ? "text-rose-300" : "text-amber-300")}>{v.final.gate}</div>
              <div className="text-[0.8125rem] text-slate-400">{v.final.counts.critical} critical · {v.final.counts.major} major · {v.final.counts.minor} minor · {v.final.counts.info} info · proofs: {v.proofs.conflicts} contradiction(s) ({v.proofs.engine})</div>
            </div>
          </div>
          <div className="mt-3 space-y-1.5">
            {v.passes.map((p: any) => (
              <div key={p.pass} className="text-[0.8125rem] rounded-lg bg-slate-900/70 border border-slate-800 px-2.5 py-1.5">
                <div className="flex justify-between"><b className="text-slate-200">Compiler pass {p.pass}</b><span className="font-mono text-slate-400">{Math.round(p.readiness)} · {p.gate}</span></div>
                {p.auto_repaired.map((r: any, i: number) => <div key={i} className="text-fuchsia-300">auto-repaired {r.rule_id} ({r.clause_key}): {r.message.slice(0, 90)}…</div>)}
                {!p.auto_repaired.length && <div className="text-emerald-300/80">no further repairs needed</div>}
              </div>
            ))}
            {v.open_findings.filter((f: any) => f.severity !== "info").map((f: any, i: number) => (
              <div key={i} className="text-[0.8125rem] text-amber-200 flex gap-1"><AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />{f.rule_id} ({f.clause_key}): {f.message}</div>
            ))}
          </div>
        </Card>
        <Card>
          <div className="text-sm font-bold text-ink flex items-center gap-1.5 mb-2"><Store className="w-4 h-4 text-amber-300" /> Competition meter</div>
          {gen.lines.map((l: any) => {
            const c = l.competition || {};
            return (
              <div key={l.index} className="mb-3">
                <div className="flex justify-between text-[0.8125rem]"><span className="text-slate-300">{l.item_label.split("(")[0]}</span>
                  <span className="font-mono text-slate-400">{c.available ? `${c.eligible_manufacturers}/${c.licensed_manufacturers} makers` : "no catalogue"}</span></div>
                {c.available && <Bar value={c.eligible_manufacturers} max={c.licensed_manufacturers} tone={c.ok ? "bg-emerald-500" : "bg-rose-500"} />}
                {c.warning && <div className="text-[0.8125rem] text-rose-300 mt-1">{c.warning}</div>}
                {(c.alternatives || []).map((a: any, i: number) => <div key={i} className="text-[0.8125rem] text-sky-300">→ {a.label} {String(a.to)} would allow {a.manufacturers} makers</div>)}
                {(c.binding || []).slice(0, 2).map((b: any, i: number) => <div key={i} className="text-[0.75rem] text-slate-500">binding: {b.slot.replaceAll("_", " ")} excludes {b.excluded}</div>)}
              </div>
            );
          })}
          {gen.competition_guard.map((g: any, i: number) => (
            <div key={i} className="text-[0.8125rem] text-amber-200 rounded bg-amber-500/10 border border-amber-500/30 p-2 mt-1"><Scale className="w-3 h-3 inline mr-1" />Competition guard: {g.reason}</div>
          ))}
          <div className="text-[0.75rem] text-slate-500 mt-1">Synthetic catalogue in the demo; plug in GeM / BIS licence data in production.</div>
        </Card>
        <Card>
          <div className="text-sm font-bold text-ink flex items-center gap-1.5 mb-2"><BookMarked className="w-4 h-4 text-emerald-300" /> Standards & regulations (as of {gen.as_of})</div>
          <div className="space-y-1">
            {gen.standards_register.map((s: any) => (
              <div key={s.cite_as} className="text-[0.8125rem]">
                <span className="font-mono text-emerald-300">{s.cite_as}</span> <span className="text-slate-500">· {s.role}</span>
                {s.concurrent?.map((c: any) => <div key={c.is_number} className="text-amber-300/90 pl-3">↳ {c.is_number} valid only until {c.valid_to} (concurrent)</div>)}
              </div>
            ))}
            <div className="border-t border-slate-800 my-2" />
            {gen.regulations_register.map((g: any) => (
              <div key={g.key} className="text-[0.8125rem] flex gap-1.5">
                <ShieldCheck className={cn("w-3.5 h-3.5 shrink-0 mt-0.5", g.in_force ? "text-rose-300" : "text-sky-300")} />
                <span className="text-slate-300">{g.title} <span className="text-slate-500">· {g.in_force ? "in force" : `from ${g.effective_from}`} · {g.verification_state}</span></span>
              </div>
            ))}
          </div>
        </Card>
        {gen.watchlist.length > 0 && (
          <Card>
            <div className="text-sm font-bold text-ink flex items-center gap-1.5 mb-2"><CalendarClock className="w-4 h-4 text-sky-300" /> Regulatory watchlist</div>
            {gen.watchlist.map((w: any, i: number) => <div key={i} className="text-[0.8125rem] text-slate-300 mb-1"><span className="font-mono text-sky-300">{w.date}</span> · {w.message}</div>)}
          </Card>
        )}
        <Card>
          <div className="text-sm font-bold text-ink flex items-center gap-1.5 mb-1"><Route className="w-4 h-4 text-violet-300" /> Procurement route (GFR 2017)</div>
          <div className="text-[0.875rem] text-slate-200">{gen.route_advice.route} <span className="text-slate-500">({gen.route_advice.rule})</span></div>
          <div className="text-[0.8125rem] text-slate-400 mt-1">{gen.route_advice.note}</div>
          <div className="text-[0.75rem] text-slate-400 mt-1">{gen.route_advice.caveat}</div>
        </Card>
      </div>
    </div>
  );
}

function WhyPanel({ c, onClose }: { c: any; onClose: () => void }) {
  const b = BASIS[c.basis] || BASIS.practice;
  return (
    <Card glow>
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-[0.75rem] uppercase tracking-widest text-slate-500 font-bold">Why clause {c.key} exists</div>
          <div className="text-sm font-bold text-ink">{c.heading}</div>
        </div>
        <button onClick={onClose} className="text-slate-500 hover:text-ink text-xs">✕</button>
      </div>
      <div className="mt-2 flex items-center gap-1.5 text-[0.8125rem]"><span className={cn("w-2.5 h-2.5 rounded-full", b.dot)} /><b className="text-slate-200">{b.label}</b><span className="text-slate-400">— {b.hint}</span></div>
      <div className="mt-3 space-y-2">
        {(c.provenance || []).length === 0 && <div className="text-[0.8125rem] text-slate-500">Standard drafting practice (no external source).</div>}
        {(c.provenance || []).map((p: any, i: number) => (
          <div key={i} className="rounded-lg bg-slate-900/70 border border-slate-800 p-2 text-[0.8125rem]">
            {p.kind === "standard" && <>
              <div className="text-emerald-300 font-semibold">{p.cite_as} <span className="text-slate-500 font-normal">({p.relation ? p.relation.toLowerCase().replaceAll("_", " ") : "edition in force on the tender date"})</span></div>
              {p.concurrent?.length > 0 && <div className="text-amber-300">Older edition still valid: {p.concurrent.map((x: any) => `${x.is_number} until ${x.valid_to}`).join(", ")}</div>}
              {p.path && <PathChips path={p.path} />}
            </>}
            {p.kind === "regulation" && <>
              <div className="text-rose-300 font-semibold">{p.title}</div>
              <div className="text-slate-400">{p.scheme} · verification: <b>{p.verification_state}</b> {p.source_url && <a className="text-sky-300 underline ml-1" href={p.source_url} target="_blank" rel="noreferrer">source</a>}</div>
              {p.path && <PathChips path={p.path} />}
            </>}
            {p.kind === "policy" && <>
              <div className="text-violet-300 font-semibold">{p.key}</div>
              {p.detail && <div className="text-slate-400">{p.detail}</div>}
              {p.source_url && <a className="text-sky-300 underline" href={p.source_url} target="_blank" rel="noreferrer">source ({p.verification_state})</a>}
            </>}
            {p.kind === "slot" && (
              <div className="text-slate-300"><b className="text-sky-300">{p.label}</b> = <b>{p.value}</b> · <span className="text-slate-400">{p.source === "stated" ? "you said it" : p.source === "answered" ? "you chose it" : `default (${p.basis})`}</span>
                {p.guarded && <span className="text-amber-300"> · relaxed by the competition guard</span>}</div>
            )}
            {["intent", "estimate", "repair"].includes(p.kind) && <div className="text-slate-400">{p.kind}: {p.detail}</div>}
          </div>
        ))}
        {c.repairs?.length > 0 && <div className="text-[0.8125rem] text-fuchsia-300">Self-repair appended: {c.repairs.join(" ")}</div>}
      </div>
    </Card>
  );
}

/** Where the officer is in the Studio flow — so the long page always says what to do next. */
function StudioSteps({ step }: { step: number }) {
  const steps = [
    ["Describe what you need", "Type or speak one sentence, then press “Understand request”."],
    ["Confirm the details", "Answer the few questions SpecSure could not work out, then generate."],
    ["Review the draft", "Read each clause and why it exists; change values if needed."],
    ["Save or publish", "Save as a draft for vetting, publish for bidding, or download .docx."],
  ];
  return (
    <ol className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3" aria-label="Steps">
      {steps.map(([t, d], i) => {
        const n = i + 1, done = n < step, cur = n === step;
        return (
          <li key={t} aria-current={cur ? "step" : undefined}
            className={cn("rounded-lg border p-3.5 flex gap-3 bg-white", cur ? "border-[#1d4f93] ring-2 ring-[#1d4f93]/15" : "border-[#d5deea]", !cur && !done && "opacity-75")}>
            <span className={cn("w-7 h-7 rounded-full flex items-center justify-center text-[0.875rem] font-bold shrink-0",
              done ? "bg-[#138808] text-white" : cur ? "bg-[#ff9933] text-[#0f2748]" : "bg-[#eef2f7] text-[#475569]")}>{done ? "✓" : n}</span>
            <span>
              <span className={cn("block font-bold leading-snug", cur ? "text-[#0f2748]" : "text-[#334155]")}>{t}</span>
              <span className="block text-[0.875rem] text-[#475569] leading-snug mt-0.5">{d}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
