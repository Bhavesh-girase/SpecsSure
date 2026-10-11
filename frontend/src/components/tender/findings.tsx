"use client";

import { useMemo, useState } from "react";
import { Wand2, ChevronDown, ChevronRight, Check, X, Scale, FileDiff } from "lucide-react";
import { Badge, Button, Card, Empty, SevBadge } from "@/components/ui";
import { autofix, explainFinding, reviewFinding } from "@/lib/api";
import { cn } from "@/lib/utils";

const CATS = ["all", "contradiction", "standards", "certification", "restriction", "testing", "completeness", "ambiguity", "measurability", "drafting", "security"];

export function Findings({ twin, tenderId, onChanged }: { twin: any; tenderId: string; onChanged: () => void }) {
  const [cat, setCat] = useState("all");
  const [showClosed, setShowClosed] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [draft, setDraft] = useState<any>(null);
  const [open, setOpen] = useState<string | null>(null);

  const list = useMemo(() => twin.findings.filter((f: any) =>
    (cat === "all" || f.category === cat) && (showClosed || ["open", "accepted", undefined].includes(f.review_status))), [twin, cat, showClosed]);
  const fixable = list.filter((f: any) => f.fix);

  const toggle = (fp: string) => setSelected((s) => { const n = new Set(s); n.has(fp) ? n.delete(fp) : n.add(fp); return n; });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {CATS.map((c) => {
          const n = c === "all" ? twin.findings.length : twin.findings.filter((f: any) => f.category === c).length;
          if (c !== "all" && !n) return null;
          return (
            <button key={c} onClick={() => setCat(c)} className={cn("px-2.5 py-1 rounded-full text-[0.8125rem] border capitalize",
              cat === c ? "bg-sky-500/20 border-sky-500/50 text-sky-200" : "border-slate-700 text-slate-400 hover:text-slate-200")}>{c} <span className="opacity-60">{n}</span></button>
          );
        })}
        <label className="ml-auto text-[0.8125rem] text-slate-400 flex items-center gap-1.5">
          <input type="checkbox" checked={showClosed} onChange={(e) => setShowClosed(e.target.checked)} /> show dismissed / fixed
        </label>
      </div>

      <Card className="flex flex-wrap items-center gap-3 py-3">
        <Wand2 className="w-4 h-4 text-violet-300" />
        <span className="text-xs text-slate-300"><b>{selected.size}</b> autofix(es) selected · {fixable.length} available in view</span>
        <Button variant="ghost" onClick={() => setSelected(new Set(fixable.map((f: any) => f.fingerprint)))}>Select all fixable</Button>
        <Button variant="primary" disabled={!selected.size} onClick={async () => setDraft((await autofix(tenderId, Array.from(selected), false)).draft)}>
          <FileDiff className="w-3.5 h-3.5" /> Preview draft corrigendum
        </Button>
      </Card>

      {draft && (
        <Card glow>
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-bold text-ink">Draft corrigendum (generated from approved fixes)</div>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={() => setDraft(null)}>Close</Button>
              <Button variant="success" onClick={async () => { await autofix(tenderId, Array.from(selected), true); setDraft(null); setSelected(new Set()); onChanged(); }}>
                Issue & re-compile
              </Button>
            </div>
          </div>
          <pre className="text-[0.8125rem] text-slate-200 whitespace-pre-wrap bg-slate-950/70 border border-slate-800 rounded-lg p-3 max-h-80 overflow-auto">{draft.text}</pre>
          <p className="text-[0.8125rem] text-slate-500 mt-2">Issuing adds it as a corrigendum document: the clause history, blame and the whole twin are re-computed — any regression it introduces is flagged immediately.</p>
        </Card>
      )}

      {list.length === 0 ? <Empty>No findings in this view. 🎉</Empty> : (
        <div className="space-y-2">
          {list.map((f: any) => (
            <FindingCard key={f.fingerprint} f={f} tenderId={tenderId} open={open === f.fingerprint}
              onToggle={() => setOpen(open === f.fingerprint ? null : f.fingerprint)}
              selected={selected.has(f.fingerprint)} onSelect={() => toggle(f.fingerprint)} onChanged={onChanged} />
          ))}
        </div>
      )}
    </div>
  );
}

function FindingCard({ f, tenderId, open, onToggle, selected, onSelect, onChanged }: any) {
  const [comment, setComment] = useState("");
  const [expl, setExpl] = useState<any>(null);
  const closed = ["dismissed", "fixed"].includes(f.review_status);
  return (
    <div className={cn("rounded-xl border transition-colors", closed ? "border-slate-800 bg-slate-900/30 opacity-60" : "border-slate-800 bg-slate-900/60 hover:border-slate-700")}>
      <div className="flex items-start gap-3 p-3">
        {f.fix ? <input type="checkbox" className="mt-1" checked={selected} onChange={onSelect} title="Include autofix" /> : <span className="w-3.5" />}
        <button onClick={onToggle} className="flex-1 text-left">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <SevBadge sev={f.severity} />
            <span className="font-mono text-[0.75rem] text-slate-400">{f.rule_id}</span>
            <span className="text-[0.8125rem] text-slate-300 font-semibold">{f.rule_name}</span>
            {f.clause_key && <Badge className="border-slate-700 text-slate-300">Cl. {f.clause_key}{f.page ? ` · p.${f.page}` : ""}</Badge>}
            {f.source !== "deterministic" && <Badge className="border-violet-500/40 text-violet-300">{f.source === "solver" ? "SMT proof" : f.source}</Badge>}
            {f.fix && <Badge className="border-violet-500/40 text-violet-300"><Wand2 className="w-3 h-3" />autofix</Badge>}
            {f.review_status && f.review_status !== "open" && <Badge className="border-emerald-500/40 text-emerald-300">{f.review_status}</Badge>}
          </div>
          <div className="text-xs text-slate-100">{f.message}</div>
          {f.suggestion && <div className="text-[0.8125rem] text-sky-200/80 mt-1">→ {f.suggestion}</div>}
        </button>
        {open ? <ChevronDown className="w-4 h-4 text-slate-500 mt-1" /> : <ChevronRight className="w-4 h-4 text-slate-500 mt-1" />}
      </div>
      {open && (
        <div className="border-t border-slate-800 p-3 space-y-3 text-xs">
          {f.quote && <div><div className="text-[0.75rem] uppercase text-slate-500 mb-1">Source text</div><blockquote className="border-l-2 border-amber-400/60 pl-3 text-amber-100/90 italic">{f.quote}</blockquote></div>}
          {f.basis && <div className="flex gap-2 text-slate-300"><Scale className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />{f.basis}</div>}
          {f.evidence?.length > 0 && (
            <div>
              <div className="text-[0.75rem] uppercase text-slate-500 mb-1">Evidence</div>
              <div className="space-y-1">
                {f.evidence.map((e: any, i: number) => (
                  <div key={i} className="rounded-lg bg-slate-950/60 border border-slate-800 p-2">
                    <span className="font-mono text-[0.75rem] text-sky-300 mr-2">{e.type}</span>
                    <span className="text-slate-200">{e.ref}</span>
                    {e.detail && <span className="text-slate-400"> — {typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail)}</span>}
                    {e.url && <a href={e.url} target="_blank" rel="noreferrer" className="ml-2 text-sky-400 underline">source</a>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {f.fix && (
            <div>
              <div className="text-[0.75rem] uppercase text-slate-500 mb-1">Autofix</div>
              <pre className="text-[0.8125rem] bg-slate-950/60 border border-slate-800 rounded-lg p-2 whitespace-pre-wrap">{f.fix.op === "replace" ? `- ${f.fix.find}\n+ ${f.fix.replace}` : JSON.stringify(f.fix, null, 1)}</pre>
            </div>
          )}
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={async () => setExpl(await explainFinding(tenderId, f.fingerprint, "hi"))}>हिन्दी में समझाएँ</Button>
            <Button variant="ghost" onClick={async () => setExpl(await explainFinding(tenderId, f.fingerprint, "en"))}>Plain English</Button>
            {expl && <span className="text-[0.75rem] text-violet-300">{expl.generated_by === "llm" ? "AI-generated · evidence-fenced" : expl.note}</span>}
          </div>
          {expl && <div className="rounded-lg border border-violet-500/30 bg-violet-500/5 p-2 text-slate-200">{expl.text}</div>}
          {f.review && <div className="text-slate-400">Reviewed by {f.review.reviewer}: “{f.review.comment}”</div>}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Justification (required to dismiss) — recorded in the audit ledger"
              className="flex-1 min-w-[240px] bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200" />
            <Button variant="subtle" onClick={async () => { await reviewFinding(tenderId, f.fingerprint, "accepted", comment); onChanged(); }}><Check className="w-3.5 h-3.5" />Accept</Button>
            <Button variant="success" onClick={async () => { await reviewFinding(tenderId, f.fingerprint, "fixed", comment || "Fixed"); onChanged(); }}>Mark fixed</Button>
            <Button variant="danger" disabled={!comment.trim()} onClick={async () => { await reviewFinding(tenderId, f.fingerprint, "dismissed", comment); onChanged(); }}><X className="w-3.5 h-3.5" />Dismiss</Button>
            {f.review_status && f.review_status !== "open" && <Button variant="ghost" onClick={async () => { await reviewFinding(tenderId, f.fingerprint, "open", comment); onChanged(); }}>Re-open</Button>}
          </div>
        </div>
      )}
    </div>
  );
}
