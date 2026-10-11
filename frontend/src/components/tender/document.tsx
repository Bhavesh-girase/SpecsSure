"use client";

import { useMemo, useState } from "react";
import { History, FileText, Upload } from "lucide-react";
import { Badge, Button, Card, SevBadge } from "@/components/ui";
import { addTenderDocument, demoCorrigendum } from "@/lib/api";
import { cn, SEV_DOT } from "@/lib/utils";

function highlight(text: string, quotes: { q: string; sev: string }[]) {
  if (!text) return [<span key="e" className="text-slate-500 italic">(heading only)</span>];
  const marks: { s: number; e: number; sev: string }[] = [];
  for (const { q, sev } of quotes) {
    if (!q || q.length < 3) continue;
    const i = text.toLowerCase().indexOf(q.toLowerCase().slice(0, 160));
    if (i >= 0) marks.push({ s: i, e: i + Math.min(q.length, 160), sev });
  }
  marks.sort((a, b) => a.s - b.s);
  const out: any[] = [];
  let pos = 0;
  marks.forEach((m, k) => {
    if (m.s < pos) return;
    out.push(<span key={`t${k}`}>{text.slice(pos, m.s)}</span>);
    const cls = m.sev === "critical" ? "bg-rose-500/30 decoration-rose-400" : m.sev === "major" ? "bg-amber-500/25 decoration-amber-300" : "bg-sky-500/20 decoration-sky-300";
    out.push(<mark key={`m${k}`} className={cn("text-inherit rounded px-0.5 underline decoration-wavy underline-offset-4", cls)}>{text.slice(m.s, m.e)}</mark>);
    pos = m.e;
  });
  out.push(<span key="end">{text.slice(pos)}</span>);
  return out;
}

export function DocumentView({ twin }: { twin: any }) {
  const [hist, setHist] = useState<string | null>(null);
  const byClause = useMemo(() => {
    const m: Record<string, any[]> = {};
    twin.findings.forEach((f: any) => { if (f.clause_key) (m[f.clause_key] ||= []).push(f); });
    return m;
  }, [twin]);
  const blame = twin.corrigenda?.blame || {};
  const history = twin.corrigenda?.history || {};
  return (
    <div className="grid lg:grid-cols-[1fr_380px] gap-6">
      <Card className="p-0 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-800 flex items-center gap-2 text-xs text-slate-400">
          <FileText className="w-4 h-4 text-sky-400" /> Canonical tender (all corrigenda merged) — clause-anchored, page-preserving
          {twin.corrigenda?.deleted?.length > 0 && <span className="ml-auto">Deleted: {twin.corrigenda.deleted.join(", ")}</span>}
        </div>
        <div className="divide-y divide-slate-800/70 max-h-[70vh] overflow-auto">
          {twin.clauses.map((c: any) => {
            const fs = byClause[c.key] || [];
            const b = blame[c.key];
            const worst = fs.map((f: any) => f.severity).sort((a: string, z: string) => ["critical", "major", "minor", "info"].indexOf(a) - ["critical", "major", "minor", "info"].indexOf(z))[0];
            return (
              <div key={c.key} className={cn("px-5 py-3 flex gap-3", !c.parent && !c.text ? "bg-slate-900/60" : "")}>
                <div className="w-14 shrink-0 font-mono text-xs text-sky-300 pt-0.5">{c.key}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold text-ink">{c.heading}</span>
                    <span className="text-[0.75rem] text-slate-500">p.{c.page_start} · {c.section_type}</span>
                    {b && b.change !== "original" && (
                      <button onClick={() => setHist(c.key)}><Badge className="border-violet-500/40 text-violet-300"><History className="w-3 h-3" />{b.change} · {b.doc}</Badge></button>
                    )}
                    {worst && <span className={cn("w-2 h-2 rounded-full", SEV_DOT[worst])} title={`${fs.length} finding(s)`} />}
                    {fs.length > 0 && <span className="text-[0.75rem] text-slate-500">{fs.length} finding(s)</span>}
                  </div>
                  <div className="text-[0.9375rem] text-slate-300 leading-relaxed mt-1 whitespace-pre-wrap">
                    {highlight(c.text, fs.map((f: any) => ({ q: f.quote || "", sev: f.severity })))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </Card>
      <div className="space-y-4">
        <Card>
          <div className="text-sm font-bold text-ink mb-2 flex items-center gap-2"><History className="w-4 h-4 text-violet-300" /> Clause history</div>
          {!hist ? <p className="text-xs text-slate-400">Click a “modified/added” badge to see every version of that clause with a word-level diff.</p> : (
            <div className="space-y-3">
              <div className="text-xs text-slate-300">Clause <b className="font-mono">{hist}</b> — {history[hist]?.length} version(s)</div>
              {(history[hist] || []).map((v: any) => (
                <div key={v.version} className="rounded-lg border border-slate-800 bg-slate-950/60 p-2 text-[0.8125rem]">
                  <div className="text-slate-400 mb-1">v{v.version} · {v.change} · {v.doc} {v.date ? `· ${v.date}` : ""}</div>
                  {v.diff ? (
                    <div className="leading-relaxed">{v.diff.map(([op, t]: any, i: number) => (
                      <span key={i} className={op === "+" ? "bg-emerald-500/20 text-emerald-200" : op === "-" ? "bg-rose-500/20 text-rose-200 line-through" : "text-slate-300"}>{t} </span>))}</div>
                  ) : <div className="text-slate-300">{v.text}</div>}
                </div>
              ))}
            </div>
          )}
        </Card>
        <Card>
          <div className="text-sm font-bold text-ink mb-2">Documents</div>
          <div className="space-y-1.5">
            {(twin.documents || []).map((d: any) => (
              <div key={d.id} className="text-[0.8125rem] flex items-center gap-2">
                <Badge className="border-slate-700 text-slate-300">{d.doc_type}</Badge>
                <span className="text-slate-200 truncate">{d.filename}</span>
                <span className="ml-auto font-mono text-slate-500" title={d.sha256}>{d.sha256.slice(0, 8)}</span>
              </div>
            ))}
          </div>
          <p className="text-[0.75rem] text-slate-500 mt-2">Parser: {(twin.documents?.[0]?.meta?.parser) || "—"} · OCR pages: {(twin.documents || []).flatMap((d: any) => d.meta?.ocr_pages || []).length}</p>
        </Card>
      </div>
    </div>
  );
}

export function Corrigenda({ twin, tenderId, onChanged, isDemo }: { twin: any; tenderId: string; onChanged: () => void; isDemo: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [dtype, setDtype] = useState("corrigendum");
  const log = twin.corrigenda?.changelog || [];
  const applied = (twin.documents || []).filter((d: any) => d.doc_type === "corrigendum").map((d: any) => d.filename);
  return (
    <div className="grid lg:grid-cols-[1fr_360px] gap-6">
      <Card>
        <div className="text-sm font-bold text-ink mb-3">Change log (chronological merge)</div>
        {log.length === 0 ? <p className="text-xs text-slate-400">No corrigenda yet. Upload one — SpecSure parses “Clause X shall be read as…”, “Clause Y is deleted”, “New clause Z is added…”.</p> : (
          <ol className="relative border-l border-slate-700 ml-2 space-y-4">
            {log.map((e: any, i: number) => (
              <li key={i} className="ml-4">
                <span className={cn("absolute -left-1.5 w-3 h-3 rounded-full", e.op === "delete" ? "bg-rose-500" : e.op === "add" ? "bg-emerald-500" : "bg-violet-500")} />
                <div className="text-[0.8125rem] text-slate-400">{e.date || "undated"} · {e.doc} · <b className="uppercase text-slate-200">{e.op}</b> Clause <span className="font-mono text-sky-300">{e.clause_key}</span></div>
                {e.warning && <div className="text-[0.8125rem] text-amber-300">{e.warning}</div>}
                {e.diff ? (
                  <div className="text-xs leading-relaxed mt-1">{e.diff.map(([op, t]: any, j: number) => (
                    <span key={j} className={op === "+" ? "bg-emerald-500/20 text-emerald-200" : op === "-" ? "bg-rose-500/20 text-rose-200 line-through" : "text-slate-400"}>{t} </span>))}</div>
                ) : e.op === "add" ? <div className="text-xs text-emerald-200 mt-1">+ {e.after}</div> : <div className="text-xs text-rose-200 line-through mt-1">{e.before}</div>}
              </li>
            ))}
          </ol>
        )}
      </Card>
      <div className="space-y-4">
        <Card>
          <div className="text-sm font-bold text-ink mb-2 flex items-center gap-2"><Upload className="w-4 h-4 text-sky-400" /> Add document</div>
          <select value={dtype} onChange={(e) => setDtype(e.target.value)} className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2 py-1.5 text-xs mb-2">
            <option value="corrigendum">Corrigendum / addendum</option>
            <option value="prebid">Pre-bid clarifications (Q&A)</option>
            <option value="annexure">Annexure / additional tender volume</option>
            <option value="auto">Auto-detect</option>
          </select>
          <input type="file" accept=".pdf,.docx,.txt,.md,.png,.jpg" onChange={(e) => setFile(e.target.files?.[0] || null)} className="text-xs text-slate-300 w-full mb-2" />
          <Button disabled={!file} onClick={async () => { await addTenderDocument(tenderId, file!, dtype); setFile(null); onChanged(); }}>Upload & re-compile</Button>
        </Card>
        {isDemo && (
          <Card className="border-violet-500/30">
            <div className="text-sm font-bold text-ink mb-1">Demo script</div>
            <p className="text-[0.8125rem] text-slate-400 mb-3">Corrigendum 1 fixes the proven contradiction and the brand clause. Corrigendum 2 “tightens” strength — and silently makes three clauses mathematically impossible together. Watch the solver catch it.</p>
            <div className="flex gap-2">
              <Button variant="subtle" disabled={applied.includes("corrigendum_1.txt")} onClick={async () => { await demoCorrigendum(tenderId, 1); onChanged(); }}>Apply Corrigendum 1</Button>
              <Button variant="subtle" disabled={applied.includes("corrigendum_2.txt")} onClick={async () => { await demoCorrigendum(tenderId, 2); onChanged(); }}>Apply Corrigendum 2</Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
