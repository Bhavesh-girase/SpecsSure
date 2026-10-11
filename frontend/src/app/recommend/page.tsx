"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle, BadgeCheck, BookOpenCheck, ChevronDown, ChevronRight, ExternalLink, FileSearch, Languages, Library, Link2, Loader2,
  Mic, MicOff, Search, ShieldCheck, Sparkles,
} from "lucide-react";
import { corpusRecommend, corpusRecommendDocument, corpusStandard, corpusStats } from "@/lib/api";
import { Notice, PageHead } from "@/components/gov-ui";
import { T } from "@/lib/prefs";
import { StandardsNetwork } from "@/components/standards-network";
import { DependencyTree } from "@/components/dependency-tree";
import { SpeakButton, recommendationSpeech, speak } from "@/components/speak";
import { LabsPanel } from "@/components/labs-panel";
import { ConfidenceBadge, SpecBasketProvider, SpecBlockButton } from "@/components/spec-basket";

const EXAMPLES: [string, string][] = [
  ["en", "PVC insulated copper wire for house wiring, 450/750 V, FR"],
  ["en", "Ordinary Portland cement 53 grade for RCC work"],
  ["en", "portable fire extinguisher, dry powder, 9 kg"],
  ["en", "helmet for two wheeler riders"],
  ["hi", "दोपहिया वाहन चालकों के लिए हेलमेट"],
  ["hi", "सरिया Fe 500D"],
  ["en", "HDPE pipes for drinking water supply"],
  ["te", "ఎల్ఈడి బల్బ్"],
  ["hi", "स्प्लिट एयर कंडीशनर"],
  ["kn", "ಸೀಲಿಂಗ್ ಫ್ಯಾನ್"],
  ["ta", "பிளாஸ்டிக் நாற்காலி"],
  ["en", "LED luminaire for road and street lights"],
];

const KIND_TONE: Record<string, string> = {
  normative: "#0f2748", test_method: "#1d4f93", terminology: "#6d28d9", safety: "#c0262d", installation: "#b45309",
  sampling: "#0e7490", packaging_marking: "#475569", material: "#047857", allied_product: "#334155",
};

function useSpeech(onText: (t: string) => void) {
  const rec = useRef<any>(null);
  const [on, setOn] = useState(false);
  const [ok, setOk] = useState(false);
  useEffect(() => { setOk(!!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)); }, []);
  return {
    ok, on,
    start: (lang: string) => {
      const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SR) return;
      const r = new SR(); r.lang = lang; r.interimResults = false;
      r.onresult = (e: any) => onText(Array.from(e.results).map((x: any) => x[0].transcript).join(" "));
      r.onend = () => setOn(false); r.onerror = () => setOn(false);
      rec.current = r; setOn(true); r.start();
    },
    stop: () => { rec.current?.stop(); setOn(false); },
  };
}

function highlight(text: string, q: string) {
  const STOPW = new Set(["for", "and", "the", "with", "from", "used", "use", "type", "shall", "each", "into", "than", "that", "this"]);
  const words = Array.from(new Set((q.toLowerCase().match(/[a-z0-9]{3,}/g) || []).filter((w) => !STOPW.has(w))));
  if (!words.length || !text) return text;
  const rx = new RegExp(`(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "ig");
  return text.split(rx).map((p, i) => (i % 2 ? <mark key={i} className="bg-[#fff1cc] text-inherit rounded-sm px-0.5">{p}</mark> : p));
}

export default function RecommendPage() {
  const [q, setQ] = useState(EXAMPLES[0][1]);
  const [res, setRes] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [lang, setLang] = useState("en-IN");
  const [division, setDivision] = useState("");
  const [speakAnswers, setSpeakAnswers] = useState(false);
  const [mode, setMode] = useState<"text" | "doc">("text");
  const [docRes, setDocRes] = useState<any>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  async function runDoc(f: File) {
    setBusy(true); setErr(null); setDocRes(null);
    try { setDocRes(await corpusRecommendDocument(f)); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  const speech = useSpeech((t) => setQ(t));
  useEffect(() => {
    corpusStats().then(setStats).catch(() => {});
    const u = new URLSearchParams(window.location.search).get("q");
    if (u) { setQ(u); run(u); }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  async function run(text?: string) {
    const query = (text ?? q).trim();
    if (query.length < 3) return;
    setBusy(true); setErr(null);
    try {
      const out = await corpusRecommend(query, 8, 1, division);
      setRes(out);
      if (speakAnswers && out.results?.[0]) speak(recommendationSpeech(out.results[0], out.language), ({ hi: "hi-IN", mr: "mr-IN", ta: "ta-IN", te: "te-IN", bn: "bn-IN", kn: "kn-IN" } as any)[out.language] || "en-IN");
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  return (
    <SpecBasketProvider>
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-20 space-y-6">
      <PageHead icon={FileSearch} kicker={<T en="Standards Recommender · core of PS SIH26108" hi="मानक अनुशंसा · पीएस SIH26108 का मूल" />}
        title={<T en="Find the right Indian Standard — and everything it depends on" hi="सही भारतीय मानक खोजें — और उससे जुड़े सभी मानक" />}
        right={<Link href="/extension" className="text-[0.875rem] font-bold text-[#1d4f93] underline">Use it inside GeM / CPPP → browser extension</Link>}
        sub={<T en="Describe the product or paste a specification in any Indian language. Recommendations come from the scope clauses of the full Indian Standards corpus; allied standards come from each standard's own references, test and terminology clauses; editions and amendments are checked against the BIS portal."
                hi="उत्पाद का वर्णन लिखें या विनिर्देश चिपकाएँ — किसी भी भारतीय भाषा में। अनुशंसाएँ पूरे भारतीय मानक संग्रह के ‘स्कोप’ खंडों से आती हैं; संबद्ध मानक प्रत्येक मानक के अपने संदर्भ, परीक्षण और शब्दावली खंडों से।" />} />

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 bg-white border border-[#d5deea] rounded-lg overflow-hidden shadow-card">
          {[
            [stats.designations?.toLocaleString("en-IN"), "Indian Standards in the catalogue", "मानक सूची में"],
            [stats.parsed_with_text?.toLocaleString("en-IN"), "full texts parsed", "पूर्ण पाठ विश्लेषित"],
            [stats.relations?.toLocaleString("en-IN"), "typed links (refs, tests, terms…)", "वर्गीकृत संबंध"],
            [stats.layers?.portal_designations?.toLocaleString("en-IN") || Object.keys(stats.divisions || {}).length, stats.layers?.portal_designations ? `editions checked on BIS portal (${stats.layers.portal_fetched})` : "BIS divisions", "बीआईएस पोर्टल से संस्करण"],
            [stats.layers?.gem_categories?.toLocaleString("en-IN") || (stats.dense_index ? "BM25 + dense" : "BM25"), stats.layers?.gem_categories ? "GeM categories linked" : "retrieval (multilingual)", "जेम श्रेणियाँ"],
          ].map(([v, en, hi], i) => (
            <div key={i} className={`p-4 text-center ${i ? "border-l border-[#e2e8f0]" : ""}`}>
              <div className="text-xl font-extrabold font-mono text-[#0f2748]">{v ?? "—"}</div>
              <div className="text-[0.8125rem] font-semibold text-slate-500 uppercase tracking-wide"><T en={en as string} hi={hi as string} /></div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-1" role="tablist">
        {([["text", "Describe a product", "उत्पाद का वर्णन"], ["doc", "Upload a tender / specification", "निविदा / विनिर्देश अपलोड"]] as const).map(([m, en, hi]) => (
          <button key={m} role="tab" aria-selected={mode === m} onClick={() => setMode(m)}
            className={`px-4 py-2 rounded-t-md text-[0.9375rem] font-bold border border-b-0 ${mode === m ? "bg-white text-[#0f2748] border-[#d5deea]" : "bg-[#e8eef6] text-slate-400 border-transparent"}`}>
            <T en={en} hi={hi} />
          </button>
        ))}
      </div>
      {mode === "doc" && (
        <div className="bg-white border border-[#d5deea] rounded-lg shadow-card p-5 space-y-3 -mt-6">
          <p className="text-[0.9375rem] text-slate-400">PDF, DOCX, TXT or a scanned page / phone photo (OCR). Every technical section is read in context; the result shows which standards the
            document should cite, with the text that led to each — and checks the IS numbers it already cites.</p>
          <div onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) runDoc(f); }}
            onClick={() => fileRef.current?.click()}
            className="border-2 border-dashed border-[#c9d5e6] hover:border-[#1d4f93] rounded-md p-8 text-center cursor-pointer text-[0.9375rem] text-slate-400">
            {busy ? <span className="flex items-center justify-center gap-2 text-[#1d4f93]"><Loader2 className="w-4 h-4 animate-spin" />Reading the document…</span>
                  : <span className="flex flex-col items-center gap-1"><FileSearch className="w-6 h-6 text-slate-400" />Drop a file here or click to choose</span>}
            <input ref={fileRef} type="file" className="hidden" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg" onChange={(e) => { const f = e.target.files?.[0]; if (f) runDoc(f); e.target.value = ""; }} />
          </div>
          {docRes && <DocResult d={docRes} />}
        </div>
      )}
      {mode === "text" && <form onSubmit={(e) => { e.preventDefault(); run(); }} className="-mt-6 bg-white border-t-4 border-[#ff9933] border-x border-b border-x-[#d5deea] border-b-[#d5deea] rounded-lg shadow-card p-5 space-y-3">
        <label htmlFor="q" className="font-bold text-[#0f2748] flex items-center gap-2"><Search className="w-4 h-4" /><T en="Product description, specification or tender clause" hi="उत्पाद विवरण, विनिर्देश या निविदा खंड" /></label>
        <div className="relative">
          <textarea id="q" rows={3} value={q} onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) run(); }}
            className="w-full rounded-md border border-[#c9d5e6] bg-[#f8fafc] p-3 pr-14 text-[1.0625rem] outline-none focus:border-[#1d4f93]" />
          {speech.ok && (
            <button type="button" onClick={() => (speech.on ? speech.stop() : speech.start(lang))} aria-label="Speak"
              className={`absolute right-3 top-3 p-2 rounded-full border ${speech.on ? "bg-[#c0262d] border-[#c0262d] text-white animate-pulse" : "bg-white border-[#c9d5e6] text-[#1d4f93]"}`}>
              {speech.on ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {EXAMPLES.map(([l, x]) => (
            <button type="button" key={x} onClick={() => { setQ(x); run(x); }}
              className="text-[0.8125rem] px-2 py-1 rounded-sm bg-[#eef4fb] text-[#13325d] hover:bg-[#d6e4f5]"><b className="uppercase mr-1">{l}</b>{x}</button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button type="submit" disabled={busy} className="px-5 py-2.5 rounded-md bg-[#0f2748] text-white font-bold text-sm flex items-center gap-2 hover:bg-[#1d4f93] disabled:opacity-60">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}<T en="Recommend standards" hi="मानक सुझाएँ" />
          </button>
          <label className="text-[0.875rem] text-slate-400 flex items-center gap-1.5"><Languages className="w-3.5 h-3.5" />Voice
            <select value={lang} onChange={(e) => setLang(e.target.value)} className="border border-[#c9d5e6] rounded px-1.5 py-1 text-[0.875rem]">
              {[["en-IN", "English"], ["hi-IN", "हिन्दी"], ["ta-IN", "தமிழ்"], ["te-IN", "తెలుగు"], ["mr-IN", "मराठी"], ["bn-IN", "বাংলা"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="text-[0.875rem] text-slate-400 flex items-center gap-1.5" title="Read the top answer aloud after each search (browser voices)">
            <input type="checkbox" checked={speakAnswers} onChange={(e) => setSpeakAnswers(e.target.checked)} />Speak answers</label>
          <label className="text-[0.875rem] text-slate-400 flex items-center gap-1.5">Sector
            <select value={division} onChange={(e) => setDivision(e.target.value)} className="border border-[#c9d5e6] rounded px-1.5 py-1 text-[0.875rem] max-w-[220px]" aria-label="Restrict to a BIS division">
              <option value="">Any BIS division</option>
              {(stats?.division_list || []).map((d: string) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
          <span className="text-[0.8125rem] text-slate-500">Ctrl + Enter to search</span>
        </div>
      </form>}

      {err && <Notice tone="bad">{err}</Notice>}
      {mode === "text" && res && (
        <div className="space-y-4">
          {res.translated && <Notice tone="info"><Languages className="w-4 h-4 inline -mt-0.5 mr-1" />Detected <b>{res.language}</b> — searched as: “{res.query_en}”
            {res.reading?.length > 0 && <div className="mt-1 flex flex-wrap gap-1.5">{res.reading.map((t: any, i: number) => (
              <span key={i} className="text-[0.8125rem] bg-white border border-[#adc8ea] rounded px-1.5 py-0.5" title={t.skeleton ? `romanised “${t.roman}”, sound skeleton ${t.skeleton}` : undefined}>
                {t.word} → <b>{t.english}</b> <i className="text-slate-500">{t.via}</i></span>))}
              <span className="text-[0.8125rem] text-slate-500">offline reading: procurement glossary + loanword transliteration; the multilingual embeddings also read the original text</span></div>}
          </Notice>}
          {res.results.map((r: any, i: number) => <ResultCard key={r.base} r={r} rank={i + 1} q={res.query_en} open={i === 0} language={res.language} />)}
          {!res.results.length && <Notice tone="warn">No standard matched. Try describing the product with its material or use (e.g. “steel pipes for water mains”).</Notice>}
          <p className="text-[0.8125rem] text-slate-500 flex gap-2"><ShieldCheck className="w-4 h-4 shrink-0" />{res.disclaimer}</p>
        </div>
      )}
    </div>
    </SpecBasketProvider>
  );
}

function ResultCard({ r, rank, q, open: open0, language = "en" }: { r: any; rank: number; q: string; open: boolean; language?: string }) {
  const [open, setOpen] = useState(open0);
  const [detail, setDetail] = useState<any>(r.allied ? r : null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (open && !detail && !loading) {
      setLoading(true);
      corpusStandard(r.base).then(setDetail).catch(() => {}).finally(() => setLoading(false));
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  const cert = (detail?.certification || r.certification || []) as any[];
  const status = detail?.status || r.status;
  return (
    <article className={`bg-white border rounded-lg shadow-card overflow-hidden ${rank === 1 ? "border-[#1d4f93]" : "border-[#d5deea]"}`}>
      <button onClick={() => setOpen(!open)} className="w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-[#f8fafc]" aria-expanded={open}>
        <span className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-[0.9375rem] font-extrabold ${rank === 1 ? "bg-[#ff9933] text-[#0f2748]" : "bg-[#eef2f7] text-[#334155]"}`}>{rank}</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono font-extrabold text-[#0f2748] text-[1.0625rem]">{r.base}{r.latest_archived_year ? `:${r.latest_archived_year}` : ""}</span>
            {r.committee_code && <span className="text-[0.8125rem] px-1.5 py-0.5 rounded-sm bg-[#eef4fb] text-[#1d4f93] font-bold">{r.committee_code}</span>}
            {r.aspect ? <span title="Document type as classified by BIS" className="text-[0.8125rem] px-1.5 py-0.5 rounded-sm bg-[#f1f5f9] text-[#334155] font-semibold">{r.aspect}</span>
              : r.doc_kind && r.doc_kind !== "allied_product" && <span className="text-[0.8125rem] px-1.5 py-0.5 rounded-sm bg-[#f1f5f9] text-[#334155] font-semibold">{r.doc_kind.replace("_", " ")}</span>}
            {r.withdrawn && <span className="text-[0.8125rem] px-1.5 py-0.5 rounded-sm bg-[#fdecec] text-[#8a1414] border border-[#f1b0b0] font-bold">Withdrawn</span>}
            {cert.length > 0 && <span className="text-[0.8125rem] px-1.5 py-0.5 rounded-sm bg-[#e7f5e9] text-[#0d6b06] font-bold flex items-center gap-1"><BadgeCheck className="w-3 h-3" />Compulsory: {Array.from(new Set(cert.map((c) => c.scheme))).join(", ")}</span>}
            <ConfidenceBadge level={r.confidence} />
            {r.origin === "bis_portal" && <span title="Published after the archived corpus: title and edition from the BIS portal; full text not analysed" className="text-[0.8125rem] px-1.5 py-0.5 rounded-sm border border-[#cbd5e1] bg-[#f8fafc] text-[#475569] font-semibold">BIS catalogue · title only</span>}
          </div>
          <div className="text-[1rem] font-semibold text-[#13325d] mt-0.5">{r.title}</div>
          <div className="text-[0.8125rem] text-slate-500">{r.division}{r.committee ? ` · ${r.committee}` : ""}{r.editions?.length > 1 ? ` · editions archived: ${r.editions.join(", ")}` : ""}</div>
          {r.signals && <div className="text-[0.8125rem] text-slate-500 mt-0.5" title="Deterministic reason trace: how the two retrievers ranked this standard and how much of your query its title/scope covers. Engineering signals, not an official BIS methodology.">
            <b className="text-slate-400">Why:</b>{" "}
            {[r.signals.lex_rank != null ? `keyword rank ${r.signals.lex_rank + 1}` : "not in keyword top 80",
              r.signals.dense_available ? (r.signals.dense_rank != null ? `meaning rank ${r.signals.dense_rank + 1}` : "not in meaning top 80") : null,
              `${Math.round((r.signals.coverage || 0) * 100)}% of your words in its title/scope`,
              r.signals.alias ? `matches a product name used by BIS/GeM (“${r.signals.alias.split(":").slice(1).join(":")}”)` : null].filter(Boolean).join(" · ")}
          </div>}
          {r.gem_categories?.length > 0 && <div className="text-[0.8125rem] text-[#334155] mt-0.5"><b className="text-[#b7862b]">GeM:</b> {r.gem_categories.slice(0, 2).map((g: any) => `${g.category} (${g.bids} live bid${g.bids === 1 ? "" : "s"})`).join(" · ")}</div>}
        </div>
        {open ? <ChevronDown className="w-5 h-5 text-slate-400 shrink-0" /> : <ChevronRight className="w-5 h-5 text-slate-400 shrink-0" />}
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-4 border-t border-[#e2e8f0] pt-3">
          {status && <Notice tone={status.level === "bad" ? "bad" : status.level === "warn" ? "warn" : status.level === "ok" ? "good" : "info"}>
            {status.level !== "ok" && <AlertTriangle className="w-3.5 h-3.5 inline -mt-0.5 mr-1" />}{status.text}</Notice>}
          <div className="grid lg:grid-cols-[1.3fr_1fr] gap-4">
            <div className="space-y-3">
              <section>
                <h4 className="text-[0.875rem] font-bold uppercase tracking-wide text-slate-500 mb-1 flex items-center gap-1"><BookOpenCheck className="w-3.5 h-3.5" />Why it matches — Scope clause</h4>
                <p className="text-[0.9375rem] text-[#334155] leading-relaxed bg-[#f8fafc] border border-[#e2e8f0] rounded-md p-3">
                  {r.scope ? highlight(r.scope, q) : <span className="text-slate-500">Scope clause not available for this document (catalogue match on title).</span>}</p>
              </section>
              {cert.length > 0 && (
                <section>
                  <h4 className="text-[0.875rem] font-bold uppercase tracking-wide text-slate-500 mb-1 flex items-center gap-1"><BadgeCheck className="w-3.5 h-3.5" />Mandatory certification</h4>
                  <ul className="space-y-1.5">
                    {cert.slice(0, 6).map((c, i) => (
                      <li key={i} className="text-[0.875rem] border border-[#9bd3a3] bg-[#f3fbf4] rounded-md p-2">
                        <b className="text-[#0d4f07]">{c.scheme}</b>{c.product ? ` — ${c.product}` : ""}<div className="text-slate-400">{c.title}{c.matched_via ? ` (listed under ${c.matched_via})` : ""}</div>
                        {c.source_url && <a href={c.source_url} target="_blank" rel="noreferrer" className="text-[0.8125rem] text-[#1d4f93] underline">source</a>}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              <LabsPanel base={r.base} summary={r.labs} />
              {(r.equivalents?.length > 0 || r.equivalence) && (
                <section>
                  <h4 className="text-[0.875rem] font-bold uppercase tracking-wide text-slate-500 mb-1">International equivalence</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {r.equivalence && <span className="text-[0.875rem] px-2 py-0.5 rounded-sm border border-[#adc8ea] bg-[#eef4fb]">{r.equivalence} <i className="text-slate-500">(catalogue)</i></span>}
                    {r.equivalents?.map((e: any) => <span key={e.standard} className="text-[0.875rem] px-2 py-0.5 rounded-sm border border-[#e2e8f0]">{e.standard} <i className="text-slate-500">{e.degree}</i></span>)}
                  </div>
                </section>
              )}
              <div className="flex flex-wrap gap-3 text-[0.875rem]">
                {r.revision && <span className="text-slate-400">{r.revision} revision</span>}
                {status?.amendments?.length ? <span className="text-slate-400">Amendments: {status.amendments.map((a: any) => `No. ${a.no} (${a.year})`).join(", ")}</span> : r.amendments ? <span className="text-slate-400">{r.amendments} amendment(s)</span> : null}
                {r.reaffirmed && <span className="text-slate-400">reaffirmed {r.reaffirmed}</span>}
                <SpecBlockButton base={r.base} title={r.title} />
                <SpeakButton text={recommendationSpeech({ ...r, status, certification: cert }, language)} language={language} label={language === "hi" ? "सुनें" : "Read aloud"} />
                <a href={r.source} target="_blank" rel="noreferrer" className="text-[#1d4f93] underline flex items-center gap-1"><Library className="w-3.5 h-3.5" />{r.origin === "bis_portal" ? "BIS catalogue entry" : "archived text"}</a>
                <a href={`https://standardsbis.bsbedge.com/BIS_SearchStandard.aspx?Standard_Number=${encodeURIComponent(r.base.replace(/ \((.*)\)$/, (_m: string, p: string) => " : " + p.split("/").join(" : ")))}&id=0`} target="_blank" rel="noreferrer" className="text-[#1d4f93] underline flex items-center gap-1"><ExternalLink className="w-3.5 h-3.5" />verify on BIS portal</a>
              </div>
            </div>
            <div>
              <h4 className="text-[0.875rem] font-bold uppercase tracking-wide text-slate-500 mb-1 flex items-center gap-1"><Link2 className="w-3.5 h-3.5" />Allied standards to consider</h4>
              {loading && <div className="text-[0.875rem] text-slate-500 flex items-center gap-1"><Loader2 className="w-3.5 h-3.5 animate-spin" />Reading the standard’s references…</div>}
              {detail?.allied && <Allied allied={detail.allied} />}
            </div>
          </div>
          {detail?.allied && (detail.allied.groups.length > 0 || detail.allied.cited_by_total > 0) && (
            <details open={rank === 1}>
              <summary className="cursor-pointer text-[0.875rem] font-bold uppercase tracking-wide text-slate-500">Dependency map &amp; compliance tree</summary>
              <div className="mt-2 space-y-3"><StandardsNetwork base={r.base} allied={detail.allied} /><DependencyTree base={r.base} /></div>
            </details>
          )}
        </div>
      )}
    </article>
  );
}

function Allied({ allied }: { allied: any }) {
  const [openKind, setOpenKind] = useState<string | null>(allied.groups[0]?.kind || null);
  if (!allied.groups.length) return <p className="text-[0.875rem] text-slate-500">No references were extracted from this document’s text.</p>;
  return (
    <div className="space-y-1.5">
      {allied.groups.map((g: any) => (
        <div key={g.kind} className="border border-[#e2e8f0] rounded-md overflow-hidden">
          <button onClick={() => setOpenKind(openKind === g.kind ? null : g.kind)} className="w-full px-3 py-2 flex items-center justify-between text-left hover:bg-[#f8fafc]">
            <span className="text-[0.9375rem] font-bold flex items-center gap-2" style={{ color: KIND_TONE[g.kind] || "#334155" }}>
              <span className="w-2 h-2 rounded-full" style={{ background: KIND_TONE[g.kind] || "#334155" }} />{g.label}</span>
            <span className="text-[0.8125rem] font-mono text-slate-500">{g.total}</span>
          </button>
          {openKind === g.kind && (
            <ul className="divide-y divide-[#eef2f7]">
              {g.items.map((x: any) => (
                <li key={x.base} className="px-3 py-2 text-[0.875rem]">
                  <div className="flex flex-wrap items-baseline gap-2">
                    <Link href={`/recommend?q=${encodeURIComponent(x.base + " " + (x.title || ""))}`} className="font-mono font-bold text-[#1d4f93] hover:underline">{x.base}</Link>
                    <span className="text-[#334155]">{x.title}</span>
                  </div>
                  <div className="text-[0.8125rem] text-slate-500 mt-0.5">
                    cited{x.cited_edition ? ` as :${x.cited_edition}` : ""} in {x.clauses.join(" + ")} clause
                    {x.latest_archived_year && x.cited_edition && x.latest_archived_year > x.cited_edition ? <b className="text-[#8a5300]"> · newer edition :{x.latest_archived_year} exists</b> : null}
                  </div>
                  {x.snippet && <div className="text-[0.8125rem] text-slate-500 italic mt-0.5 line-clamp-2">“…{x.snippet}…”</div>}
                </li>
              ))}
              {g.total > g.items.length && <li className="px-3 py-1.5 text-[0.8125rem] text-slate-500">+{g.total - g.items.length} more</li>}
            </ul>
          )}
        </div>
      ))}
      {allied.cited_by_total > 0 && <p className="text-[0.8125rem] text-slate-500 pt-1">Used by <b className="text-[#0f2748]">{allied.cited_by_total}</b> other standard(s) — e.g. {allied.cited_by.slice(0, 4).map((c: any) => c.base).join(", ")}.</p>}
    </div>
  );
}

function DocResult({ d }: { d: any }) {
  const chk = d.citation_check || {};
  const TONE: Record<string, [string, string]> = {
    named: ["IS named in tender", "bg-[#eef4fb] text-[#1d4f93] border-[#adc8ea]"],
    recommended: ["Recommended", "bg-[#e7f5e9] text-[#0d6b06] border-[#9bd3a3]"], possible: ["Possible — verify", "bg-[#fff4e0] text-[#8a5300] border-[#f2cf8c]"],
    none: ["No confident IS", "bg-[#f1f5f9] text-[#475569] border-[#cbd5e1]"], service: ["Service — IS usually n/a", "bg-[#eef4fb] text-[#1d4f93] border-[#adc8ea]"],
  };
  return (
    <div className="space-y-5 pt-2">
      <div className="text-[0.875rem] text-slate-500">{d.document.filename} · {d.document.pages} page(s){d.document.ocr_pages?.length ? ` · OCR on ${d.document.ocr_pages.length}` : ""} · {d.items.length} item(s) found</div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {Object.entries(TONE).map(([k, [label, cls]]) => (
          <div key={k} className={`border rounded-md px-3 py-2 ${cls}`}><div className="text-[1.375rem] font-extrabold font-mono">{d.counts[k] ?? 0}</div><div className="text-[0.8125rem] font-bold uppercase">{label}</div></div>
        ))}
      </div>
      <section>
        <h3 className="font-extrabold text-[#0f2748] mb-2">What this tender buys — and the Indian Standard for each item</h3>
        <table className="gov-table">
          <thead><tr><th>Item (page)</th><th>Qty</th><th>Status</th><th>Indian Standard</th><th></th></tr></thead>
          <tbody>
            {d.items.map((it: any, i: number) => {
              const top = it.candidates[0];
              const show = it.status === "recommended" || it.status === "possible" || it.status === "named";
              const ed = top?.edition;
              return (
                <tr key={i}>
                  <td><b className="text-[#0f2748]">{it.text}</b> <span className="text-slate-500 text-[0.8125rem]">(p.{it.page})</span>
                    {it.context && <div className="text-[0.8125rem] text-slate-500 line-clamp-2">{it.context}</div>}</td>
                  <td className="whitespace-nowrap">{it.qty || "—"}</td>
                  <td><span className={`text-[0.8125rem] px-1.5 py-0.5 rounded-sm border font-bold whitespace-nowrap ${TONE[it.status]?.[1] || ""}`}>{TONE[it.status]?.[0] || it.status}</span></td>
                  <td>{show && top ? <>
                      <span className="font-mono font-bold">{top.base}{top.latest_archived_year ? `:${top.latest_archived_year}` : ""}</span> <span className="text-slate-400">{top.title}</span>
                      {top.certification?.length > 0 && <div className="text-[0.8125rem] font-bold text-[#0d6b06]">Compulsory: {top.certification.map((c: any) => c.scheme).join(", ")}</div>}
                      {ed?.status === "Withdrawn" ? <div className="text-[0.8125rem] font-bold text-[#8a1414]">withdrawn on the BIS portal → {ed.replacement || ed.superseded_by}</div>
                        : ed?.newer_than_archive ? <div className="text-[0.8125rem] font-bold text-[#8a5300]">edition in force: {ed.edition_in_force}</div>
                        : ed?.edition_in_force ? <div className="text-[0.8125rem] text-slate-400">in force: {ed.edition_in_force}{ed.amendments?.length ? ` + ${ed.amendments.length} amendment(s)` : ""}</div> : null}
                      {it.status === "named" ? null : top.already_cited ? <div className="text-[0.8125rem] text-[#0d6b06]">cited in the tender</div> : <div className="text-[0.8125rem] text-[#8a5300]">not cited in the tender</div>}
                    </> : <span className="text-slate-500 text-[0.875rem]">{it.status === "service" ? "Service item — Indian Standards usually not applicable" : "No Indian Standard matched confidently — SpecSure abstains"}</span>}</td>
                  <td>{show && top && <SpecBlockButton base={top.base} item={it.text} title={top.title} compact />}</td>
                </tr>
              );
            })}
            {!d.items.length && <tr><td colSpan={5} className="text-center text-slate-500 py-4">No procurement items found in this document.</td></tr>}
          </tbody>
        </table>
        <p className="text-[0.8125rem] text-slate-500 mt-1">{d.note}</p>
      </section>
      <section>
        <h3 className="font-extrabold text-[#0f2748] mb-2">Indian Standards the tender already cites</h3>
        {chk.citations?.length ? (
          <table className="gov-table">
            <thead><tr><th>Cited</th><th>In the corpus</th><th>Certification</th><th>Its own references not cited</th></tr></thead>
            <tbody>{chk.citations.map((c: any) => (
              <tr key={c.family}>
                <td className="font-mono">{c.citation}</td>
                <td>{c.found ? <><b className="font-mono">{c.base}</b> {c.title}
                  {c.withdrawn ? <div className="text-[0.8125rem] font-bold text-[#8a1414]">withdrawn — superseded by {c.edition?.superseded_by || c.edition?.replacement}</div>
                    : c.edition?.edition_in_force ? <div className="text-[0.8125rem] text-slate-400">in force: <b>{c.edition.edition_in_force}</b>{c.edition.amendments?.length ? ` + Amd ${c.edition.amendments.map((a: any) => a.no).join(", ")}` : ""} <i>(BIS portal, {c.edition.fetched})</i></div> : null}
                  {c.newer_edition_archived && <div className="text-[0.8125rem] font-bold text-[#8a5300]">tender cites the {c.cited_year} edition — {c.edition?.edition_in_force || c.latest_archived_year} is newer</div>}</> : <span className="text-[#8a1414] font-semibold">not found</span>}</td>
                <td className="text-[0.8125rem]">{c.certification?.map((x: any, i: number) => <div key={i}><b>{x.scheme}</b></div>) || "—"}</td>
                <td className="text-[0.8125rem]">{c.not_cited_dependencies?.slice(0, 4).map((x: any) => <div key={x.base}><span className="font-mono">{x.base}</span> {x.title}</div>)}{c.not_cited_dependencies?.length > 4 ? <div className="text-slate-500">+{c.not_cited_dependencies.length - 4} more</div> : null}</td>
              </tr>))}</tbody>
          </table>
        ) : <p className="text-[0.875rem] text-[#8a5300] font-semibold">This tender does not cite any Indian Standard.</p>}
      </section>
      <p className="text-[0.8125rem] text-slate-500">{d.disclaimer}</p>
    </div>
  );
}
