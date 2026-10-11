"use client";

import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { Check, ClipboardCopy, Download, FileText, Loader2, Plus, Trash2, X } from "lucide-react";
import { specBlock, specBlockDocx } from "@/lib/api";
import { SpeakButton } from "@/components/speak";

type Entry = { base: string; item?: string; title?: string };
type Ctx = { entries: Entry[]; add: (e: Entry) => void; remove: (base: string) => void; clear: () => void };
const BasketCtx = createContext<Ctx | null>(null);

export function SpecBasketProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<Entry[]>([]);
  return (
    <BasketCtx.Provider value={{
      entries,
      add: (e) => setEntries((x) => (x.some((y) => y.base === e.base && y.item === e.item) ? x : [...x, e])),
      remove: (b) => setEntries((x) => x.filter((y) => y.base !== b)),
      clear: () => setEntries([]),
    }}>
      {children}
      <SpecBasketBar />
    </BasketCtx.Provider>
  );
}

export const useBasket = () => useContext(BasketCtx);

export function ConfidenceBadge({ level }: { level?: string }) {
  if (!level) return null;
  const m: Record<string, [string, string, string]> = {
    high: ["High confidence", "bg-[#e7f5e9] text-[#0d6b06] border-[#9bd3a3]", "Lexical and semantic retrievers agree and the query words are covered by the standard’s title / scope (≈88 % top-1 precision on the benchmark)."],
    medium: ["Possible — verify", "bg-[#fff4e0] text-[#8a5300] border-[#f2cf8c]", "Partial agreement — check the scope clause before citing."],
    low: ["Low — no confident match", "bg-[#f1f5f9] text-[#475569] border-[#cbd5e1]", "The retrievers disagree or the words are not covered. SpecSure abstains rather than guess."],
  };
  const [label, cls, tip] = m[level] || m.low;
  return <span title={tip} className={`text-[0.8125rem] px-1.5 py-0.5 rounded-sm border font-bold ${cls}`}>{label}</span>;
}

export function SpecBlockButton({ base, item, title, compact }: { base: string; item?: string; title?: string; compact?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={(e) => { e.stopPropagation(); setOpen(true); }}
        className={`inline-flex items-center gap-1 rounded-md border border-[#0f2748] text-[#0f2748] font-bold hover:bg-[#eef4fb] ${compact ? "px-2 py-1 text-[0.8125rem]" : "px-3 py-1.5 text-[0.875rem]"}`}>
        <FileText className="w-3.5 h-3.5" />Spec block
      </button>
      {open && <SpecBlockModal base={base} item={item} title={title} onClose={() => setOpen(false)} />}
    </>
  );
}

function SpecBlockModal({ base, item, title, onClose }: { base: string; item?: string; title?: string; onClose: () => void }) {
  const basket = useBasket();
  const [block, setBlock] = useState<any>(null);
  const [text, setText] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [itemName, setItemName] = useState(item || "");
  const load = (it?: string) => specBlock(base, it || undefined).then((b: any) => { setBlock(b); setText(b.text + "\n\nNote: " + b.notes.join(" ")); }).catch((e) => setErr(e.message));
  useEffect(() => { load(item); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="fixed inset-0 z-[80] bg-black/40 flex items-center justify-center p-4" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-lift w-full max-w-3xl max-h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="px-5 py-3 border-b border-[#e2e8f0] flex items-center justify-between">
          <div>
            <div className="text-[0.8125rem] uppercase tracking-widest font-bold text-[#b7862b]">Exportable specification block</div>
            <div className="font-extrabold text-[#0f2748]">{block?.edition || base} {title ? `— ${title.slice(0, 70)}` : ""}</div>
          </div>
          <button onClick={onClose} aria-label="Close" className="p-1.5 rounded hover:bg-[#f1f5f9]"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-5 space-y-3 overflow-y-auto">
          <label className="text-[0.875rem] text-slate-400 flex items-center gap-2">Item name in the clause
            <input value={itemName} onChange={(e) => setItemName(e.target.value)} placeholder={title || "product"}
              className="flex-1 border border-[#c9d5e6] rounded px-2 py-1 text-[0.9375rem]" />
            <button onClick={() => { setBlock(null); load(itemName); }} className="px-2 py-1 rounded border border-[#c9d5e6] text-[0.875rem] font-semibold">Apply</button>
          </label>
          {err && <div className="text-[#8a1414] text-[0.9375rem]">{err}</div>}
          {!block && !err && <div className="text-[0.9375rem] text-slate-500 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" />Drafting from the standard’s clauses…</div>}
          {block && (
            <>
              {block.replaced && <div className="text-[0.875rem] bg-[#fdecec] border border-[#f1b0b0] text-[#8a1414] rounded p-2">{block.replaced}</div>}
              <textarea value={text} onChange={(e) => setText(e.target.value)} rows={14}
                className="w-full border border-[#c9d5e6] rounded-md p-3 text-[0.875rem] leading-relaxed font-sans" aria-label="Specification text" />
              <details className="text-[0.875rem]">
                <summary className="cursor-pointer font-semibold text-[#1d4f93]">Where each sentence comes from</summary>
                <ul className="mt-1 space-y-1">{block.clauses.map((c: any) => <li key={c.key}><b>{c.key}. {c.heading}</b> — <span className="text-slate-400">{c.source}</span></li>)}</ul>
              </details>
            </>
          )}
        </div>
        <div className="px-5 py-3 border-t border-[#e2e8f0] flex flex-wrap gap-2 justify-end">
          <button disabled={!block} onClick={async () => { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
            className="px-3 py-2 rounded-md border border-[#c9d5e6] text-[0.9375rem] font-bold flex items-center gap-1.5">{copied ? <Check className="w-4 h-4" /> : <ClipboardCopy className="w-4 h-4" />}{copied ? "Copied" : "Copy"}</button>
          {block && <SpeakButton text={block.clauses.map((c: any) => `${c.heading}. ${c.text}`).join(" ")} label="Read aloud" />}
          {basket && <button disabled={!block} onClick={() => { basket.add({ base: block.base, item: itemName || undefined, title }); onClose(); }}
            className="px-3 py-2 rounded-md bg-[#0f2748] text-white text-[0.9375rem] font-bold flex items-center gap-1.5"><Plus className="w-4 h-4" />Add to specification</button>}
        </div>
      </div>
    </div>
  );
}

function SpecBasketBar() {
  const b = useBasket();
  const [busy, setBusy] = useState(false);
  if (!b || !b.entries.length) return null;
  return (
    <div className="fixed bottom-0 inset-x-0 z-[70] bg-[#0f2748] text-white shadow-lift print:hidden">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex flex-wrap items-center gap-3">
        <FileText className="w-4 h-4 text-[#ff9933]" />
        <span className="text-[0.9375rem] font-bold">Specification: {b.entries.length} standard(s)</span>
        <div className="flex flex-wrap gap-1.5 flex-1">
          {b.entries.map((e) => (
            <span key={e.base + (e.item || "")} className="text-[0.8125rem] bg-white/10 rounded px-2 py-0.5 flex items-center gap-1">
              {e.item ? `${e.item.slice(0, 24)} · ` : ""}{e.base}
              <button onClick={() => b.remove(e.base)} aria-label={`Remove ${e.base}`}><X className="w-3 h-3" /></button>
            </span>
          ))}
        </div>
        <button disabled={busy} onClick={async () => {
          setBusy(true);
          try {
            const blob = await specBlockDocx(b.entries.map((e) => ({ base: e.base, item: e.item })));
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a"); a.href = url; a.download = "specification_indian_standards.docx"; a.click(); URL.revokeObjectURL(url);
          } finally { setBusy(false); }
        }} className="px-3 py-1.5 rounded-md bg-[#ff9933] text-[#0f2748] text-[0.875rem] font-extrabold flex items-center gap-1.5">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}Download Word
        </button>
        <button onClick={b.clear} className="px-2 py-1.5 rounded-md border border-white/30 text-[0.875rem] flex items-center gap-1"><Trash2 className="w-3.5 h-3.5" />Clear</button>
      </div>
    </div>
  );
}
