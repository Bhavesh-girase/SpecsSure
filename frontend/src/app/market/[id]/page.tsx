"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, UploadCloud, Sparkles, Send, FileText, BadgeCheck, CheckSquare, ClipboardCheck, Loader2 } from "lucide-react";
import { Button, Card, Disclaimer, ErrorBox, Loading, SectionTitle } from "@/components/ui";
import { bidForm, bidFormAutofill, bidFormScore, bidFormSubmitSealed, evaluation } from "@/lib/api";
import { Advisor, AwardResult, Decl, PriceBid, QueriesBox } from "@/components/market/lifecycle";
import { Notice, StagePill, StageTracker } from "@/components/gov-ui";
import { Lock } from "lucide-react";
import { FileReadout, MatchPanel, StatusPill } from "@/components/market/match";
import { cn } from "@/lib/utils";

const STRENGTH: Record<string, string> = { "3": "lab report", "2": "licence", "1": "datasheet", "0.5": "self-declared" };

function Source({ src }: { src: any }) {
  if (!src) return null;
  return (
    <div className="text-[0.75rem] text-slate-500 mt-0.5 truncate" title={src.snippet}>
      from <b className="text-slate-300">{src.doc_name}</b> p.{src.page} · {STRENGTH[String(src.strength)] || src.doc_type}{src.snippet ? ` · “${src.snippet.slice(0, 70)}”` : ""}
    </div>
  );
}

export default function BidFormPage() {
  const { id } = useParams() as { id: string };
  const [form, setForm] = useState<any>(null);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [scope, setScope] = useState<string[] | null>(null);
  const [score, setScore] = useState<any>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [readout, setReadout] = useState<any[]>([]);
  const [reading, setReading] = useState(false);
  const [bidder, setBidder] = useState("");
  const [product, setProduct] = useState("");
  const [done, setDone] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [ev, setEv] = useState<any>(null);
  const [prices, setPrices] = useState<Record<string, string>>({});
  const [decl, setDecl] = useState<Decl>({ mse: false, mii_class: "I", local_content: "" });
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    try { setBidder(localStorage.getItem("specsure.bidder") || ""); } catch {}
    evaluation(id).then(setEv).catch(() => {});
  }, [id]);
  useEffect(() => {
    bidForm(id).then((f: any) => { setForm(f); setScope(f.groups.filter((g: any) => g.id !== "general").map((g: any) => g.id)); }).catch((e) => setErr(e.message));
  }, [id]);
  useEffect(() => {
    if (!form) return;
    const t = setTimeout(() => bidFormScore(id, answers, scope).then(setScore).catch(() => {}), 250);
    return () => clearTimeout(t);
  }, [answers, scope, form, id]);

  const byField = useMemo(() => Object.fromEntries((score?.results || []).map((r: any) => [r.field_id, r])), [score]);
  const set = (fid: string, patch: any) => setAnswers((a) => ({ ...a, [fid]: { ...(a[fid] || {}), ...patch } }));

  async function readDocs(list: File[]) {
    if (!list.length) return;
    setReading(true); setErr(null);
    try {
      const r: any = await bidFormAutofill(id, list);
      setAnswers((a) => ({ ...r.answers, ...Object.fromEntries(Object.entries(a).filter(([k, v]: any) => !r.answers[k] || v.accepted)) }));
      if (r.scope) setScope(r.scope);
      setReadout(r.files);
    } catch (e: any) { setErr(e.message); } finally { setReading(false); }
  }
  async function submit() {
    try {
      const lines = Object.fromEntries(Object.entries(prices).filter(([, v]) => v !== "" && !isNaN(Number(v))).map(([k, v]) => [k, { unit_price: Number(v) }]));
      const r: any = await bidFormSubmitSealed(id, {
        bidder: bidder || "Demo Bidder", productName: product, answers, scope, files,
        financial: Object.keys(lines).length ? { lines } : undefined,
        declarations: { mse: decl.mse, mii_class: decl.mii_class, local_content: decl.local_content === "" ? null : decl.local_content },
      });
      try { if (bidder) localStorage.setItem("specsure.bidder", bidder); } catch {}
      setDone(r);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e: any) { setErr(e.message); }
  }

  if (err && !form) return <div className="max-w-4xl mx-auto p-8"><ErrorBox error={err} /></div>;
  if (!form) return <Loading label="Deriving the bid form from the tender twin…" />;
  const productGroups = form.groups.filter((g: any) => g.id !== "general");
  const decls = form.fields.filter((f: any) => f.type === "declaration");

  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-5">
      <div className="flex flex-wrap items-start gap-4">
        <Link href="/market" className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-ink"><ArrowLeft className="w-4 h-4" /></Link>
        <div className="flex-1 min-w-[260px]">
          <div className="text-[0.8125rem] uppercase tracking-widest text-emerald-400 font-bold">Smart bid form · {form.tender.reference_no || form.tender.id}</div>
          <h1 className="text-xl font-bold text-ink">{form.tender.title}</h1>
          <div className="text-[0.8125rem] text-slate-400">{form.tender.organisation} · bid due {form.tender.bid_due || "—"} · {form.field_count} fields generated from the canonical tender (content hash {String(form.content_hash).slice(0, 10)})</div>
        </div>
        {ev && <StagePill stage={ev.stage} />}
      </div>
      {ev && <div className="bg-white border border-[#d5deea] rounded-lg p-4 shadow-card"><StageTracker stage={ev.stage} /></div>}
      {ev && ev.stage !== "published" && ev.stage !== "draft" && (
        <Notice tone="warn"><Lock className="w-4 h-4 inline -mt-0.5 mr-1" />Bidding is closed for this tender ({ev.stage_label}). {ev.bids_received} bid(s) were received. The form below is read-only for reference.</Notice>
      )}
      {ev && <AwardResult ev={ev} />}
      {done && (
        <Card glow className="border-emerald-500/40 flex flex-wrap items-center gap-4">
          <BadgeCheck className="w-8 h-8 text-emerald-400" />
          <div className="flex-1 text-sm text-slate-200">Bid submitted and hash-chained in the audit ledger. Match Index <b>{Math.round(done.match_index)}</b> · {done.tier.replaceAll("_", " ")}.
            {done.financial_commitment && <div className="text-[0.875rem] mt-1"><Lock className="w-3.5 h-3.5 inline -mt-0.5" /> Sealed price commitment: <code className="font-mono break-all">{done.financial_commitment}</code> — keep this receipt.</div>}
          </div>
          <Link href={`/bids/${done.bid_id}`}><Button variant="success"><ClipboardCheck className="w-3.5 h-3.5" /> Open evaluator's view (Bid Mirror)</Button></Link>
        </Card>
      )}
      <ErrorBox error={err} />

      <div className="grid xl:grid-cols-[1fr_380px] gap-5">
        <div className="space-y-4">
          {/* documents */}
          <Card>
            <SectionTitle title="1 · Drop your documents — we fill the form" icon={<UploadCloud className="w-5 h-5 text-sky-300" />}
              subtitle="Datasheets, BIS licence / CRS registration, NABL test reports — PDF, DOCX, TXT or scans / phone photos (PNG/JPG). Scans go through PP-OCRv6 OCR with domain-aware repair; every filled value keeps document → page → snippet." />
            <div onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); const l = Array.from(e.dataTransfer.files); setFiles((f) => [...f, ...l]); readDocs(l); }}
              onClick={() => inputRef.current?.click()}
              className="rounded-xl border-2 border-dashed border-slate-700 hover:border-sky-500/60 p-6 text-center cursor-pointer">
              {reading ? <div className="flex items-center justify-center gap-2 text-sky-300 text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Reading documents (OCR on scans)…</div>
                : <div className="text-sm text-slate-400"><UploadCloud className="w-6 h-6 mx-auto mb-1 text-slate-500" />Drop files or click to choose</div>}
              <input ref={inputRef} type="file" multiple className="hidden" onChange={(e) => { const l = Array.from(e.target.files || []); setFiles((f) => [...f, ...l]); readDocs(l); e.target.value = ""; }} />
            </div>
            {files.length > 0 && <div className="flex flex-wrap gap-1.5 mt-2">{files.map((f, i) => <span key={i} className="text-[0.8125rem] px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300"><FileText className="w-3 h-3 inline mr-1" />{f.name}</span>)}</div>}
            <div className="mt-3"><FileReadout files={readout} /></div>
          </Card>

          {/* scope */}
          <Card className="p-4">
            <div className="text-sm font-bold text-ink mb-2">2 · Items you are quoting for <span className="text-[0.8125rem] font-normal text-slate-500">(item-wise bids — requirements of other items are not held against you)</span></div>
            <div className="flex flex-wrap gap-2">
              {productGroups.map((g: any) => {
                const on = !scope || scope.includes(g.id);
                return (
                  <button key={g.id} onClick={() => setScope((s) => { const cur = s || productGroups.map((x: any) => x.id); return on ? cur.filter((x) => x !== g.id) : [...cur, g.id]; })}
                    className={cn("px-3 py-1.5 rounded-lg border text-xs", on ? "bg-emerald-600/20 border-emerald-500/60 text-emerald-200" : "border-slate-700 text-slate-500")}>
                    <CheckSquare className="w-3.5 h-3.5 inline mr-1" />{g.title}
                  </button>
                );
              })}
            </div>
          </Card>

          {/* technical fields */}
          {productGroups.filter((g: any) => !scope || scope.includes(g.id)).map((g: any) => (
            <Card key={g.id} className="p-4">
              <div className="text-sm font-bold text-ink mb-3">3 · {g.title}</div>
              <div className="space-y-2">
                {form.fields.filter((f: any) => f.group === g.id).map((f: any) => (
                  <FieldRow key={f.id} f={f} a={answers[f.id] || {}} r={byField[f.id]} set={set} />
                ))}
              </div>
            </Card>
          ))}
          {form.fields.filter((f: any) => f.group === "general" && f.type !== "declaration").length > 0 && (
            <Card className="p-4">
              <div className="text-sm font-bold text-ink mb-3">4 · Commercial offer</div>
              <div className="space-y-2">
                {form.fields.filter((f: any) => f.group === "general" && f.type !== "declaration").map((f: any) => (
                  <FieldRow key={f.id} f={f} a={answers[f.id] || {}} r={byField[f.id]} set={set} />
                ))}
              </div>
            </Card>
          )}
          {decls.length > 0 && (
            <Card className="p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-bold text-ink">5 · Undertakings ({decls.filter((f: any) => answers[f.id]?.accepted).length}/{decls.length} accepted)</div>
                <Button variant="subtle" onClick={() => setAnswers((a) => ({ ...a, ...Object.fromEntries(decls.map((f: any) => [f.id, { accepted: true }])) }))}>Accept all</Button>
              </div>
              <div className="grid md:grid-cols-2 gap-1.5">
                {decls.map((f: any) => (
                  <label key={f.id} className="flex gap-2 text-[0.8125rem] text-slate-300 rounded-lg bg-slate-900/60 border border-slate-800 p-2 cursor-pointer">
                    <input type="checkbox" checked={!!answers[f.id]?.accepted} onChange={(e) => set(f.id, { accepted: e.target.checked })} />
                    <span><b className="text-slate-200">Cl. {f.clause_key} {f.label}:</b> {f.requirement}</span>
                  </label>
                ))}
              </div>
            </Card>
          )}
          {ev?.lines?.length > 0 && (
            <Card className="p-4">
              <div className="text-sm font-bold text-ink mb-3">6 · Price bid (sealed) and preference declarations</div>
              <PriceBid lines={ev.lines} scope={scope} prices={prices} setPrices={setPrices} decl={decl} setDecl={setDecl} />
            </Card>
          )}
          <Card className="p-4 flex flex-wrap items-end gap-3">
            <label className="text-xs text-slate-400">Bidder name<input value={bidder} onChange={(e) => setBidder(e.target.value)} placeholder="Your firm" className="block mt-1 rounded-lg bg-slate-950 border border-slate-700 px-2 py-1.5 text-ink" /></label>
            <label className="text-xs text-slate-400">Offered product / model<input value={product} onChange={(e) => setProduct(e.target.value)} className="block mt-1 rounded-lg bg-slate-950 border border-slate-700 px-2 py-1.5 text-ink" /></label>
            <Button variant="success" className="py-2" onClick={submit} disabled={!!ev && ev.stage !== "published" && ev.stage !== "draft"}><Send className="w-3.5 h-3.5" /> Submit sealed bid</Button>
            <span className="text-[0.8125rem] text-slate-500">Submission stores document hashes, the answers hash and the sealed price commitment in the tamper-evident ledger.</span>
          </Card>
        </div>
        <div className="self-start space-y-4">
          <MatchPanel score={score} />
          <div className="text-[0.75rem] text-slate-500 flex items-center gap-1"><Sparkles className="w-3 h-3" /> Recomputed live on every change — deterministic comparisons, no AI scoring.</div>
          <Advisor tenderId={id} answers={answers} scope={scope} />
          <QueriesBox tenderId={id} bidder={bidder} open={!ev || ev.stage === "published"} />
        </div>
      </div>
      <Disclaimer />
    </div>
  );
}

function FieldRow({ f, a, r, set }: { f: any; a: any; r: any; set: (id: string, p: any) => void }) {
  return (
    <div className={cn("rounded-lg border p-2.5 grid md:grid-cols-[1fr_260px] gap-2 items-start", r?.status === "FAILS" || r?.status === "CONFLICT" ? "border-rose-500/40 bg-rose-500/5" : "border-slate-800 bg-slate-900/50")}>
      <div>
        <div className="flex items-center gap-2">
          {r && <StatusPill s={r.status} />}
          <span className="text-[0.875rem] font-semibold text-slate-100">{f.label}</span>
          {f.knockout && <span className="text-[0.75rem] text-rose-300 border border-rose-500/30 rounded px-1">mandatory</span>}
          <span className="text-[0.75rem] font-mono text-slate-500 ml-auto">Cl. {f.clause_key}</span>
        </div>
        <div className="text-[0.8125rem] text-slate-400 mt-0.5">Required: <b className="text-slate-200">{f.requirement}</b>{f.evidence_hint ? ` · proof: ${f.evidence_hint}` : ""}</div>
        {r?.detail && <div className={cn("text-[0.8125rem] mt-0.5", r.status === "FAILS" || r.status === "CONFLICT" ? "text-rose-300" : "text-slate-500")}>{r.detail}</div>}
        <Source src={a.source} />
      </div>
      <div>
        {f.type === "number" && (
          <div className="flex items-center gap-1.5">
            <input type="number" step="any" value={a.value ?? ""} onChange={(e) => set(f.id, { value: e.target.value === "" ? null : Number(e.target.value) })}
              className="w-full rounded-lg bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm text-ink font-mono" placeholder="offered value" />
            <span className="text-[0.8125rem] text-slate-400 w-14">{f.unit}</span>
          </div>
        )}
        {f.type === "sizes" && (
          <div className="flex flex-wrap gap-1">
            {f.required_values.map((v: number) => {
              const on = (a.values || []).map(Number).includes(v);
              return <button key={v} onClick={() => set(f.id, { values: on ? (a.values || []).filter((x: number) => Number(x) !== v) : [...(a.values || []), v] })}
                className={cn("px-2 py-1 rounded border text-[0.8125rem]", on ? "bg-emerald-600/30 border-emerald-500 text-emerald-100" : "border-slate-700 text-slate-400")}>{v} {f.unit}</button>;
            })}
          </div>
        )}
        {f.type === "certificate" && (
          <div className="space-y-1">
            <input value={a.number ?? ""} onChange={(e) => set(f.id, { number: e.target.value })} placeholder="CM/L-… or R-…" className="w-full rounded-lg bg-slate-950 border border-slate-700 px-2 py-1.5 text-sm text-ink font-mono" />
            <input type="date" value={a.valid_to ?? ""} onChange={(e) => set(f.id, { valid_to: e.target.value })} className="w-full rounded-lg bg-slate-950 border border-slate-700 px-2 py-1 text-xs text-ink" />
            {a.standard && <div className="text-[0.75rem] text-slate-400">certified to <b className="text-slate-200">{a.standard}</b>{f.resolved && a.standard !== f.resolved ? <span className="text-rose-300"> · tender requires {f.resolved}</span> : null}</div>}
          </div>
        )}
        {f.type === "standard" && (
          <label className="flex items-center gap-2 text-[0.8125rem] text-slate-300"><input type="checkbox" checked={!!a.conforms} onChange={(e) => set(f.id, { conforms: e.target.checked })} /> Offered product conforms</label>
        )}
        {f.type === "test_report" && (
          <div className="grid grid-cols-2 gap-1">
            <input value={a.lab ?? ""} onChange={(e) => set(f.id, { lab: e.target.value })} placeholder="Laboratory" className="col-span-2 rounded bg-slate-950 border border-slate-700 px-2 py-1 text-[0.8125rem] text-ink" />
            <input value={a.nabl_certificate ?? ""} onChange={(e) => set(f.id, { nabl_certificate: e.target.value })} placeholder="NABL cert (TC-…)" className="rounded bg-slate-950 border border-slate-700 px-2 py-1 text-[0.8125rem] text-ink" />
            <input type="date" value={a.report_date ?? ""} onChange={(e) => set(f.id, { report_date: e.target.value })} className="rounded bg-slate-950 border border-slate-700 px-2 py-1 text-[0.8125rem] text-ink" />
          </div>
        )}
      </div>
    </div>
  );
}
