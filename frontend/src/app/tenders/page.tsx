"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Building2, Plus, Sparkles, FileUp, ArrowRight } from "lucide-react";
import { Badge, Button, Card, ErrorBox, Loading, SectionTitle } from "@/components/ui";
import { createTender, demoSeed, listTenders } from "@/lib/api";
import { gateStyle, cn } from "@/lib/utils";
import { PageIntro } from "@/components/gov-ui";

export default function TendersPage() {
  const router = useRouter();
  const [rows, setRows] = useState<any[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [ref, setRef] = useState("");
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [types, setTypes] = useState<string[]>([]);
  const load = () => listTenders().then(setRows).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  const submit = async () => {
    setErr(null);
    const fd = new FormData();
    fd.append("title", title || files[0]?.name || "Untitled tender");
    if (ref) fd.append("reference_no", ref);
    if (text.trim()) fd.append("text", text);
    files.forEach((f) => fd.append("files", f));
    if (files.length) fd.append("doc_types", types.join(","));
    try {
      const r = await createTender(fd);
      router.push(`/tenders/${r.id}`);
    } catch (e: any) { setErr(e.message); }
  };

  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-8">
      <PageIntro icon={Building2} kicker="Tender vetting · for procurement officers" title="Check a tender before you publish it"
        sub="Upload a tender document (PDF, Word, scan or pasted text). SpecSure reads every clause and flags outdated or withdrawn standards, missing mandatory certification, contradictions, missing tests and clauses that unfairly limit competition — each with the clause it came from."
        steps={["Upload the tender (and any corrigenda) on the right, or open one from the list.", "Read the readiness score and the issues found.", "Fix or dismiss each issue, then publish."]}
        details={<>The tender is compiled into a Digital Twin: requirements, standards resolved as of the tender date, QCOs, tests, formal contradiction proofs (Z3), market-restriction evidence, predicted pre-bid questions and a publish gate.</>}
        right={<Button variant="subtle" onClick={async () => { await demoSeed(); load(); }}><Sparkles className="w-3.5 h-3.5" />Load demo tenders</Button>} />
      <ErrorBox error={err} />
      <div className="grid lg:grid-cols-[1fr_420px] gap-6">
        <div className="space-y-3">
          {rows === null ? <Loading /> : rows.length === 0 ? <Card className="text-sm text-slate-400">No tenders yet — create one or load the demo.</Card> : rows.map((t) => (
            <Link key={t.id} href={`/tenders/${t.id}`} className="block">
              <Card className="hover:border-sky-500/40 transition-colors">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex-1 min-w-[240px]">
                    <div className="text-sm font-bold text-ink">{t.title}</div>
                    <div className="text-[0.8125rem] text-slate-400">{t.reference_no || t.id} · {t.status} · {(t.domains || []).join(", ")} · {t.documents} document(s)</div>
                  </div>
                  {t.counts && <div className="flex flex-wrap gap-x-2 text-[0.8125rem]" title="Open issues by severity"><span className="text-rose-300 font-semibold">{t.counts.critical} critical</span><span className="text-amber-300 font-semibold">{t.counts.major} major</span><span className="text-sky-300">{t.counts.minor} minor</span></div>}
                  <div className="text-2xl font-mono font-bold text-ink w-16 text-right">{t.readiness_score != null ? Math.round(t.readiness_score) : "—"}</div>
                  <span className={cn("px-2 py-1 rounded-full border text-[0.75rem] font-bold", gateStyle(t.gate))}>{t.gate || "—"}</span>
                  <ArrowRight className="w-4 h-4 text-slate-500" />
                </div>
              </Card>
            </Link>
          ))}
        </div>
        <Card glow className="h-fit space-y-3">
          <div className="text-sm font-bold text-ink flex items-center gap-2"><Plus className="w-4 h-4 text-sky-400" />New tender</div>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs" />
          <input value={ref} onChange={(e) => setRef(e.target.value)} placeholder="Reference / NIT no. (optional)" className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs" />
          <label className="block rounded-xl border border-dashed border-slate-700 p-4 text-center cursor-pointer hover:border-sky-500/50">
            <FileUp className="w-5 h-5 text-sky-400 mx-auto mb-1" />
            <span className="text-xs text-slate-300">Tender PDF / DOCX / scanned images / TXT — multiple files (tender volumes, annexures, corrigenda, pre-bid Q&A)</span>
            <input type="file" multiple className="hidden" accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.tif"
              onChange={(e) => { const fs = Array.from(e.target.files || []); setFiles(fs); setTypes(fs.map(() => "auto")); }} />
          </label>
          {files.map((f, i) => (
            <div key={i} className="flex items-center gap-2 text-[0.8125rem]">
              <span className="flex-1 truncate text-slate-300">{f.name}</span>
              <select value={types[i]} onChange={(e) => setTypes(types.map((t, j) => (j === i ? e.target.value : t)))} className="bg-slate-950 border border-slate-700 rounded px-1 py-0.5">
                {["auto", "tender", "annexure", "corrigendum", "prebid"].map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
          ))}
          <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="…or paste tender text (clause numbers like 4.1, 4.2 are recognised)" className="w-full h-32 bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs" />
          <Button className="w-full" disabled={!files.length && !text.trim()} onClick={submit}>Check this tender</Button>
          <p className="text-[0.75rem] text-slate-500">Parsing: PyMuPDF text + table finder, OCR fallback for scanned pages (Tesseract / RapidOCR), optional Docling layout AI.</p>
        </Card>
      </div>
    </div>
  );
}
